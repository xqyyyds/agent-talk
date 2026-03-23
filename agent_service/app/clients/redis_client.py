"""
Redis 客户端封装

复用 docker-compose 中已有的 Redis 实例（与 Go 后端共用），
为 Agent 记忆功能提供统一的异步访问入口。
"""

import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger("agent_service")


class RedisClient:
    """Redis 客户端（懒加载连接）"""

    def __init__(self):
        self._client: Optional[Redis] = None

    def _get_client(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=180,
                socket_timeout=180,
            )
            logger.info("✓ Redis 客户端已连接: %s", settings.redis_url.split("@")[-1])
        return self._client

    async def hget(self, key: str, field: str) -> Optional[str]:
        return await self._get_client().hget(key, field)

    async def hset(self, key: str, mapping: dict) -> int:
        return await self._get_client().hset(key, mapping=mapping)

    async def expire(self, key: str, seconds: int) -> bool:
        return await self._get_client().expire(key, seconds)

    async def hget_json(self, key: str, field: str, default: Any = None) -> Any:
        raw = await self.hget(key, field)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Redis JSON 解析失败: %s.%s", key, field)
            return default

    async def hset_json(self, key: str, field: str, value: Any) -> None:
        await self.hset(key, {field: json.dumps(value, ensure_ascii=False)})


redis_client = RedisClient()
