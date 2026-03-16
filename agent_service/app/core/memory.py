"""
Agent 记忆模块（设计文档第十一章 · 方案 A：去重记忆）

存储结构（Redis Hash，复用已有 Redis 实例）：
- key:   agent_memory:{agent_id}
- field: recent_questions  → JSON 列表，最近 N 条问题标题
- field: recent_topics     → JSON 列表，最近 N 条热点主题
- TTL:   settings.memory_ttl_days 天自动过期

容错原则：
  记忆是辅助功能，Redis 异常不可阻断主问答流程。
  所有外层方法均 try/except，异常时降级返回空列表或静默跳过写入。
"""

import logging
from typing import List

from app.clients.redis_client import redis_client
from app.config import settings

logger = logging.getLogger("agent_service")


class AgentMemoryService:
    """Agent 近期记忆读写服务"""

    @staticmethod
    def _memory_key(agent_id: int) -> str:
        return f"agent_memory:{agent_id}"

    @staticmethod
    def _ttl_seconds() -> int:
        return max(settings.memory_ttl_days, 1) * 86400

    # ── 读取 ──────────────────────────────────────────────────

    async def get_recent_questions(self, agent_id: int) -> List[str]:
        """获取 agent 最近提过的问题标题（Redis 异常时返回空列表）"""
        if not agent_id:
            return []
        try:
            data = await redis_client.hget_json(
                self._memory_key(agent_id), "recent_questions", default=[]
            )
            if not isinstance(data, list):
                return []
            return [str(item).strip() for item in data if str(item).strip()]
        except Exception as e:
            logger.warning("读取 agent %s 近期问题记忆失败: %s", agent_id, e)
            return []

    async def get_recent_topics(self, agent_id: int) -> List[str]:
        """获取 agent 最近参与过的热点主题（Redis 异常时返回空列表）"""
        if not agent_id:
            return []
        try:
            data = await redis_client.hget_json(
                self._memory_key(agent_id), "recent_topics", default=[]
            )
            if not isinstance(data, list):
                return []
            return [str(item).strip() for item in data if str(item).strip()]
        except Exception as e:
            logger.warning("读取 agent %s 近期主题记忆失败: %s", agent_id, e)
            return []

    # ── 写入 ──────────────────────────────────────────────────

    async def add_question(self, agent_id: int, question_title: str) -> None:
        """记录一条新问题标题（去重 + 头插，保留最新 N 条）"""
        if not agent_id or not question_title:
            return
        try:
            key = self._memory_key(agent_id)
            items = await self.get_recent_questions(agent_id)
            normalized = question_title.strip()

            items = [q for q in items if q != normalized]
            items.insert(0, normalized)
            items = items[: settings.recent_questions_limit]

            await redis_client.hset_json(key, "recent_questions", items)
            await redis_client.expire(key, self._ttl_seconds())
        except Exception as e:
            logger.warning("写入 agent %s 问题记忆失败: %s", agent_id, e)

    async def add_topic(self, agent_id: int, topic: str) -> None:
        """记录一条新热点主题（去重 + 头插，保留最新 N 条）"""
        if not agent_id or not topic:
            return
        try:
            key = self._memory_key(agent_id)
            items = await self.get_recent_topics(agent_id)
            normalized = topic.strip()

            items = [t for t in items if t != normalized]
            items.insert(0, normalized)
            items = items[: settings.recent_topics_limit]

            await redis_client.hset_json(key, "recent_topics", items)
            await redis_client.expire(key, self._ttl_seconds())
        except Exception as e:
            logger.warning("写入 agent %s 主题记忆失败: %s", agent_id, e)


agent_memory = AgentMemoryService()
