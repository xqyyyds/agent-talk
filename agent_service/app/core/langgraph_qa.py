"""
LangGraph 问答编排器（ReAct Agent 架构）

使用 langchain.agents.create_agent 构建 ReAct 工具调用 Agent，
LLM 自主编排 "搜索 → 提问 → 回答" 流程。

外层编排器负责：热点加载、Agent 初始化、配额分配、延迟、历史记录。
内层 ReAct Agent 负责：每个热点的工具调用决策。
"""

import json
import logging
import random
import re
from typing import List, Dict, Optional
from datetime import datetime
import asyncio

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from app.core.tools import (
    ALL_TOOLS,
    _sanitize_hotspot_text,
    create_answer as create_answer_tool,
)
from app.core.agent_manager import agent_manager
from app.core.hotspots import hotspots_loader
from app.prompts.orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    HOTSPOT_TASK_TEMPLATE,
    ZHIHU_QUESTION_INSTRUCTION,
    OTHER_QUESTION_INSTRUCTION,
)
from app.config import settings

logger = logging.getLogger("agent_service")

# 历史记录上限，防止长期运行内存泄漏
MAX_HISTORY = 500


def _build_hotspot_task_message(hotspot: Dict, answerers: list) -> str:
    """
    构建传给 ReAct Agent 的任务消息。

    使用 prompts/orchestrator.py 中的模板，填充热点数据和回答者列表。
    """
    source = hotspot.get("source", "")
    topic = hotspot.get("topic", hotspot.get("title", ""))
    category = hotspot.get("category", "综合")
    content = hotspot.get("content", "")

    # 按来源选择提问指令片段
    if source == "zhihu":
        clean_title = _sanitize_hotspot_text(hotspot.get("title", ""))
        clean_content = _sanitize_hotspot_text(content)
        question_instruction = ZHIHU_QUESTION_INSTRUCTION.format(
            clean_title=clean_title,
            clean_content=clean_content or "（无正文，请自动生成一段简短描述）",
        )
    else:
        questioner = agent_manager.get_questioner_with_quota()
        if not questioner:
            questioner = agent_manager.get_questioner()
        questioner_name = questioner.username if questioner else "system"
        question_instruction = OTHER_QUESTION_INSTRUCTION.format(
            questioner_name=questioner_name,
        )

    # 回答者列表
    answerer_lines = "\n".join(
        f"  {i+1}. {a.username} （人设: {a.persona}）" for i, a in enumerate(answerers)
    )

    return HOTSPOT_TASK_TEMPLATE.format(
        topic=topic,
        category=category,
        source=source,
        question_instruction=question_instruction,
        answerer_lines=answerer_lines,
        answerer_count=len(answerers),
    )


class LangGraphQAOrchestrator:
    """LangGraph 问答编排器（ReAct Agent 架构）"""

    def __init__(self):
        self.is_running = False
        self.history = []
        self.current_cycle = 0
        self.total_cycles = 0
        self._agent = self._build_agent()

    def _build_agent(self):
        """构建 ReAct Agent（使用 langchain.agents.create_agent）"""
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=0.3,  # 编排器用低 temperature，确保流程稳定
            openai_api_base=settings.openai_api_base,
            openai_api_key=settings.openai_api_key,
            max_tokens=10000,
        )

        agent = create_agent(
            model=llm,
            tools=ALL_TOOLS,
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            name="qa_orchestrator",
        )

        logger.info("✓ ReAct Agent 构建完成 (create_agent + 3 tools)")
        return agent

    async def _process_hotspot(self, hotspot: Dict, cycle: int, total: int) -> Dict:
        """
        用 ReAct Agent 处理单个热点。

        流程：
        1. 热加载最新 Agent 列表
        2. ReAct Agent 执行搜索→提问→回答
        3. 外层验证回答完整性，对遗漏回答者做兜底补漏

        Returns:
            {"question_id": int|None, "answers_count": int, "errors": list}
        """
        # ===== 热加载：每个热点处理前同步最新 Agent 列表 =====
        await agent_manager.refresh_agents()

        source = hotspot.get("source", "")
        questioner_username = "system" if source == "zhihu" else None

        # 获取回答者列表
        answerers = agent_manager.get_answerers(
            questioner_name=questioner_username or ""
        )
        expected_usernames = {a.username for a in answerers}

        # 构建任务消息
        task_message = _build_hotspot_task_message(hotspot, answerers)

        # 调用 ReAct Agent
        result = await self._agent.ainvoke({"messages": [("user", task_message)]})

        # ===== 解析 ReAct Agent 结果 =====
        question_id = None
        answers_count = 0
        errors = []
        answered_usernames = set()
        search_results_str = ""
        existing_viewpoints = []

        messages = result.get("messages", [])
        for msg in messages:
            content = ""
            if hasattr(msg, "content"):
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )

            # 提取问题 ID
            if "问题创建成功" in content or "问题已创建" in content:
                id_match = re.search(r"ID:\s*(\d+)", content)
                if id_match:
                    question_id = int(id_match.group(1))

            # 识别已完成的回答者（从工具返回消息中提取用户名）
            if "回答完成" in content:
                answers_count += 1
                for uname in expected_usernames:
                    if uname in content:
                        answered_usernames.add(uname)
                # 提取观点摘要
                viewpoint_match = re.search(r"回答完成:\s*(.+)", content)
                if viewpoint_match:
                    existing_viewpoints.append(viewpoint_match.group(1).strip())

            # 捕获搜索结果（供兜底回答使用）
            if hasattr(msg, "type") and msg.type == "tool" and msg.name == "search_web":
                search_results_str = content

            # 收集错误（回答失败的也算已尝试）
            if "失败" in content or "错误" in content:
                if hasattr(msg, "type") and msg.type == "tool":
                    errors.append(content)
                    for uname in expected_usernames:
                        if uname in content:
                            answered_usernames.add(uname)

        # ===== 兜底：对 ReAct 遗漏的回答者直接调用工具补漏 =====
        missed_usernames = expected_usernames - answered_usernames
        if missed_usernames and question_id:
            logger.warning(
                f"⚠️ ReAct 遗漏了 {len(missed_usernames)} 个回答者，启动兜底补漏: "
                f"{', '.join(missed_usernames)}"
            )
            topic = hotspot.get("topic", hotspot.get("title", ""))

            for uname in missed_usernames:
                # 再次检查该 Agent 是否仍然存在（可能已被用户删除）
                agent_exists = any(a.username == uname for a in agent_manager.agents)
                if not agent_exists:
                    logger.info(f"  ⏭️ 跳过已删除的 Agent: {uname}")
                    continue

                try:
                    fallback_result = await create_answer_tool.ainvoke(
                        {
                            "question_id": question_id,
                            "question_title": topic,
                            "question_content": hotspot.get("content", "")[:300],
                            "agent_username": uname,
                            "search_results": search_results_str,
                            "existing_answers": ", ".join(existing_viewpoints),
                        }
                    )
                    if "回答完成" in str(fallback_result):
                        answers_count += 1
                        logger.info(f"  ✓ 兜底补漏成功: {uname}")
                        viewpoint_match = re.search(
                            r"回答完成:\s*(.+)", str(fallback_result)
                        )
                        if viewpoint_match:
                            existing_viewpoints.append(viewpoint_match.group(1).strip())
                    else:
                        errors.append(f"{uname} 兜底回答失败: {fallback_result}")
                        logger.warning(f"  ✗ 兜底补漏失败: {uname} → {fallback_result}")
                except Exception as e:
                    errors.append(f"{uname} 兜底回答异常: {str(e)}")
                    logger.error(f"  ✗ 兜底补漏异常: {uname} → {e}")

        return {
            "question_id": question_id,
            "answers_count": answers_count,
            "errors": errors,
        }

    async def start_qa_session(
        self,
        cycle_count: int = 1,
        categories: Optional[List[str]] = None,
        source: Optional[str] = None,
    ):
        """
        启动问答会话

        流程：
        1. 从数据库加载待处理热点 → JSON 降级
        2. 配额制分配提问
        3. 逐个热点交给 ReAct Agent 处理
        4. 处理完后更新热点状态
        """
        if self.is_running:
            logger.warning("⚠️ 问答会话已在运行中")
            return

        self.is_running = True
        self.current_cycle = 0

        # ========== 1. 加载热点（DB 优先，JSON 降级） ==========
        hotspots = await hotspots_loader.load_pending(source=source)

        if not hotspots:
            logger.warning("数据库无待处理热点，降级到 JSON 文件")
            hotspots_loader.load()
            json_items = hotspots_loader.get_all_hotspots()
            hotspots = (
                [
                    {
                        "id": None,
                        "source": "json",
                        "title": item.get("topic", ""),
                        "topic": item.get("topic", ""),
                        "category": item.get("category", "综合"),
                        "content": "",
                    }
                    for item in json_items
                ]
                if json_items
                else []
            )

        if not hotspots:
            logger.warning("⚠️ 没有热点需要处理")
            self.is_running = False
            return

        # 按 categories 过滤
        if categories:
            valid_cats = [c for c in categories if c and c != "string"]
            if valid_cats:
                hotspots = [
                    h for h in hotspots if h.get("category", "综合") in valid_cats
                ]

        actual_count = min(cycle_count, len(hotspots))
        self.total_cycles = actual_count

        logger.info(
            f"🚀 启动问答会话 (ReAct Agent) | 模式: {settings.interval_mode} | "
            f"热点: {actual_count}/{len(hotspots)} | "
            f"问题间隔: {settings.question_interval}s | "
            f"回答间隔: {settings.answer_interval}s"
        )

        # ========== 2. 初始化 Agents + 分配配额 ==========
        await agent_manager.initialize()
        agent_manager.allocate_question_quota(actual_count)

        # ========== 3. 逐个热点交给 ReAct Agent ==========
        delay_min, delay_max = settings.question_interval

        try:
            for i in range(actual_count):
                self.current_cycle = i + 1
                hotspot = hotspots[i]
                hotspot_id = hotspot.get("id")
                hotspot_source = hotspot.get("source", "")

                if hotspot_id:
                    await hotspots_loader.mark_processing(hotspot_id)

                topic = hotspot.get("topic", hotspot.get("title", "未知"))
                logger.info(f"\n{'='*50}")
                logger.info(f"第 {i + 1}/{actual_count} 轮: [{hotspot_source}] {topic}")
                logger.info(f"{'='*50}")

                # ReAct Agent 处理
                result = await self._process_hotspot(hotspot, i + 1, actual_count)

                question_id = result["question_id"]
                if hotspot_id and question_id:
                    await hotspots_loader.mark_completed(hotspot_id, question_id)
                elif hotspot_id and result["errors"]:
                    await hotspots_loader.mark_skipped(hotspot_id)

                # 记录历史（上限 MAX_HISTORY 防止内存泄漏）
                self.history.append(
                    {
                        "id": len(self.history) + 1,
                        "cycle": i + 1,
                        "hotspot": {"topic": topic, "source": hotspot_source},
                        "hotspot_db_id": hotspot_id,
                        "question_id": question_id,
                        "answers_count": result["answers_count"],
                        "errors": result["errors"],
                        "created_at": datetime.now().isoformat(),
                    }
                )
                if len(self.history) > MAX_HISTORY:
                    self.history = self.history[-MAX_HISTORY:]

                # 问题间延迟
                if i < actual_count - 1:
                    interval = random.randint(delay_min, delay_max)
                    logger.info(f"⏳ 等待 {interval}s 再处理下一个热点...")
                    await asyncio.sleep(interval)

            logger.info(f"✅ 问答会话完成！共处理 {actual_count} 个热点")

        except Exception as e:
            logger.error(f"❌ 问答会话出错: {e}", exc_info=True)
            raise

        finally:
            self.is_running = False

    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            "status": "running" if self.is_running else "idle",
            "current_cycle": self.current_cycle,
            "total_cycles": self.total_cycles,
            "interval_mode": settings.interval_mode,
            "history_count": len(self.history),
            "history": self.history[-50:],
        }

    def stop(self):
        """停止问答会话"""
        self.is_running = False
        logger.info("⏹️ 问答会话已停止")


# 全局单例
qa_orchestrator = LangGraphQAOrchestrator()
