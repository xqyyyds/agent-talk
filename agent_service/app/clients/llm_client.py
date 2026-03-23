"""
LLM client for question/answer generation.
"""

import logging
import re
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from app import prompts
from app.core.agent_model_catalog import get_system_model_catalog
from app.core.llm_alerts import push_llm_alert
from app.core.agent_model_resolver import resolve_agent_model
from app.core.llm_runtime import run_with_llm_failover
from app.core.runtime_config import get_runtime_config
from app.schemas.models import AgentInfo, AnswerOutput, QuestionOutput

logger = logging.getLogger("agent_service")


class LLMClient:
    def __init__(self):
        pass

    def _clean_markdown_formatting(self, text: str) -> str:
        if not text:
            return text
        text = re.sub(r"```[\w]*\n?", "", text)
        text = re.sub(r"```", "", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"^(#{1,6})\s+", "", text, flags=re.MULTILINE)
        # Keep list prefixes and indentation for downstream paragraph/list rendering.
        lines = text.split("\n")
        cleaned_lines = [line.rstrip() for line in lines]
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _get_system_prompt(self, agent: AgentInfo) -> str:
        if agent.system_prompt:
            return agent.system_prompt

        local_prompt = prompts.SYSTEM_AGENT_PROMPTS.get(agent.username)
        if local_prompt:
            return local_prompt

        return (
            f"你是一个名叫“{agent.username}”的知乎用户，风格是{agent.persona}。"
            "请以真人口吻发言。"
        )

    def _format_search_results(self, search_results: Optional[List[Dict]]) -> str:
        if not search_results:
            return ""

        items = []
        for i, result in enumerate(search_results[:5], 1):
            items.append(
                f"[{i}] {result.get('title', '')}\n{result.get('content', '')[:500]}...\n来源: {result.get('url', '')}"
            )

        return "\n## 参考资料\n" + "\n\n".join(items)

    def _is_json_parse_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        keywords = ("invalid json", "json_invalid", "json decode", "jsondecodeerror")
        return any(keyword in text for keyword in keywords)

    def _coerce_plain_answer_output(self, text: str) -> AnswerOutput:
        cleaned = self._clean_markdown_formatting(text)
        if not cleaned:
            cleaned = "这个问题我还在想，先说一个直观感受：现实里大家会更看重确定性。"
        first_line = cleaned.splitlines()[0].strip()
        viewpoint = first_line[:100] if first_line else cleaned[:100]
        return AnswerOutput(
            content=cleaned,
            viewpoint=viewpoint or "基于现实体验给出的直接判断",
            evidence=[],
            references=[],
        )

    def _should_use_plain_answer_output(self, llm: object) -> bool:
        model_name = str(getattr(llm, "model_name", "")).strip().lower()
        api_base = str(getattr(llm, "openai_api_base", "")).strip().lower()
        return model_name.startswith("glm-") or "bigmodel.cn" in api_base

    async def _resolve_agent_model_override(
        self, agent: AgentInfo
    ) -> dict | None:
        runtime_cfg = await get_runtime_config()
        catalog = get_system_model_catalog(runtime_cfg)
        if not catalog:
            return None

        resolved = resolve_agent_model(
            {
                "model_source": agent.model_source,
                "model_id": agent.model_id,
                "model_config": agent.custom_model_config,
            },
            runtime_cfg,
        )
        if not resolved:
            return None
        return {
            "label": resolved.get("label", ""),
            "model": resolved.get("model", ""),
            "base_url": resolved.get("base_url", ""),
            "api_key": resolved.get("api_key", ""),
        }

    async def _run_generation_with_retry(
        self,
        *,
        scene: str,
        agent: AgentInfo,
        runner,
        max_tokens: int = 2000,
    ):
        runtime_cfg = await get_runtime_config()
        model_override = await self._resolve_agent_model_override(agent)
        primary_model = (
            str(model_override.get("model") or model_override.get("label") or "").strip()
            if model_override
            else str(runtime_cfg.llm_model or "").strip()
        )
        secondary_model = (
            None
            if model_override
            else (
                str(runtime_cfg.llm_model_secondary or "").strip()
                if str(runtime_cfg.llm_failover_mode).lower() == "dual_fallback"
                else None
            )
        )
        effective_model = (
            str(model_override.get("label") or model_override.get("model") or "").strip()
            if model_override
            else primary_model
        )

        last_error: Exception | None = None
        for attempt in range(1, 3):
            try:
                return await run_with_llm_failover(
                    scene=scene,
                    runner=runner,
                    max_tokens=max_tokens,
                    model_override=model_override,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "%s failed for %s on attempt %s/2: %s",
                    scene,
                    agent.username,
                    attempt,
                    exc,
                )
                if attempt < 2:
                    continue

        await push_llm_alert(
            kind="generation_failure",
            scene=scene,
            primary_model=primary_model,
            secondary_model=secondary_model,
            primary_error=str(last_error or "unknown generation error"),
            fallback_succeeded=False,
            secondary_error=None,
            agent_username=agent.username,
            attempts=2,
            effective_model=effective_model,
            message=f"{agent.username} 在 {scene} 连续两次生成失败，已跳过本次内容生成。",
        )
        raise RuntimeError(
            f"{scene} failed twice for agent {agent.username}: {last_error}"
        ) from last_error

    async def generate_question(
        self,
        agent: AgentInfo,
        category: str,
        topic: str,
        search_results: Optional[List[Dict]] = None,
        recent_questions: Optional[List[str]] = None,
        recent_topics: Optional[List[str]] = None,
    ) -> QuestionOutput:
        if not category or not topic:
            raise ValueError("category and topic cannot be empty")

        system_prompt = self._get_system_prompt(agent)
        expressiveness_instruction = prompts.QUESTION_EXPRESSIVENESS_INSTRUCTIONS.get(
            agent.expressiveness,
            prompts.QUESTION_EXPRESSIVENESS_INSTRUCTIONS["balanced"],
        )
        search_results_section = self._format_search_results(search_results)

        memory_section = ""
        if recent_questions or recent_topics:
            recent_questions_text = "\n".join(
                f"- {item}" for item in (recent_questions or [])[:10]
            )
            recent_topics_text = "\n".join(
                f"- {item}" for item in (recent_topics or [])[:10]
            )
            memory_section = prompts.QUESTION_MEMORY_SECTION.format(
                recent_questions_text=recent_questions_text or "- （暂无）",
                recent_topics_text=recent_topics_text or "- （暂无）",
            )

        payload = {
            "category": category,
            "topic": topic,
            "search_results_section": search_results_section,
            "memory_section": memory_section,
            "expressiveness_instruction": expressiveness_instruction,
        }

        async def _invoke(llm):
            chain = ChatPromptTemplate.from_messages(
                [("system", system_prompt), ("human", prompts.QUESTION_USER_PROMPT)]
            ) | llm.with_structured_output(QuestionOutput, include_raw=False)
            return await chain.ainvoke(payload)

        result = await self._run_generation_with_retry(
            scene="qa.generate_question",
            agent=agent,
            runner=_invoke,
            max_tokens=2000,
        )
        result.content = self._clean_markdown_formatting(result.content)
        logger.info("[question] generated by %s: %s", agent.username, result.title)
        return result

    async def generate_answer(
        self,
        agent: AgentInfo,
        question: Dict,
        search_results: Optional[List[Dict]] = None,
        existing_answers: Optional[List[str]] = None,
    ) -> AnswerOutput:
        if not question or not question.get("title"):
            raise ValueError("question must include title")

        system_prompt = self._get_system_prompt(agent)
        expressiveness_instruction = prompts.ANSWER_EXPRESSIVENESS_INSTRUCTIONS.get(
            agent.expressiveness,
            prompts.ANSWER_EXPRESSIVENESS_INSTRUCTIONS["balanced"],
        )
        search_results_section = self._format_search_results(search_results)

        existing_answers_section = ""
        if existing_answers:
            existing_answers_text = "\n".join(existing_answers)
            existing_answers_section = prompts.EXISTING_ANSWERS_SECTION.format(
                existing_answers_text=existing_answers_text
            )

        payload = {
            "question_title": question.get("title", ""),
            "question_content": question.get("content", "")[:300],
            "search_results_section": search_results_section,
            "expressiveness_instruction": expressiveness_instruction,
            "existing_answers_section": existing_answers_section,
        }

        async def _invoke(llm):
            prompt_template = ChatPromptTemplate.from_messages(
                [("system", system_prompt), ("human", prompts.ANSWER_USER_PROMPT)]
            )
            if self._should_use_plain_answer_output(llm):
                raw_chain = prompt_template | llm
                raw_result = await raw_chain.ainvoke(payload)
                raw_content = (
                    raw_result.content
                    if hasattr(raw_result, "content")
                    else str(raw_result)
                )
                return self._coerce_plain_answer_output(str(raw_content))

            structured_chain = prompt_template | llm.with_structured_output(
                AnswerOutput, include_raw=False
            )
            try:
                return await structured_chain.ainvoke(payload)
            except Exception as parse_error:
                if not self._is_json_parse_error(parse_error):
                    raise
                logger.warning(
                    "Answer structured output parse failed, fallback to plain text: %s",
                    parse_error,
                )
                raw_chain = prompt_template | llm
                raw_result = await raw_chain.ainvoke(payload)
                raw_content = (
                    raw_result.content
                    if hasattr(raw_result, "content")
                    else str(raw_result)
                )
                return self._coerce_plain_answer_output(str(raw_content))

        result = await self._run_generation_with_retry(
            scene="qa.generate_answer",
            agent=agent,
            runner=_invoke,
            max_tokens=2000,
        )
        result.content = self._clean_markdown_formatting(result.content)
        logger.info("[answer] generated by %s", agent.username)
        return result

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: Optional[float] = None,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))

        try:
            async def _invoke(llm):
                chain = ChatPromptTemplate.from_messages(messages) | llm
                result = await chain.ainvoke({})
                return str(result.content)

            return await run_with_llm_failover(
                scene="qa.generic_generate",
                runner=_invoke,
                max_tokens=max_tokens,
                temperature_override=temperature,
            )
        except Exception as e:
            logger.error("LLM generate failed: %s", e, exc_info=True)
            raise


llm_client = LLMClient()
