"""
LangGraph QA orchestrator.

This module orchestrates: search -> create question -> create answers.
"""

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from html import unescape
from typing import Dict, List, Optional

from langchain.agents import create_agent

from app.config import settings
from app.core.agent_manager import agent_manager
from app.core.hotspots import hotspots_loader
from app.core.llm_runtime import run_with_llm_failover
from app.core.tools import ALL_TOOLS, _sanitize_hotspot_text, create_answer as create_answer_tool
from app.prompts.orchestrator import (
    HOTSPOT_TASK_TEMPLATE,
    ORCHESTRATOR_SYSTEM_PROMPT,
    OTHER_QUESTION_INSTRUCTION,
    ZHIHU_QUESTION_INSTRUCTION,
)

logger = logging.getLogger("agent_service")

MAX_HISTORY = 500


def _safe_text(text: str) -> str:
    if not text:
        return ""
    cleaned = unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _build_hotspot_task_message(hotspot: Dict, answerers: list) -> str:
    source = hotspot.get("source", "")
    topic = hotspot.get("topic", hotspot.get("title", ""))
    category = hotspot.get("category", "综合")
    content = hotspot.get("content", "")

    if source == "zhihu":
        clean_title = _sanitize_hotspot_text(hotspot.get("title", ""))
        clean_content = _sanitize_hotspot_text(content)
        question_instruction = ZHIHU_QUESTION_INSTRUCTION.format(
            clean_title=clean_title,
            clean_content=clean_content or "（无正文，请自动生成一段简短描述）",
        )
    else:
        questioner = agent_manager.get_questioner_with_quota() or agent_manager.get_questioner()
        questioner_name = questioner.username if questioner else "system"
        question_instruction = OTHER_QUESTION_INSTRUCTION.format(
            questioner_name=questioner_name,
        )

    answerer_lines = "\n".join(
        f"  {i + 1}. {a.username}（人设: {a.persona}）" for i, a in enumerate(answerers)
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
    def __init__(self):
        self.is_running = False
        self.history: list[dict] = []
        self.current_cycle = 0
        self.total_cycles = 0

    def _build_agent_with_llm(self, llm):
        return create_agent(
            model=llm,
            tools=ALL_TOOLS,
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            name="qa_orchestrator",
        )

    async def _invoke_react(self, task_message: str):
        async def _invoke(llm):
            react_agent = self._build_agent_with_llm(llm)
            return await react_agent.ainvoke({"messages": [("user", task_message)]})

        return await run_with_llm_failover(
            scene="orchestrator.react",
            runner=_invoke,
            max_tokens=10000,
            temperature_override=0.3,
        )

    async def _process_hotspot(self, hotspot: Dict, cycle: int, total: int) -> Dict:
        await agent_manager.refresh_agents()

        source = hotspot.get("source", "")
        questioner_username = "system" if source == "zhihu" else ""
        answerers = agent_manager.get_answerers(questioner_name=questioner_username)
        expected_usernames = {a.username for a in answerers}

        task_message = _build_hotspot_task_message(hotspot, answerers)
        result = await self._invoke_react(task_message)

        question_id = None
        answers_count = 0
        errors: list[str] = []
        answered_usernames: set[str] = set()
        search_results_str = ""
        existing_viewpoints: list[str] = []

        messages = result.get("messages", []) if isinstance(result, dict) else []
        for msg in messages:
            content = ""
            if hasattr(msg, "content"):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
            content = _safe_text(content)

            if "问题创建成功" in content or "问题已创建" in content:
                id_match = re.search(r"ID:\s*(\d+)", content)
                if id_match:
                    question_id = int(id_match.group(1))

            if "回答完成" in content:
                answers_count += 1
                for uname in expected_usernames:
                    if uname in content:
                        answered_usernames.add(uname)
                viewpoint_match = re.search(r"回答完成:\s*(.+)", content)
                if viewpoint_match:
                    existing_viewpoints.append(viewpoint_match.group(1).strip())

            if (
                hasattr(msg, "type")
                and getattr(msg, "type", None) == "tool"
                and getattr(msg, "name", None) == "search_web"
            ):
                search_results_str = content

            if ("失败" in content or "错误" in content) and hasattr(msg, "type") and getattr(msg, "type", None) == "tool":
                errors.append(content)
                for uname in expected_usernames:
                    if uname in content:
                        answered_usernames.add(uname)

        missed_usernames = expected_usernames - answered_usernames
        if missed_usernames and question_id:
            logger.warning(
                "react missed %s answerers, fallback invoke: %s",
                len(missed_usernames),
                ", ".join(sorted(missed_usernames)),
            )
            topic = hotspot.get("topic", hotspot.get("title", ""))

            for uname in missed_usernames:
                if not any(a.username == uname for a in agent_manager.agents):
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
                    fallback_result_str = str(fallback_result)
                    if "回答完成" in fallback_result_str:
                        answers_count += 1
                        viewpoint_match = re.search(r"回答完成:\s*(.+)", fallback_result_str)
                        if viewpoint_match:
                            existing_viewpoints.append(viewpoint_match.group(1).strip())
                    else:
                        errors.append(f"{uname} fallback failed: {fallback_result_str}")
                except Exception as e:
                    errors.append(f"{uname} fallback exception: {e}")
                    logger.error("fallback answer failed: %s", e, exc_info=True)

        return {
            "question_id": question_id,
            "answers_count": answers_count,
            "errors": errors,
            "cycle": cycle,
            "total": total,
        }

    async def start_qa_session(
        self,
        total_cycles: int,
        categories: Optional[List[str]] = None,
        source: Optional[str] = None,
    ):
        if self.is_running:
            logger.warning("qa session already running")
            return

        self.is_running = True
        self.current_cycle = 0
        self.total_cycles = total_cycles

        try:
            await agent_manager.initialize()

            hotspots = await hotspots_loader.load_pending(source=source)
            if categories:
                categories_set = {x.strip() for x in categories if x and x.strip()}
                if categories_set:
                    hotspots = [
                        h
                        for h in hotspots
                        if str(h.get("category", "")).strip() in categories_set
                    ]

            if not hotspots:
                logger.warning("no pending hotspots")
                return

            actual_count = min(total_cycles, len(hotspots))
            delay_min, delay_max = settings.question_interval

            for i in range(actual_count):
                if not self.is_running:
                    break

                self.current_cycle = i + 1
                hotspot = hotspots[i]
                hotspot_id = hotspot.get("id")
                hotspot_source = hotspot.get("source", "")
                topic = hotspot.get("topic", hotspot.get("title", "未知"))

                if hotspot_id:
                    await hotspots_loader.mark_processing(hotspot_id)

                result = await self._process_hotspot(hotspot, i + 1, actual_count)

                question_id = result.get("question_id")
                if hotspot_id and question_id:
                    await hotspots_loader.mark_completed(hotspot_id, question_id)
                elif hotspot_id and result.get("errors"):
                    await hotspots_loader.mark_skipped(hotspot_id)

                self.history.append(
                    {
                        "id": len(self.history) + 1,
                        "cycle": i + 1,
                        "hotspot": {"topic": topic, "source": hotspot_source},
                        "hotspot_db_id": hotspot_id,
                        "question_id": question_id,
                        "answers_count": result.get("answers_count", 0),
                        "errors": result.get("errors", []),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                if len(self.history) > MAX_HISTORY:
                    self.history = self.history[-MAX_HISTORY:]

                if i < actual_count - 1:
                    interval = random.randint(delay_min, delay_max)
                    await asyncio.sleep(interval)
        except Exception as e:
            logger.error("qa session failed: %s", e, exc_info=True)
            raise
        finally:
            self.is_running = False

    def get_status(self) -> Dict:
        return {
            "status": "running" if self.is_running else "idle",
            "current_cycle": self.current_cycle,
            "total_cycles": self.total_cycles,
            "interval_mode": settings.interval_mode,
            "history_count": len(self.history),
            "history": self.history[-50:],
        }

    def stop(self):
        self.is_running = False
        logger.info("qa session stopped")


qa_orchestrator = LangGraphQAOrchestrator()
