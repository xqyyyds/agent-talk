import json
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from redis.asyncio import Redis

from app.config import settings


RUNTIME_POLICY_KEY = "agent_service:runtime:policies"
RUNTIME_POLICY_VERSION_KEY = "agent_service:runtime:policies:version"
CACHE_TTL_SECONDS = 3

POLICY_QA = "qa_policy"
POLICY_DEBATE = "debate_policy"
POLICY_SCHEDULER = "scheduler_policy"
POLICY_REALTIME = "realtime_policy"

DEFAULT_POLICIES: dict[str, dict[str, Any]] = {
    POLICY_QA: {
        "enabled": True,
        "target_daily_hotspots": 480,
        "dispatch_min_seconds": 10,
        "dispatch_max_seconds": 180,
        "jitter_min": 0.85,
        "jitter_max": 1.15,
        "max_parallelism": 2,
        "ewma_alpha": 0.25,
    },
    POLICY_DEBATE: {
        "enabled": True,
        "daily_target_min": 10,
        "daily_target_max": 15,
        "interval_min_minutes": 45,
        "interval_max_minutes": 180,
        "jitter_min": 0.85,
        "jitter_max": 1.15,
        "new_agent_auto_join": True,
    },
    POLICY_SCHEDULER: {
        "auto_crawler_enabled": True,
        "auto_crawler_interval_minutes": 120,
        "sources": ["zhihu", "weibo"],
    },
    POLICY_REALTIME: {
        "sse_enabled": True,
        "fallback_poll_seconds": 5,
    },
}

_cache: dict[str, Any] = {"data": None, "ts": 0.0}


def _to_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        num = int(value)
    except Exception:
        num = default
    return max(minimum, min(maximum, num))


def _to_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        num = float(value)
    except Exception:
        num = default
    return max(minimum, min(maximum, num))


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _normalize_sources(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["zhihu", "weibo"]
    normalized: list[str] = []
    for item in value:
        source = str(item).strip().lower()
        if source in {"zhihu", "weibo"} and source not in normalized:
            normalized.append(source)
    return normalized or ["zhihu", "weibo"]


def _validate_policy(policy_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    defaults = DEFAULT_POLICIES[policy_name]

    if policy_name == POLICY_QA:
        min_seconds = _to_int(
            payload.get("dispatch_min_seconds"), defaults["dispatch_min_seconds"], 1, 600
        )
        max_seconds = _to_int(
            payload.get("dispatch_max_seconds"), defaults["dispatch_max_seconds"], min_seconds, 1800
        )
        jitter_min = _to_float(payload.get("jitter_min"), defaults["jitter_min"], 0.5, 1.0)
        jitter_max = _to_float(payload.get("jitter_max"), defaults["jitter_max"], jitter_min, 2.0)
        return {
            "enabled": _to_bool(payload.get("enabled"), defaults["enabled"]),
            "target_daily_hotspots": _to_int(
                payload.get("target_daily_hotspots"),
                defaults["target_daily_hotspots"],
                1,
                5000,
            ),
            "dispatch_min_seconds": min_seconds,
            "dispatch_max_seconds": max_seconds,
            "jitter_min": jitter_min,
            "jitter_max": jitter_max,
            "max_parallelism": _to_int(
                payload.get("max_parallelism"), defaults["max_parallelism"], 1, 8
            ),
            "ewma_alpha": _to_float(payload.get("ewma_alpha"), defaults["ewma_alpha"], 0.05, 0.95),
        }

    if policy_name == POLICY_DEBATE:
        min_target = _to_int(payload.get("daily_target_min"), defaults["daily_target_min"], 1, 100)
        max_target = _to_int(payload.get("daily_target_max"), defaults["daily_target_max"], min_target, 200)
        min_interval = _to_int(
            payload.get("interval_min_minutes"), defaults["interval_min_minutes"], 1, 1440
        )
        max_interval = _to_int(
            payload.get("interval_max_minutes"), defaults["interval_max_minutes"], min_interval, 1440
        )
        jitter_min = _to_float(payload.get("jitter_min"), defaults["jitter_min"], 0.5, 1.0)
        jitter_max = _to_float(payload.get("jitter_max"), defaults["jitter_max"], jitter_min, 2.0)
        return {
            "enabled": _to_bool(payload.get("enabled"), defaults["enabled"]),
            "daily_target_min": min_target,
            "daily_target_max": max_target,
            "interval_min_minutes": min_interval,
            "interval_max_minutes": max_interval,
            "jitter_min": jitter_min,
            "jitter_max": jitter_max,
            "new_agent_auto_join": _to_bool(
                payload.get("new_agent_auto_join"), defaults["new_agent_auto_join"]
            ),
        }

    if policy_name == POLICY_SCHEDULER:
        return {
            "auto_crawler_enabled": _to_bool(
                payload.get("auto_crawler_enabled"), defaults["auto_crawler_enabled"]
            ),
            "auto_crawler_interval_minutes": _to_int(
                payload.get("auto_crawler_interval_minutes"),
                defaults["auto_crawler_interval_minutes"],
                10,
                1440,
            ),
            "sources": _normalize_sources(payload.get("sources", defaults["sources"])),
        }

    if policy_name == POLICY_REALTIME:
        return {
            "sse_enabled": _to_bool(payload.get("sse_enabled"), defaults["sse_enabled"]),
            "fallback_poll_seconds": _to_int(
                payload.get("fallback_poll_seconds"), defaults["fallback_poll_seconds"], 1, 120
            ),
        }

    raise ValueError(f"unsupported policy: {policy_name}")


async def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def get_runtime_policies(force_refresh: bool = False) -> dict[str, dict[str, Any]]:
    now = time.time()
    if (
        not force_refresh
        and _cache["data"] is not None
        and now - float(_cache["ts"]) < CACHE_TTL_SECONDS
    ):
        return json.loads(json.dumps(_cache["data"]))

    policies: dict[str, dict[str, Any]] = {
        name: dict(defaults) for name, defaults in DEFAULT_POLICIES.items()
    }

    redis = await _redis()
    try:
        stored = await redis.hgetall(RUNTIME_POLICY_KEY)
        for policy_name, raw in stored.items():
            if policy_name not in policies:
                continue
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    merged = {**policies[policy_name], **parsed}
                    policies[policy_name] = _validate_policy(policy_name, merged)
            except Exception:
                continue
    finally:
        await redis.aclose()

    _cache["data"] = policies
    _cache["ts"] = now
    return json.loads(json.dumps(policies))


async def get_runtime_policy(policy_name: str) -> dict[str, Any]:
    if policy_name not in DEFAULT_POLICIES:
        raise ValueError(f"unsupported policy: {policy_name}")
    policies = await get_runtime_policies()
    return policies[policy_name]


async def update_runtime_policy(policy_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if policy_name not in DEFAULT_POLICIES:
        raise ValueError(f"unsupported policy: {policy_name}")

    policies = await get_runtime_policies(force_refresh=True)
    merged = {**policies[policy_name], **(payload or {})}
    validated = _validate_policy(policy_name, merged)

    redis = await _redis()
    try:
        await redis.hset(
            RUNTIME_POLICY_KEY,
            mapping={policy_name: json.dumps(validated, ensure_ascii=False)},
        )
        await redis.incr(RUNTIME_POLICY_VERSION_KEY)
    finally:
        await redis.aclose()

    _cache["data"] = None
    _cache["ts"] = 0.0
    return await get_runtime_policy(policy_name)


def seconds_until_end_of_day_utc() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((tomorrow - now).total_seconds()))


def random_daily_target(min_value: int, max_value: int) -> int:
    return random.randint(min_value, max_value)
