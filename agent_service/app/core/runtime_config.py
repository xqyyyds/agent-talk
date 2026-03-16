import json
import time
from typing import Any

from redis.asyncio import Redis

from app.config import settings


_ALLOWED_KEYS = {
    "llm_failover_mode",
    "openai_api_base",
    "openai_api_key",
    "llm_model",
    "llm_temperature",
    "openai_api_base_secondary",
    "openai_api_key_secondary",
    "llm_model_secondary",
    "llm_temperature_secondary",
    "tavily_api_key",
    "zhihu_cookie",
    "weibo_cookie",
}

_DEFAULTS: dict[str, Any] = {
    "llm_failover_mode": "single",
    "openai_api_base": settings.openai_api_base,
    "openai_api_key": settings.openai_api_key,
    "llm_model": settings.llm_model,
    "llm_temperature": settings.llm_temperature,
    "openai_api_base_secondary": "",
    "openai_api_key_secondary": "",
    "llm_model_secondary": "",
    "llm_temperature_secondary": settings.llm_temperature,
    "tavily_api_key": settings.tavily_api_key,
    "zhihu_cookie": "",
    "weibo_cookie": "",
}

_cache: dict[str, Any] = {"data": None, "ts": 0.0}


def _to_string_map(values: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in values.items():
        if key not in _ALLOWED_KEYS:
            continue
        if value is None:
            continue
        out[key] = json.dumps(value, ensure_ascii=False)
    return out


def _parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return raw


async def get_runtime_config(force_refresh: bool = False) -> dict[str, Any]:
    now = time.time()
    if (
        not force_refresh
        and _cache["data"] is not None
        and now - float(_cache["ts"]) < 5
    ):
        return dict(_cache["data"])

    data: dict[str, Any] = dict(_DEFAULTS)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        stored = await redis.hgetall(settings.runtime_config_key)
        if stored:
            for key, raw in stored.items():
                if key in _ALLOWED_KEYS:
                    data[key] = _parse_value(raw)
    finally:
        await redis.aclose()

    _cache["data"] = dict(data)
    _cache["ts"] = now
    return data


async def update_runtime_config(payload: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in _ALLOWED_KEYS:
            continue
        if value is None:
            continue
        updates[key] = value

    if not updates:
        return await get_runtime_config(force_refresh=True)

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.hset(settings.runtime_config_key, mapping=_to_string_map(updates))
    finally:
        await redis.aclose()

    _cache["data"] = None
    _cache["ts"] = 0.0
    return await get_runtime_config(force_refresh=True)
