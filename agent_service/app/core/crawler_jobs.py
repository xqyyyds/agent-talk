import asyncio
import json
import os
import sys
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redis.asyncio import Redis

from app.config import settings
from app.core.runtime_config import get_runtime_config


JOB_INDEX_KEY = "crawler:jobs:index"
JOB_KEY_PREFIX = "crawler:job:"
JOB_LOG_KEY_PREFIX = "crawler:job:logs:"
RUNNING_SOURCE_KEY_PREFIX = "crawler:running:"
MAX_JOB_HISTORY = 200
MAX_LOG_LINES = 1200
STALE_CLEANUP_SECONDS = 86400
RUNNING_STATUSES = {"queued", "running"}
SUPPORTED_SOURCES = {"zhihu", "weibo"}
SCRIPT_BY_SOURCE = {
    "zhihu": "zhihu_hotspot_crawler.py",
    "weibo": "weibo_spider.py",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


class CrawlerJobError(Exception):
    pass


class CrawlerConflictError(CrawlerJobError):
    def __init__(self, source: str, job_id: str):
        super().__init__(f"source '{source}' already has a running job: {job_id}")
        self.source = source
        self.job_id = job_id


class CrawlerJobNotFoundError(CrawlerJobError):
    pass


class CrawlerJobManager:
    def __init__(self) -> None:
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._default_job_timeout_seconds = max(
            300, int(getattr(settings, "crawler_job_timeout_seconds", 1800))
        )
        self._default_lock_ttl_seconds = max(
            self._default_job_timeout_seconds + 600,
            int(getattr(settings, "crawler_source_lock_ttl_seconds", 3600)),
        )
        self._scripts_dir = Path(__file__).resolve().parents[2] / "scripts"

    async def _resolve_job_timeout_seconds(self) -> int:
        runtime_cfg = await get_runtime_config()
        value = runtime_cfg.get(
            "crawler_job_timeout_seconds", self._default_job_timeout_seconds
        )
        try:
            return max(300, int(value))
        except (TypeError, ValueError):
            return self._default_job_timeout_seconds

    def _resolve_lock_ttl_seconds(self, job_timeout_seconds: int) -> int:
        return max(job_timeout_seconds + 600, self._default_lock_ttl_seconds)

    async def _redis(self) -> Redis:
        return Redis.from_url(settings.redis_url, decode_responses=True)

    @staticmethod
    def _job_key(job_id: str) -> str:
        return f"{JOB_KEY_PREFIX}{job_id}"

    @staticmethod
    def _job_logs_key(job_id: str) -> str:
        return f"{JOB_LOG_KEY_PREFIX}{job_id}"

    @staticmethod
    def _source_running_key(source: str) -> str:
        return f"{RUNNING_SOURCE_KEY_PREFIX}{source}"

    async def _append_log(self, redis: Redis, job_id: str, message: str) -> None:
        line = message.strip()
        if not line:
            return
        # Use local container timezone (Asia/Shanghai in our image) for readable ops logs.
        log_line = f"{datetime.now().strftime('%H:%M:%S')} {line}"
        logs_key = self._job_logs_key(job_id)
        await redis.rpush(logs_key, log_line)
        await redis.ltrim(logs_key, -MAX_LOG_LINES, -1)
        await redis.expire(logs_key, STALE_CLEANUP_SECONDS)

    async def _update_job(self, redis: Redis, job_id: str, fields: dict[str, Any]) -> None:
        if not fields:
            return
        payload = {k: json.dumps(v, ensure_ascii=False) for k, v in fields.items()}
        payload["updated_at"] = json.dumps(_now_iso(), ensure_ascii=False)
        await redis.hset(self._job_key(job_id), mapping=payload)
        await redis.expire(self._job_key(job_id), STALE_CLEANUP_SECONDS)

    async def _reconcile_stale_jobs(
        self, redis: Redis, source: str | None = None
    ) -> None:
        """
        Recover orphaned jobs that are still marked queued/running after process restart.
        A job is considered stale when:
        - status is queued/running
        - no local active task
        - no source lock points to this job
        - elapsed time exceeds timeout_seconds
        """
        now = datetime.now(timezone.utc)
        ids = await redis.lrange(JOB_INDEX_KEY, 0, MAX_JOB_HISTORY - 1)
        for job_id in ids:
            raw = await redis.hgetall(self._job_key(job_id))
            if not raw:
                continue
            job = self._decode_job(raw)
            job_source = str(job.get("source") or "").strip().lower()
            if source and job_source != source:
                continue
            status = str(job.get("status") or "").strip().lower()
            if status not in RUNNING_STATUSES:
                continue

            task = self._active_tasks.get(job_id)
            if task is not None and not task.done():
                continue

            lock_owner = await redis.get(self._source_running_key(job_source))
            if lock_owner == job_id:
                continue

            timeout_seconds = int(
                job.get("timeout_seconds") or self._default_job_timeout_seconds
            )
            started_at = _parse_iso(job.get("started_at")) or _parse_iso(job.get("created_at"))
            if started_at is None:
                started_at = now
            elapsed = int((now - started_at).total_seconds())
            if elapsed < timeout_seconds:
                continue

            await self._append_log(
                redis,
                job_id,
                "[system] stale running job recovered after restart",
            )
            await self._update_job(
                redis,
                job_id,
                {
                    "status": "timeout",
                    "finished_at": _now_iso(),
                    "duration_seconds": elapsed,
                    "exit_code": None,
                    "error_message": "stale running job recovered",
                },
            )

    @staticmethod
    def _decode_job(raw: dict[str, str]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in raw.items():
            try:
                result[key] = json.loads(value)
            except Exception:
                result[key] = value
        return result

    async def create_job(self, source: str) -> dict[str, Any]:
        source = source.strip().lower()
        if source not in SUPPORTED_SOURCES:
            raise CrawlerJobError(f"unsupported source: {source}")

        script_name = SCRIPT_BY_SOURCE[source]
        script_path = self._scripts_dir / script_name
        if not script_path.exists():
            raise CrawlerJobError(f"script not found: {script_name}")

        job_id = uuid.uuid4().hex
        now = _now_iso()
        lock_key = self._source_running_key(source)
        lock_acquired = False
        timeout_seconds = await self._resolve_job_timeout_seconds()
        lock_ttl_seconds = self._resolve_lock_ttl_seconds(timeout_seconds)

        redis = await self._redis()
        try:
            await self._reconcile_stale_jobs(redis, source=source)
            locked = await redis.set(lock_key, job_id, nx=True, ex=lock_ttl_seconds)
            if not locked:
                running_job_id = await redis.get(lock_key)
                raise CrawlerConflictError(source, running_job_id or "unknown")
            lock_acquired = True

            job = {
                "job_id": job_id,
                "source": source,
                "script_name": script_name,
                "status": "queued",
                "created_at": now,
                "started_at": None,
                "finished_at": None,
                "exit_code": None,
                "duration_seconds": None,
                "error_message": "",
                "timeout_seconds": timeout_seconds,
                "updated_at": now,
            }
            await self._update_job(redis, job_id, job)
            await redis.lpush(JOB_INDEX_KEY, job_id)
            await redis.ltrim(JOB_INDEX_KEY, 0, MAX_JOB_HISTORY - 1)
            await redis.expire(JOB_INDEX_KEY, STALE_CLEANUP_SECONDS)
        except Exception:
            if lock_acquired:
                with suppress(Exception):
                    lock_job_id = await redis.get(lock_key)
                    if lock_job_id == job_id:
                        await redis.delete(lock_key)
            raise
        finally:
            await redis.aclose()

        async with self._lock:
            task = asyncio.create_task(
                self._run_job(
                    job_id,
                    source,
                    script_name,
                    script_path,
                    timeout_seconds,
                )
            )
            self._active_tasks[job_id] = task

        return job

    async def _run_job(
        self,
        job_id: str,
        source: str,
        script_name: str,
        script_path: Path,
        timeout_seconds: int,
    ) -> None:
        start_ts = datetime.now(timezone.utc).timestamp()
        redis = await self._redis()
        process: asyncio.subprocess.Process | None = None
        try:
            await self._update_job(
                redis,
                job_id,
                {
                    "status": "running",
                    "started_at": _now_iso(),
                    "error_message": "",
                },
            )
            await self._append_log(redis, job_id, f"[system] starting {script_name}")

            runtime_cfg = await get_runtime_config()
            subprocess_env = {**os.environ}
            zhihu_cookie = str(runtime_cfg.get("zhihu_cookie", "") or "").strip()
            weibo_cookie = str(runtime_cfg.get("weibo_cookie", "") or "").strip()
            if zhihu_cookie:
                subprocess_env["ZHIHU_COOKIE"] = zhihu_cookie
            if weibo_cookie:
                subprocess_env["WEIBO_COOKIE"] = weibo_cookie
            subprocess_env["PYTHONUNBUFFERED"] = "1"

            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                str(script_path),
                cwd=str(self._scripts_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=subprocess_env,
            )

            async def _consume_stream(stream: asyncio.StreamReader | None, tag: str) -> None:
                if stream is None:
                    return
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    if text:
                        await self._append_log(redis, job_id, f"[{tag}] {text}")

            stdout_task = asyncio.create_task(_consume_stream(process.stdout, "stdout"))
            stderr_task = asyncio.create_task(_consume_stream(process.stderr, "stderr"))

            timed_out = False
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                timed_out = True
                with suppress(Exception):
                    process.kill()
                await process.wait()

            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

            duration_seconds = int(datetime.now(timezone.utc).timestamp() - start_ts)
            if timed_out:
                await self._append_log(redis, job_id, "[system] timeout reached, process killed")
                await self._update_job(
                    redis,
                    job_id,
                    {
                        "status": "timeout",
                        "finished_at": _now_iso(),
                        "duration_seconds": duration_seconds,
                        "exit_code": None,
                        "error_message": "crawler timed out",
                    },
                )
                return

            return_code = process.returncode
            if return_code == 0:
                await self._append_log(redis, job_id, "[system] crawler finished successfully")
                await self._update_job(
                    redis,
                    job_id,
                    {
                        "status": "success",
                        "finished_at": _now_iso(),
                        "duration_seconds": duration_seconds,
                        "exit_code": return_code,
                        "error_message": "",
                    },
                )
            else:
                await self._append_log(redis, job_id, f"[system] crawler failed: exit={return_code}")
                await self._update_job(
                    redis,
                    job_id,
                    {
                        "status": "failed",
                        "finished_at": _now_iso(),
                        "duration_seconds": duration_seconds,
                        "exit_code": return_code,
                        "error_message": f"script exited with code {return_code}",
                    },
                )
        except Exception as exc:
            duration_seconds = int(datetime.now(timezone.utc).timestamp() - start_ts)
            await self._append_log(redis, job_id, f"[system] internal error: {exc}")
            await self._update_job(
                redis,
                job_id,
                {
                    "status": "failed",
                    "finished_at": _now_iso(),
                    "duration_seconds": duration_seconds,
                    "exit_code": None,
                    "error_message": str(exc),
                },
            )
        finally:
            # Release per-source running lock if it still belongs to this job.
            lock_key = self._source_running_key(source)
            with suppress(Exception):
                lock_job_id = await redis.get(lock_key)
                if lock_job_id == job_id:
                    await redis.delete(lock_key)
            await redis.aclose()
            async with self._lock:
                self._active_tasks.pop(job_id, None)

    async def get_job(self, job_id: str) -> dict[str, Any]:
        redis = await self._redis()
        try:
            await self._reconcile_stale_jobs(redis)
            raw = await redis.hgetall(self._job_key(job_id))
        finally:
            await redis.aclose()
        if not raw:
            raise CrawlerJobNotFoundError(f"job not found: {job_id}")
        return self._decode_job(raw)

    async def list_jobs(self, source: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        source_filter = source.strip().lower() if source else None
        if source_filter and source_filter not in SUPPORTED_SOURCES:
            raise CrawlerJobError(f"unsupported source: {source_filter}")

        limit = max(1, min(limit, 100))
        redis = await self._redis()
        try:
            await self._reconcile_stale_jobs(redis, source=source_filter)
            ids = await redis.lrange(JOB_INDEX_KEY, 0, max(limit * 4 - 1, 0))
            jobs: list[dict[str, Any]] = []
            for job_id in ids:
                raw = await redis.hgetall(self._job_key(job_id))
                if not raw:
                    continue
                job = self._decode_job(raw)
                if source_filter and job.get("source") != source_filter:
                    continue
                jobs.append(job)
                if len(jobs) >= limit:
                    break
            return jobs
        finally:
            await redis.aclose()

    async def get_logs(self, job_id: str, tail: int = 200) -> list[str]:
        tail = max(1, min(tail, 2000))
        redis = await self._redis()
        try:
            exists = await redis.exists(self._job_key(job_id))
            if not exists:
                raise CrawlerJobNotFoundError(f"job not found: {job_id}")
            logs = await redis.lrange(self._job_logs_key(job_id), -tail, -1)
            return logs
        finally:
            await redis.aclose()


crawler_job_manager = CrawlerJobManager()
