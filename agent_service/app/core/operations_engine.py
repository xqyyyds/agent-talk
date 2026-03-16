import asyncio
import logging
import random
import time
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

from app.config import settings
from app.core.agent_manager import agent_manager
from app.core.crawler_jobs import CrawlerConflictError, crawler_job_manager
from app.core.debate import debate_orchestrator
from app.core.hotspots import hotspots_loader
from app.core.langgraph_qa import MAX_HISTORY as QA_MAX_HISTORY
from app.core.langgraph_qa import qa_orchestrator
from app.core.runtime_policy import (
    POLICY_DEBATE,
    POLICY_QA,
    POLICY_SCHEDULER,
    get_runtime_policy,
    random_daily_target,
    seconds_until_end_of_day_utc,
)

logger = logging.getLogger("agent_service")


class OperationsEngine:
    def __init__(self) -> None:
        self._instance_id = uuid.uuid4().hex
        self._stop_event = asyncio.Event()
        self._tasks: dict[str, asyncio.Task] = {}
        self._loop_state: dict[str, dict[str, Any]] = {}
        self._redis: Redis | None = None
        self._qa_ewma_process_seconds = 0.0

    async def _redis_client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def start(self) -> None:
        if self._tasks:
            return

        self._stop_event.clear()
        self._tasks["qa"] = asyncio.create_task(self._qa_loop(), name="qa_loop")
        self._tasks["debate"] = asyncio.create_task(self._debate_loop(), name="debate_loop")
        self._tasks["crawler"] = asyncio.create_task(self._crawler_scheduler_loop(), name="crawler_loop")
        logger.info("operations engine started (instance=%s)", self._instance_id)

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks.values():
            task.cancel()
        with suppress(Exception):
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        logger.info("operations engine stopped")

    def snapshot(self) -> dict[str, Any]:
        return {
            "instance_id": self._instance_id,
            "loops": {
                name: {
                    **state,
                    "running": bool(task and not task.done()),
                }
                for name, state in self._loop_state.items()
                for task in [self._tasks.get(name)]
            },
        }

    async def _sleep(self, seconds: float) -> None:
        timeout = max(0.5, float(seconds))
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

    async def _acquire_or_refresh_leader(self, name: str, ttl_seconds: int = 120) -> bool:
        redis = await self._redis_client()
        key = f"agent_service:leader:{name}"

        current = await redis.get(key)
        if current == self._instance_id:
            await redis.expire(key, ttl_seconds)
            return True

        locked = await redis.set(key, self._instance_id, nx=True, ex=ttl_seconds)
        return bool(locked)

    def _mark_loop(self, name: str, **fields: Any) -> None:
        state = self._loop_state.setdefault(name, {})
        state.update(fields)
        state["updated_at"] = datetime.now(timezone.utc).isoformat()

    async def _get_daily_counter(self, key_prefix: str) -> int:
        redis = await self._redis_client()
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"agent_service:{key_prefix}:{day}"
        raw = await redis.get(key)
        try:
            return int(raw or 0)
        except Exception:
            return 0

    async def _incr_daily_counter(self, key_prefix: str, delta: int = 1) -> int:
        redis = await self._redis_client()
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"agent_service:{key_prefix}:{day}"
        value = await redis.incrby(key, delta)
        await redis.expire(key, 172800)
        return int(value)

    async def _process_hotspot_once(self, hotspot: dict[str, Any]) -> dict[str, Any]:
        hotspot_id = hotspot.get("id")
        topic = hotspot.get("topic", hotspot.get("title", ""))

        if hotspot_id:
            with suppress(Exception):
                await hotspots_loader.mark_processing(hotspot_id)

        try:
            result = await qa_orchestrator._process_hotspot(hotspot, 1, 1)
        except Exception as exc:
            logger.exception("qa hotspot processing failed: %s", exc)
            result = {
                "question_id": None,
                "answers_count": 0,
                "errors": [str(exc)],
            }

        question_id = result.get("question_id")
        errors = result.get("errors", [])

        if hotspot_id:
            try:
                if question_id:
                    await hotspots_loader.mark_completed(hotspot_id, question_id)
                elif errors:
                    await hotspots_loader.mark_skipped(hotspot_id)
            except Exception as exc:
                logger.warning("failed to update hotspot status (id=%s): %s", hotspot_id, exc)

        qa_orchestrator.history.append(
            {
                "id": len(qa_orchestrator.history) + 1,
                "cycle": 0,
                "hotspot": {
                    "topic": topic,
                    "source": hotspot.get("source", ""),
                },
                "hotspot_db_id": hotspot_id,
                "question_id": question_id,
                "answers_count": result.get("answers_count", 0),
                "errors": errors,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(qa_orchestrator.history) > QA_MAX_HISTORY:
            qa_orchestrator.history = qa_orchestrator.history[-QA_MAX_HISTORY:]

        return result

    def _calc_qa_interval(self, policy: dict[str, Any], pending_count: int, processed_today: int) -> float:
        target_daily = int(policy["target_daily_hotspots"])
        remaining_seconds = seconds_until_end_of_day_utc()
        target_remaining = max(pending_count, target_daily - processed_today)
        target_cycle_seconds = remaining_seconds / max(target_remaining, 1)

        min_s = int(policy["dispatch_min_seconds"])
        max_s = int(policy["dispatch_max_seconds"])
        jitter_min = float(policy["jitter_min"])
        jitter_max = float(policy["jitter_max"])

        raw_interval = target_cycle_seconds - max(self._qa_ewma_process_seconds, 0.0)
        clamped = max(min_s, min(max_s, raw_interval))
        return max(1.0, clamped * random.uniform(jitter_min, jitter_max))

    async def _qa_loop(self) -> None:
        loop_name = "qa"
        await agent_manager.initialize()

        while not self._stop_event.is_set():
            try:
                policy = await get_runtime_policy(POLICY_QA)
                self._mark_loop(loop_name, policy=policy)

                if not policy.get("enabled", True):
                    self._mark_loop(loop_name, status="disabled")
                    await self._sleep(5)
                    continue

                is_leader = await self._acquire_or_refresh_leader(loop_name, ttl_seconds=120)
                self._mark_loop(loop_name, is_leader=is_leader)
                if not is_leader:
                    await self._sleep(3)
                    continue

                if qa_orchestrator.is_running:
                    self._mark_loop(loop_name, status="manual_qa_running")
                    await self._sleep(3)
                    continue

                pending_hotspots = await hotspots_loader.load_pending()
                pending_count = len(pending_hotspots)

                if pending_count == 0:
                    processed_today = await self._get_daily_counter("qa:processed")
                    interval = self._calc_qa_interval(policy, 0, processed_today)
                    self._mark_loop(
                        loop_name,
                        status="idle",
                        pending_hotspots=0,
                        processed_today=processed_today,
                        next_interval_seconds=interval,
                    )
                    await self._sleep(interval)
                    continue

                parallelism = max(1, int(policy.get("max_parallelism", 1)))
                batch = pending_hotspots[:parallelism]

                started = time.perf_counter()
                await asyncio.gather(*(self._process_hotspot_once(item) for item in batch))
                elapsed = max(0.001, time.perf_counter() - started)
                avg_process = elapsed / max(1, len(batch))

                alpha = float(policy.get("ewma_alpha", 0.25))
                if self._qa_ewma_process_seconds <= 0:
                    self._qa_ewma_process_seconds = avg_process
                else:
                    self._qa_ewma_process_seconds = (
                        alpha * avg_process + (1 - alpha) * self._qa_ewma_process_seconds
                    )

                processed_today = await self._incr_daily_counter("qa:processed", len(batch))
                remaining_estimate = max(0, pending_count - len(batch))
                interval = self._calc_qa_interval(policy, remaining_estimate, processed_today)

                self._mark_loop(
                    loop_name,
                    status="running",
                    pending_hotspots=pending_count,
                    processed_today=processed_today,
                    batch_size=len(batch),
                    ewma_process_seconds=round(self._qa_ewma_process_seconds, 3),
                    next_interval_seconds=round(interval, 3),
                )
                await self._sleep(interval)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("qa loop error: %s", exc)
                self._mark_loop(loop_name, status="error", error=str(exc))
                await self._sleep(5)

    async def _get_or_create_debate_daily_target(self, min_target: int, max_target: int) -> int:
        redis = await self._redis_client()
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"agent_service:debate:target:{day}"

        raw = await redis.get(key)
        if raw is not None:
            try:
                return int(raw)
            except Exception:
                pass

        target = random_daily_target(min_target, max_target)
        await redis.set(key, target, ex=172800)
        return target

    def _calc_debate_interval(self, policy: dict[str, Any], remaining_sessions: int) -> float:
        remaining_seconds = seconds_until_end_of_day_utc()
        base = remaining_seconds / max(1, remaining_sessions)

        min_seconds = int(policy["interval_min_minutes"]) * 60
        max_seconds = int(policy["interval_max_minutes"]) * 60
        jitter_min = float(policy["jitter_min"])
        jitter_max = float(policy["jitter_max"])

        clamped = max(min_seconds, min(max_seconds, base))
        return max(1.0, clamped * random.uniform(jitter_min, jitter_max))

    async def _debate_loop(self) -> None:
        loop_name = "debate"

        while not self._stop_event.is_set():
            try:
                policy = await get_runtime_policy(POLICY_DEBATE)
                self._mark_loop(loop_name, policy=policy)

                if not policy.get("enabled", True):
                    self._mark_loop(loop_name, status="disabled")
                    await self._sleep(10)
                    continue

                is_leader = await self._acquire_or_refresh_leader(loop_name, ttl_seconds=120)
                self._mark_loop(loop_name, is_leader=is_leader)
                if not is_leader:
                    await self._sleep(5)
                    continue

                if debate_orchestrator.is_running:
                    self._mark_loop(loop_name, status="manual_debate_running")
                    await self._sleep(5)
                    continue

                daily_target = await self._get_or_create_debate_daily_target(
                    int(policy["daily_target_min"]), int(policy["daily_target_max"])
                )
                completed = await self._get_daily_counter("debate:completed")

                if completed >= daily_target:
                    self._mark_loop(
                        loop_name,
                        status="daily_target_reached",
                        daily_target=daily_target,
                        completed=completed,
                    )
                    await self._sleep(30)
                    continue

                history_count_before = len(debate_orchestrator.history)
                await debate_orchestrator.start_debate_session(cycle_count=1, resume=False)
                history_count_after = len(debate_orchestrator.history)

                if history_count_after > history_count_before:
                    completed = await self._incr_daily_counter("debate:completed", 1)
                else:
                    completed = await self._get_daily_counter("debate:completed")

                remaining_sessions = max(0, daily_target - completed)
                interval = self._calc_debate_interval(policy, remaining_sessions)

                self._mark_loop(
                    loop_name,
                    status="running",
                    daily_target=daily_target,
                    completed=completed,
                    remaining_sessions=remaining_sessions,
                    next_interval_seconds=round(interval, 3),
                )
                await self._sleep(interval)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("debate loop error: %s", exc)
                self._mark_loop(loop_name, status="error", error=str(exc))
                await self._sleep(10)

    async def _crawler_scheduler_loop(self) -> None:
        loop_name = "crawler"
        key_last_run = "agent_service:crawler:last_run_ts"

        while not self._stop_event.is_set():
            try:
                policy = await get_runtime_policy(POLICY_SCHEDULER)
                self._mark_loop(loop_name, policy=policy)

                if not policy.get("auto_crawler_enabled", True):
                    self._mark_loop(loop_name, status="disabled")
                    await self._sleep(15)
                    continue

                is_leader = await self._acquire_or_refresh_leader(loop_name, ttl_seconds=120)
                self._mark_loop(loop_name, is_leader=is_leader)
                if not is_leader:
                    await self._sleep(10)
                    continue

                interval_seconds = int(policy.get("auto_crawler_interval_minutes", 120)) * 60
                sources = policy.get("sources") or ["zhihu", "weibo"]

                redis = await self._redis_client()
                raw = await redis.get(key_last_run)
                try:
                    last_run_ts = int(raw) if raw is not None else 0
                except Exception:
                    last_run_ts = 0

                now_ts = int(time.time())
                elapsed = now_ts - last_run_ts

                if elapsed < interval_seconds:
                    wait_seconds = max(5, interval_seconds - elapsed)
                    self._mark_loop(
                        loop_name,
                        status="waiting",
                        next_run_in_seconds=wait_seconds,
                        last_run_ts=last_run_ts,
                    )
                    await self._sleep(min(wait_seconds, 30))
                    continue

                created_jobs: list[str] = []
                skipped_sources: list[str] = []
                for source in sources:
                    try:
                        job = await crawler_job_manager.create_job(source)
                        created_jobs.append(job["job_id"])
                    except CrawlerConflictError:
                        skipped_sources.append(source)
                    except Exception as exc:
                        logger.warning("auto crawler failed to create job (%s): %s", source, exc)
                        skipped_sources.append(source)

                await redis.set(key_last_run, now_ts, ex=172800)
                self._mark_loop(
                    loop_name,
                    status="triggered",
                    created_jobs=created_jobs,
                    skipped_sources=skipped_sources,
                    last_run_ts=now_ts,
                    next_run_in_seconds=interval_seconds,
                )
                await self._sleep(10)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("crawler loop error: %s", exc)
                self._mark_loop(loop_name, status="error", error=str(exc))
                await self._sleep(15)


operations_engine = OperationsEngine()
