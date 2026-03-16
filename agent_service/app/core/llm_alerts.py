import json
import uuid
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

from app.config import settings


ALERTS_KEY = "agent_service:llm_alerts"
ALERTS_ACK_KEY = "agent_service:llm_alerts:acked"
ALERTS_MAX_ITEMS = 500


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def push_llm_alert(
    *,
    scene: str,
    primary_model: str,
    secondary_model: str | None,
    primary_error: str,
    fallback_succeeded: bool,
    secondary_error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "at": _utc_now_iso(),
        "scene": scene,
        "primary_model": primary_model,
        "secondary_model": secondary_model,
        "primary_error": primary_error[:2000],
        "fallback_succeeded": fallback_succeeded,
        "secondary_error": (secondary_error or "")[:2000],
    }

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.lpush(ALERTS_KEY, json.dumps(payload, ensure_ascii=False))
        await redis.ltrim(ALERTS_KEY, 0, ALERTS_MAX_ITEMS - 1)
    finally:
        await redis.aclose()
    return payload


async def list_llm_alerts(limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(500, int(limit)))
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw_items = await redis.lrange(ALERTS_KEY, 0, limit - 1)
        acked_ids = await redis.smembers(ALERTS_ACK_KEY)
    finally:
        await redis.aclose()

    acked_set = set(acked_ids or [])
    items: list[dict[str, Any]] = []
    for raw in raw_items:
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                payload["acknowledged"] = payload.get("id") in acked_set
                items.append(payload)
        except Exception:
            continue
    return items


async def ack_llm_alerts(ids: list[str]) -> int:
    clean_ids = [x.strip() for x in ids if isinstance(x, str) and x.strip()]
    if not clean_ids:
        return 0

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        count = await redis.sadd(ALERTS_ACK_KEY, *clean_ids)
    finally:
        await redis.aclose()
    return int(count or 0)
