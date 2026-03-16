import json
import random
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from app.clients.backend_api import backend_client
from app.schemas.models import AgentInfo, AgentStatus

logger = logging.getLogger("agent_service")

# ============================================================
# 提问权重 & 回答概率（设计文档 第二、三章）
# ============================================================

QUESTIONER_WEIGHT = {
    "high": 3,
    "medium": 2,
    "low": 1,
}

ANSWER_PROBABILITY = {
    "high": 0.8,
    "medium": 0.5,
    "low": 0.15,
}


class AgentManager:
    """Agent 管理器（配额制提问 + 系统必答/用户概率回答）"""

    def __init__(self):
        self.agents: List[AgentInfo] = []
        self.state_file = Path("data/agent_state.json")
        self._lock = asyncio.Lock()

        # 提问配额（由 allocate_question_quota 分配）
        self._quota: Dict[str, int] = {}

        # 系统 Agent 人设映射（本地 persona 标签，仅用于未设 system_prompt 时降级）
        self.agent_configs = [
            {"username": "路过一阵风", "persona": "短评路人型"},
            {"username": "先厘清再讨论", "persona": "逻辑思辨型"},
            {"username": "不正经观察员", "persona": "幽默吐槽型"},
            {"username": "普通人日记", "persona": "温和型"},
            {"username": "情绪稳定练习生", "persona": "情绪+理性型"},
            {"username": "冷静一点点", "persona": "降温反焦虑型"},
            {"username": "踩坑记录本", "persona": "过来人经验型"},
            {"username": "想问清楚", "persona": "善问型"},
            {"username": "温柔有棱角", "persona": "共情但有边界型"},
            {"username": "我只是不同意", "persona": "克制反对派"},
            {"username": "我去查一查", "persona": "资料核对型"},
            {"username": "比喻收藏家", "persona": "脑洞类比型"},
        ]

    async def initialize(self) -> List[AgentInfo]:
        """
        初始化 Agents（从后端内部 API 获取完整配置）

        解析 raw_config 中的 activity_level，读取 system_prompt、is_system、expressiveness
        """
        logger.info("🔄 开始初始化 Agents...")
        self.agents.clear()

        # persona 映射（本地降级用）
        persona_map = {c["username"]: c["persona"] for c in self.agent_configs}

        try:
            agents_data = await backend_client.get_active_agents()
            logger.info(f"📂 从后端获取了 {len(agents_data)} 个 Agent")

            for agent_data in agents_data:
                username = agent_data["name"]

                # 解析 raw_config 中的 activity_level
                activity_level = "medium"
                raw_config_str = agent_data.get("raw_config", "")
                if raw_config_str:
                    try:
                        raw_config = (
                            json.loads(raw_config_str)
                            if isinstance(raw_config_str, str)
                            else raw_config_str
                        )
                        activity_level = raw_config.get("activity_level", "medium")
                    except (json.JSONDecodeError, TypeError):
                        pass

                agent = AgentInfo(
                    username=username,
                    user_id=agent_data.get("id"),
                    role="agent",
                    # 优先使用后端内部接口下发的 JWT；无则回退旧字段
                    token=agent_data.get("jwt_token") or agent_data.get("api_key"),
                    token_expires_at=None,
                    persona=persona_map.get(username, "未知"),
                    system_prompt=agent_data.get("system_prompt", ""),
                    activity_level=activity_level,
                    is_system=agent_data.get("is_system", False),
                    expressiveness=agent_data.get("expressiveness", "balanced"),
                    stats={},
                )
                self.agents.append(agent)
                logger.info(
                    f"  ✓ {username} (id={agent.user_id}) "
                    f"system={agent.is_system} "
                    f"activity={agent.activity_level} "
                    f"prompt={'有' if agent.system_prompt else '无'}"
                )

        except Exception as e:
            logger.error(f"❌ 获取 Agent 列表失败: {e}")
            for config in self.agent_configs:
                agent = AgentInfo(
                    username=config["username"],
                    persona=config["persona"],
                    is_system=True,
                    activity_level="medium",
                    stats={},
                )
                self.agents.append(agent)
                logger.warning(f"  ⚠️  {config['username']} - 降级到本地配置")

        logger.info(f"✅ Agent 初始化完成！共 {len(self.agents)} 个 Agent")
        return self.agents

    # ============================================================
    # 热加载：增量同步 Agent 列表（支持运行中新增/删除/更新）
    # ============================================================

    async def refresh_agents(self):
        """
        增量同步 Agent 列表（热加载）。

        - 新增的 Agent → 追加到列表
        - 删除的 Agent → 从列表移除
        - 已有的 Agent → 更新 token/prompt/config，保留 stats
        - 若后端不可达 → 静默保持现有列表，不中断运行
        """
        try:
            agents_data = await backend_client.get_active_agents()
        except Exception as e:
            logger.warning(f"⚠️ Agent 热加载失败（后端不可达），保持现有列表: {e}")
            return

        persona_map = {c["username"]: c["persona"] for c in self.agent_configs}

        # 构建 username → 现有 AgentInfo 的索引（用于保留 stats）
        existing_map = {a.username: a for a in self.agents}

        # 构建新列表
        remote_usernames = set()
        new_agents: List[AgentInfo] = []

        for agent_data in agents_data:
            username = agent_data["name"]
            remote_usernames.add(username)

            # 解析 activity_level
            activity_level = "medium"
            raw_config_str = agent_data.get("raw_config", "")
            if raw_config_str:
                try:
                    raw_config = (
                        json.loads(raw_config_str)
                        if isinstance(raw_config_str, str)
                        else raw_config_str
                    )
                    activity_level = raw_config.get("activity_level", "medium")
                except (json.JSONDecodeError, TypeError):
                    pass

            # 如果已存在，保留 stats
            old = existing_map.get(username)
            stats = old.stats if old else {}

            agent = AgentInfo(
                username=username,
                user_id=agent_data.get("id"),
                role="agent",
                token=agent_data.get("jwt_token") or agent_data.get("api_key"),
                token_expires_at=None,
                persona=persona_map.get(username, agent_data.get("name", "未知")),
                system_prompt=agent_data.get("system_prompt", ""),
                activity_level=activity_level,
                is_system=agent_data.get("is_system", False),
                expressiveness=agent_data.get("expressiveness", "balanced"),
                stats=stats,
            )
            new_agents.append(agent)

        # 日志：新增/删除
        old_usernames = set(existing_map.keys())
        added = remote_usernames - old_usernames
        removed = old_usernames - remote_usernames

        if added:
            logger.info(f"🆕 热加载：新增 Agent: {', '.join(added)}")
        if removed:
            logger.info(f"🗑️ 热加载：移除 Agent: {', '.join(removed)}")
        if not added and not removed:
            logger.debug("🔄 热加载：Agent 列表无变化")

        self.agents = new_agents

    # ============================================================
    # 提问配额分配（设计文档 第二章）
    # ============================================================

    def allocate_question_quota(self, total_hotspots: int) -> Dict[str, int]:
        """
        根据未处理热点总数，按 activity_level 权重分配提问配额。
        系统 agent 和用户 agent 平等参与。
        """
        if not self.agents:
            return {}

        total_weight = sum(
            QUESTIONER_WEIGHT.get(a.activity_level, 2) for a in self.agents
        )

        quota: Dict[str, int] = {}
        allocated = 0
        for agent in self.agents:
            weight = QUESTIONER_WEIGHT.get(agent.activity_level, 2)
            count = (
                int(total_hotspots * weight / total_weight) if total_weight > 0 else 0
            )
            quota[agent.username] = count
            allocated += count

        # 剩余热点随机分配
        remaining = total_hotspots - allocated
        if remaining > 0:
            lucky = random.sample(self.agents, min(remaining, len(self.agents)))
            for agent in lucky:
                quota[agent.username] += 1

        self._quota = quota
        logger.info(f"📊 提问配额分配完成 ({total_hotspots} 热点): {quota}")
        return quota

    def get_questioner_with_quota(self) -> Optional[AgentInfo]:
        """按配额选提问者（配额用完则跳过）"""
        available = [a for a in self.agents if self._quota.get(a.username, 0) > 0]
        if not available:
            return None

        weights = [QUESTIONER_WEIGHT.get(a.activity_level, 2) for a in available]
        selected = random.choices(available, weights=weights, k=1)[0]

        self._quota[selected.username] -= 1
        return selected

    # ============================================================
    # 回答者选择（设计文档 第三章）
    # ============================================================

    def get_answerers(self, questioner_name: str = None) -> List[AgentInfo]:
        """
        混合筛选回答者：
        - 系统 agent (is_system=true) 全部必答
        - 用户 agent (is_system=false) 按 activity_level 概率筛选
        - 排除提问者
        """
        available = [a for a in self.agents if a.username != questioner_name]

        # 系统 agent：无条件全选（NPC 必须发言）
        system_agents = [a for a in available if a.is_system]

        # 用户 agent：概率筛选
        user_agents = [a for a in available if not a.is_system]
        willing_users = []
        for agent in user_agents:
            prob = ANSWER_PROBABILITY.get(agent.activity_level, 0.5)
            if random.random() < prob:
                willing_users.append(agent)

        # 合并并打乱顺序
        answerers = system_agents + willing_users
        random.shuffle(answerers)

        logger.info(
            f"选出 {len(answerers)} 个回答者："
            f"{len(system_agents)} 个系统agent（必答）+ "
            f"{len(willing_users)}/{len(user_agents)} 个用户agent"
        )

        return answerers

    # ============================================================
    # 兼容旧接口（逐步废弃）
    # ============================================================

    def get_questioner(self) -> Optional[AgentInfo]:
        """随机获取一个提问 Agent（兼容旧调用）"""
        return self.get_questioner_with_quota() or (
            random.choice(self.agents) if self.agents else None
        )

    def get_random_agents(
        self, count: int = 1, exclude: List[str] = None
    ) -> List[AgentInfo]:
        """随机获取指定数量的 Agent"""
        available = self.agents.copy()
        if exclude:
            available = [a for a in available if a.username not in exclude]
        if len(available) >= count:
            return random.sample(available, count)
        return available

    # ============================================================
    # 状态管理
    # ============================================================

    def get_agent_status(self) -> List[AgentStatus]:
        """获取所有 Agent 的状态"""
        status_list = []
        for agent in self.agents:
            is_active = agent.token is not None
            token_valid = (
                (
                    agent.token_expires_at is not None
                    and agent.token_expires_at > datetime.now()
                )
                if is_active
                else False
            )

            status = AgentStatus(
                username=agent.username,
                role=agent.role,
                is_active=is_active,
                token_valid=token_valid,
                questions_created=agent.stats.get("questions_created", 0),
                answers_created=agent.stats.get("answers_created", 0),
                last_activity=None,
            )
            status_list.append(status)
        return status_list

    async def update_stats(
        self,
        username: str,
        question_created: bool = False,
        answer_created: bool = False,
    ):
        """更新 Agent 统计"""
        async with self._lock:
            for agent in self.agents:
                if agent.username == username:
                    if question_created:
                        agent.stats["questions_created"] = (
                            agent.stats.get("questions_created", 0) + 1
                        )
                        agent.stats["last_question_at"] = datetime.now().isoformat()
                    if answer_created:
                        agent.stats["answers_created"] = (
                            agent.stats.get("answers_created", 0) + 1
                        )
                        agent.stats["last_answer_at"] = datetime.now().isoformat()
                    break
            self._save_state()

    def _load_state(self) -> Dict:
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        agent["username"]: agent for agent in data.get("agents", [])
                    }
            except Exception as e:
                print(f"加载状态文件失败: {e}")
        return {}

    def _save_state(self):
        """保存状态到文件"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "agents": [
                {
                    "username": a.username,
                    "user_id": a.user_id,
                    "token": a.token,
                    "token_expires_at": (
                        a.token_expires_at.isoformat() if a.token_expires_at else None
                    ),
                    "role": a.role,
                    "persona": a.persona,
                    "stats": a.stats,
                }
                for a in self.agents
            ],
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# 全局单例
agent_manager = AgentManager()
