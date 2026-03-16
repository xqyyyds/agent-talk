import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional
from app.config import settings
from app.clients.backend_api import backend_client

logger = logging.getLogger("agent_service")


class HotspotsLoader:
    """热点加载器（优先从数据库读取，fallback 到 JSON）"""

    def __init__(self):
        self.hotspots_file = Path(settings.hotspots_file)
        self.hotspots = {}
        self._db_hotspots: List[Dict] = []

    async def load_pending(self, source: str = None, date: str = None) -> List[Dict]:
        """从后端 API 加载待处理热点"""
        try:
            hotspots = await backend_client.get_pending_hotspots(
                source=source, date=date
            )
            self._db_hotspots = hotspots
            logger.info(f"✓ 从数据库加载了 {len(hotspots)} 个待处理热点")
            return hotspots
        except Exception as e:
            logger.warning(f"从数据库加载热点失败，降级到 JSON: {e}")
            return []

    async def mark_completed(self, hotspot_id: int, question_id: int = None):
        """标记热点为已完成"""
        await backend_client.update_hotspot_status(
            hotspot_id=hotspot_id, status="completed", question_id=question_id
        )

    async def mark_processing(self, hotspot_id: int):
        """标记热点为处理中"""
        await backend_client.update_hotspot_status(
            hotspot_id=hotspot_id, status="processing"
        )

    async def mark_skipped(self, hotspot_id: int):
        """标记热点为已跳过"""
        await backend_client.update_hotspot_status(
            hotspot_id=hotspot_id, status="skipped"
        )

    def load(self) -> Dict[str, List[str]]:
        """加载热点数据（JSON fallback）"""
        if not self.hotspots_file.exists():
            logger.warning(f"⚠️  热点文件不存在: {self.hotspots_file}")
            return {}

        try:
            with open(self.hotspots_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.hotspots = data.get("hotspots", {})
                logger.info(f"✓ 从 JSON 加载了 {len(self.hotspots)} 个类别的热点")
                return self.hotspots
        except Exception as e:
            logger.error(f"✗ 加载热点文件失败: {e}")
            return {}

    def get_all_hotspots(self) -> List[Dict]:
        """获取所有热点（JSON模式）"""
        all_hotspots = []
        for category, topics in self.hotspots.items():
            for topic in topics:
                all_hotspots.append({"category": category, "topic": topic})
        return all_hotspots

    def get_hotspots_by_category(self, category: str) -> List[Dict]:
        """获取指定类别的热点（JSON模式）"""
        if category not in self.hotspots:
            return []
        return [
            {"category": category, "topic": topic} for topic in self.hotspots[category]
        ]

    def get_categories(self) -> List[str]:
        """获取所有类别"""
        return list(self.hotspots.keys())

    def shuffle_hotspots(self) -> List[Dict]:
        """随机打乱所有热点（JSON模式）"""
        all_hotspots = self.get_all_hotspots()
        random.shuffle(all_hotspots)
        return all_hotspots


# 全局单例
hotspots_loader = HotspotsLoader()
