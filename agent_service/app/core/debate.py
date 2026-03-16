import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.clients.backend_api import backend_client
from app.clients.llm_client import llm_client
from app.clients.redis_client import redis_client
from app.config import settings
from app.core.agent_manager import agent_manager, ANSWER_PROBABILITY
from app.core.memory import agent_memory
from app.prompts.debate import (
    DEBATE_HOST_SUMMARY_PROMPT,
    DEBATE_OPENING_PROMPT,
    DEBATE_REBUTTAL_PROMPT,
    DEBATE_SUMMARY_PROMPT,
    DEBATE_TOPIC_CANDIDATES_PROMPT,
    DEBATE_TOPIC_SELECTOR_PROMPT,
)

logger = logging.getLogger("agent_service")

MAX_HISTORY = 500
MAX_CYCLE_COUNT = 50  # 防DoS上限
DEBATE_STATE_KEY = "debate:active_state"  # Redis key for persisting debate state

DEFAULT_STANCES = [
    "强烈支持",
    "强烈反对",
    "支持但保留",
    "反对并质疑",
    "中立审视",
    "搅局拱火",
    "理性质疑",
    "经验主义",
    "悲观预警",
    "乐观推动",
]

# 立场阵营分类：反驳时只针对对立阵营
SUPPORT_STANCES = {"强烈支持", "支持但保留", "乐观推动"}
OPPOSE_STANCES = {"强烈反对", "反对并质疑", "悲观预警"}


class DebateOrchestrator:
    def __init__(self):
        self.is_running = False
        self.current_cycle = 0
        self.total_cycles = 0
        self.history: List[Dict] = []
        self._stop_event: Optional[asyncio.Event] = None

    # ================================================================
    # 辩论状态持久化（Redis）：支持停止后恢复
    # ================================================================

    async def _save_debate_state(self, state: Dict):
        """将当前辩论进度持久化到 Redis，用于崩溃/停止后恢复"""
        try:
            await redis_client.hset_json(DEBATE_STATE_KEY, "state", state)
            await redis_client.expire(DEBATE_STATE_KEY, 86400 * 7)  # 7天过期
        except Exception as e:
            logger.warning(f"保存辩论状态失败: {e}")

    async def _load_debate_state(self) -> Optional[Dict]:
        """从 Redis 加载上次未完成的辩论状态"""
        try:
            state = await redis_client.hget_json(DEBATE_STATE_KEY, "state")
            return state if isinstance(state, dict) else None
        except Exception as e:
            logger.warning(f"加载辩论状态失败: {e}")
            return None

    async def _clear_debate_state(self):
        """清除已完成的辩论状态"""
        try:
            r = await redis_client._get_conn()
            await r.delete(DEBATE_STATE_KEY)
        except Exception as e:
            logger.warning(f"清除辩论状态失败: {e}")

    # ================================================================
    # 参与者选取：系统agent必选 + 用户agent概率筛选
    # ================================================================

    def _pick_debaters(self, proposer, initial_cap: int):
        """
        选取辩论初始参与者（与 get_answerers 一致的双层筛选逻辑）：
        - 系统 agent (is_system=true)：全部参与（NPC 必选）
        - 用户 agent (is_system=false)：按 activity_level 概率筛选
        - 排除提问者
        - initial_cap 仅限制初始选取的总人数，不阻止后续动态加入
        """
        all_agents = [
            a for a in agent_manager.agents if a.username != proposer.username
        ]
        if not all_agents:
            return []

        # 系统 agent：全部必选
        system_agents = [a for a in all_agents if a.is_system]

        # 用户 agent：按 activity_level 概率筛选
        user_agents = [a for a in all_agents if not a.is_system]
        willing_users = []
        for agent in user_agents:
            prob = ANSWER_PROBABILITY.get(agent.activity_level, 0.5)
            if random.random() < prob:
                willing_users.append(agent)

        combined = system_agents + willing_users
        random.shuffle(combined)

        # initial_cap 仅约束初始人数，不阻止后续动态加入
        if len(combined) > initial_cap:
            # 优先保留系统agent，裁剪用户agent
            if len(system_agents) >= initial_cap:
                combined = system_agents[:initial_cap]
            else:
                remaining_cap = initial_cap - len(system_agents)
                combined = system_agents + willing_users[:remaining_cap]

        logger.info(
            f"初始选取 {len(combined)} 个辩论者："
            f"{len([a for a in combined if a.is_system])} 个系统agent + "
            f"{len([a for a in combined if not a.is_system])} 个用户agent"
        )
        return combined

    async def _generate_topic(self, proposer) -> str:
        recent_topics = [
            h.get("topic", "") for h in self.history[-50:] if h.get("topic")
        ]
        if proposer.user_id:
            recent_topics = (await agent_memory.get_recent_topics(proposer.user_id))[
                :30
            ] + recent_topics[:20]

        candidates_text = await llm_client.generate(
            prompt=DEBATE_TOPIC_CANDIDATES_PROMPT.format(
                agent_name=proposer.username,
                system_prompt=proposer.system_prompt or proposer.persona,
                recent_topics="\n".join(f"- {x}" for x in recent_topics[:30]) or "- 无",
            ),
            system_prompt="你是高质量中文辩题生成器。",
            max_tokens=600,
        )

        lines = []
        for line in candidates_text.splitlines():
            line = line.strip().lstrip("- ")
            if not line:
                continue
            if line[0].isdigit() and "." in line:
                line = line.split(".", 1)[1].strip()
            lines.append(line)

        if not lines:
            return "AI 五年内会取代大多数白领，继续读大学已经没有意义了吗？"

        selected = await llm_client.generate(
            prompt=DEBATE_TOPIC_SELECTOR_PROMPT.format(
                candidates="\n".join(f"- {x}" for x in lines[:6])
            ),
            system_prompt="你是最懂社区话题传播性的选题总监。",
            max_tokens=120,
        )
        return selected.strip().strip('"') or lines[0]

    def _build_stance_map_text(self, stances: Dict[str, str]) -> str:
        """构建各方立场速览文本，明确标注每个Agent持什么立场"""
        lines = []
        for agent_name, stance in stances.items():
            lines.append(f"- {agent_name}: {stance}")
        return "\n".join(lines) or "- 暂无"

    @staticmethod
    def _get_stance_camp(stance: str) -> str:
        """将立场分类为 support / oppose / neutral"""
        if stance in SUPPORT_STANCES:
            return "support"
        if stance in OPPOSE_STANCES:
            return "oppose"
        return "neutral"

    def _select_rebuttal_target(
        self, speaker_username: str, speaker_stance: str, all_messages: List[Dict]
    ) -> Optional[Dict]:
        """
        从对立阵营中按时间权重随机选取反驳目标。
        - 支持方只反驳反对方的发言
        - 反对方只反驳支持方的发言
        - 中立方可反驳任何人
        若对立阵营无可用目标，降级为反驳任何非自己的发言。
        """
        candidates = [m for m in all_messages if m["agent"] != speaker_username]
        if not candidates:
            return None

        speaker_camp = self._get_stance_camp(speaker_stance)

        if speaker_camp == "support":
            opposing = [
                m for m in candidates if self._get_stance_camp(m["stance"]) == "oppose"
            ]
        elif speaker_camp == "oppose":
            opposing = [
                m for m in candidates if self._get_stance_camp(m["stance"]) == "support"
            ]
        else:
            opposing = candidates

        pool = opposing if opposing else candidates

        # 时间权重：越靠后的消息越可能被选中（线性递增权重）
        weights = list(range(1, len(pool) + 1))
        return random.choices(pool, weights=weights, k=1)[0]

    async def _summarize_history(self, topic: str, raw_history: List[Dict]) -> str:
        compact = []
        for item in raw_history[-30:]:
            agent_name = item.get("agent", "?")
            content = item.get("content", "")
            msg_type = item.get("type", "")
            target = item.get("target", "")
            if target:
                compact.append(f"[{agent_name} → @{target}] {content}")
            else:
                compact.append(f"[{agent_name}]({msg_type}) {content}")

        summary = await llm_client.generate(
            prompt=DEBATE_SUMMARY_PROMPT.format(
                topic=topic, history="\n".join(compact)
            ),
            system_prompt="你是辩论记录压缩器，输出简洁、结构化摘要。必须保留每个发言人的名字。",
            max_tokens=500,
        )
        return summary.strip()

    def _is_stopped(self) -> bool:
        """检查是否已收到停止信号"""
        return self._stop_event is not None and self._stop_event.is_set()

    async def _interruptible_sleep(self, seconds: int):
        """可被stop中断的sleep"""
        if self._stop_event is None:
            await asyncio.sleep(seconds)
            return
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass

    async def _process_one_debate(self, cycle: int, total: int) -> Dict:
        if self._is_stopped():
            return {
                "question_id": None,
                "topic": "",
                "messages": 0,
                "errors": ["已停止"],
            }

        await agent_manager.refresh_agents()

        proposer = (
            agent_manager.get_questioner_with_quota() or agent_manager.get_questioner()
        )
        if not proposer:
            return {
                "question_id": None,
                "topic": "",
                "messages": 0,
                "errors": ["没有可用Agent"],
            }

        topic = await self._generate_topic(proposer)

        if self._is_stopped():
            return {
                "question_id": None,
                "topic": topic,
                "messages": 0,
                "errors": ["已停止"],
            }

        question_resp = await backend_client.create_question(
            token=proposer.token,
            title=topic,
            content=f"圆桌辩论：{topic}",
            question_type="debate",
        )
        question_id = question_resp["id"]

        # 参与者：系统agent必选 + 用户agent概率筛选，initial_cap仅限初始人数
        initial_cap = settings.debate_participants_max
        debaters = self._pick_debaters(proposer, initial_cap)
        if not debaters:
            return {
                "question_id": question_id,
                "topic": topic,
                "messages": 0,
                "errors": ["没有回答者"],
            }

        logger.info(f"🎙️ 辩论 #{cycle} 参与者: {[d.username for d in debaters]}")

        # 分配立场：循环分配，超出预设立场数量的agent也能分到
        stances = {}
        for i, agent in enumerate(debaters):
            stances[agent.username] = DEFAULT_STANCES[i % len(DEFAULT_STANCES)]

        stance_map_text = self._build_stance_map_text(stances)

        answers = []  # 存储 {answer_id, agent, stance, content}
        viewpoints = []
        errors = []
        raw_history = []

        # === 开场阶段 ===
        for debater in debaters:
            if self._is_stopped():
                break

            prompt = DEBATE_OPENING_PROMPT.format(
                topic=topic,
                stance=stances[debater.username],
                existing_viewpoints="\n".join(f"- {v}" for v in viewpoints) or "- 无",
            )
            content = await llm_client.generate(
                prompt=prompt,
                system_prompt=debater.system_prompt or debater.persona,
                max_tokens=500,
            )
            try:
                answer_resp = await backend_client.create_answer(
                    token=debater.token,
                    question_id=question_id,
                    content=content.strip(),
                )
                answer_id = answer_resp.get("id")
                answers.append(
                    {
                        "answer_id": answer_id,
                        "agent": debater.username,
                        "stance": stances[debater.username],
                        "content": content.strip(),
                    }
                )
                viewpoints.append(f"{debater.username}: {content.strip()[:80]}")
                raw_history.append(
                    {
                        "agent": debater.username,
                        "type": "opening",
                        "content": content.strip(),
                    }
                )
            except Exception as e:
                logger.error(f"{debater.username} 开场失败: {e}")
                errors.append(f"{debater.username} 开场失败: {e}")

        if not answers:
            return {
                "question_id": question_id,
                "topic": topic,
                "messages": len(raw_history),
                "errors": errors,
                "participants": [d.username for d in debaters],
            }

        rolling_summary = await self._summarize_history(topic, raw_history)

        # === 反驳轮次（已临时关闭） ===
        # 需求：当前阶段不展示/不生成辩论评论（rebuttal）
        # 影响：
        # 1) 不再调用 create_comment；
        # 2) raw_history 仅包含 opening + summary；
        # 3) 记忆逻辑无需额外改动（仍只写入 topic）。
        # 如需恢复，取消注释原反驳轮次逻辑即可。
        logger.info("🧪 辩论反驳轮次已临时关闭：仅保留开场发言与主持总结")

        # === 主持人总结 ===
        if not self._is_stopped():
            # 最终摘要
            rolling_summary = await self._summarize_history(topic, raw_history)

            host_summary = await llm_client.generate(
                prompt=DEBATE_HOST_SUMMARY_PROMPT.format(
                    topic=topic, rolling_summary=rolling_summary or "暂无"
                ),
                system_prompt=(proposer.system_prompt or proposer.persona),
                max_tokens=420,
            )

            try:
                await backend_client.create_answer(
                    token=proposer.token,
                    question_id=question_id,
                    content=host_summary.strip(),
                )
                raw_history.append(
                    {
                        "agent": proposer.username,
                        "type": "summary",
                        "content": host_summary.strip(),
                    }
                )
            except Exception as e:
                logger.error(f"主持人总结失败: {e}")
                errors.append(f"主持人总结失败: {e}")

        if proposer.user_id:
            await agent_memory.add_topic(proposer.user_id, topic)

        return {
            "question_id": question_id,
            "topic": topic,
            "messages": len(raw_history),
            "errors": errors,
            "participants": [d.username for d in debaters],
        }

    async def start_debate_session(self, cycle_count: int = 1, resume: bool = False):
        if self.is_running:
            logger.warning("⚠️ 辩论会话已在运行中")
            return

        cycle_count = min(cycle_count, MAX_CYCLE_COUNT)
        self.is_running = True
        self.current_cycle = 0
        self.total_cycles = cycle_count
        self._stop_event = asyncio.Event()

        await agent_manager.initialize()
        agent_manager.allocate_question_quota(cycle_count)

        delay_min, delay_max = settings.debate_interval

        # 恢复模式：从 Redis 加载上次未完成的进度
        start_from = 0
        if resume:
            saved = await self._load_debate_state()
            if saved and saved.get("total_cycles") == cycle_count:
                start_from = saved.get("completed_cycles", 0)
                logger.info(
                    f"🔄 恢复辩论会话，从第 {start_from + 1} 场继续（共 {cycle_count} 场）"
                )
            else:
                logger.info("🆕 没有可恢复的辩论状态，从头开始")

        try:
            for i in range(start_from, cycle_count):
                if self._is_stopped():
                    logger.info("⏹️ 辩论会话被用户停止")
                    # 保存进度以便下次恢复
                    await self._save_debate_state(
                        {
                            "total_cycles": cycle_count,
                            "completed_cycles": i,
                            "stopped_at": datetime.now().isoformat(),
                        }
                    )
                    break

                self.current_cycle = i + 1
                logger.info(f"🎯 开始第 {i+1}/{cycle_count} 场辩论")
                result = await self._process_one_debate(i + 1, cycle_count)
                self.history.append(
                    {
                        "id": len(self.history) + 1,
                        "cycle": i + 1,
                        "topic": result.get("topic", ""),
                        "question_id": result.get("question_id"),
                        "messages": result.get("messages", 0),
                        "participants": result.get("participants", []),
                        "errors": result.get("errors", []),
                        "created_at": datetime.now().isoformat(),
                    }
                )
                if len(self.history) > MAX_HISTORY:
                    self.history = self.history[-MAX_HISTORY:]

                # 保存当前进度
                await self._save_debate_state(
                    {
                        "total_cycles": cycle_count,
                        "completed_cycles": i + 1,
                        "last_topic": result.get("topic", ""),
                        "updated_at": datetime.now().isoformat(),
                    }
                )

                if i < cycle_count - 1 and not self._is_stopped():
                    await self._interruptible_sleep(
                        random.randint(delay_min, delay_max)
                    )
            else:
                # 全部完成，清除状态
                await self._clear_debate_state()
                logger.info(f"✅ 辩论会话全部完成（{cycle_count} 场）")

        finally:
            self.is_running = False
            self._stop_event = None

    def stop(self):
        """停止辩论会话（通过Event信号中断sleep和循环）"""
        if self._stop_event:
            self._stop_event.set()
        self.is_running = False

    def get_status(self) -> Dict:
        return {
            "status": "running" if self.is_running else "idle",
            "current_cycle": self.current_cycle,
            "total_cycles": self.total_cycles,
            "history_count": len(self.history),
            "history": self.history[-50:],
        }


debate_orchestrator = DebateOrchestrator()
