"""
LLM 客户端（使用 LangChain）

改造要点（设计文档 第八章）：
- generate_question / generate_answer 接收 AgentInfo 参数
- 直接使用 agent.system_prompt（来自数据库），不再维护本地人设映射
- 通过 expressiveness 控制回答长度
"""

import logging
import re
from typing import List, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.models import AgentInfo, QuestionOutput, AnswerOutput
from app.config import settings
from app.core.runtime_config import get_runtime_config
from app import prompts

logger = logging.getLogger("agent_service")


class LLMClient:
    """LLM 客户端"""

    def __init__(self):
        pass

    async def _build_llm(
        self,
        max_tokens: int = 2000,
        temperature: float | None = None,
    ) -> ChatOpenAI:
        cfg = await get_runtime_config()
        return ChatOpenAI(
            model=str(cfg.get("llm_model", settings.llm_model)),
            temperature=(
                float(cfg.get("llm_temperature", settings.llm_temperature))
                if temperature is None
                else temperature
            ),
            openai_api_base=str(
                cfg.get("openai_api_base", settings.openai_api_base)
            ),
            openai_api_key=str(cfg.get("openai_api_key", settings.openai_api_key)),
            max_tokens=max_tokens,
        )

    def _clean_markdown_formatting(self, text: str) -> str:
        """清理Markdown格式，让文本更像真人回答"""
        if not text:
            return text
        text = re.sub(r"```[\w]*\n?", "", text)
        text = re.sub(r"```", "", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"^(#{1,6})\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[\s]*[-*]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
        lines = text.split("\n")
        cleaned_lines = [line.lstrip() for line in lines]
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _get_system_prompt(self, agent: AgentInfo) -> str:
        """
        获取 agent 的 system prompt。
        优先使用数据库中的 system_prompt，若为空则降级到本地预定义。
        """
        if agent.system_prompt:
            return agent.system_prompt

        # 降级：从本地预定义 System Prompts 中查找
        local_prompt = prompts.SYSTEM_AGENT_PROMPTS.get(agent.username)
        if local_prompt:
            return local_prompt

        # 最终降级：使用通用提示
        return f"你是一个名叫「{agent.username}」的知乎用户，风格是{agent.persona}。请以真人的口吻发言。"

    def _format_search_results(self, search_results: Optional[List[Dict]]) -> str:
        """格式化搜索结果"""
        if not search_results:
            return ""

        items = []
        for i, result in enumerate(search_results[:5], 1):
            items.append(
                f"[{i}] {result.get('title', '')}\n{result.get('content', '')[:500]}...\n来源: {result.get('url', '')}"
            )

        return "\n## 参考资料\n" + "\n\n".join(items)

    async def generate_question(
        self,
        agent: AgentInfo,
        category: str,
        topic: str,
        search_results: Optional[List[Dict]] = None,
        recent_questions: Optional[List[str]] = None,
        recent_topics: Optional[List[str]] = None,
    ) -> QuestionOutput:
        """
        生成问题（使用 agent.system_prompt）

        改造：接收 AgentInfo 参数，直接使用数据库中的 system_prompt
        """
        if not category or not topic:
            raise ValueError("category 和 topic 不能为空")

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

        chain = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", prompts.QUESTION_USER_PROMPT)]
        ) | (await self._build_llm()).with_structured_output(
            QuestionOutput, include_raw=False
        )

        try:
            result = await chain.ainvoke(
                {
                    "category": category,
                    "topic": topic,
                    "search_results_section": search_results_section,
                    "memory_section": memory_section,
                    "expressiveness_instruction": expressiveness_instruction,
                }
            )
            result.content = self._clean_markdown_formatting(result.content)
            logger.info(f"✓ [{agent.username}] 生成问题: {result.title}")
            return result

        except Exception as e:
            logger.error(f"LLM 生成问题失败: {e}", exc_info=True)
            return QuestionOutput(
                title=f"关于{topic}的思考",
                content=f"在{category}领域，{topic}引发了广泛关注。",
                reasoning="LLM 调用失败，使用默认回答",
                references=[],
            )

    async def generate_answer(
        self,
        agent: AgentInfo,
        question: Dict,
        search_results: Optional[List[Dict]] = None,
        existing_answers: Optional[List[str]] = None,
    ) -> AnswerOutput:
        """
        生成回答（使用 agent.system_prompt）

        改造：接收 AgentInfo 参数，通过 expressiveness 控制回答长度。
        existing_answers: 已有回答摘要列表（前几条），用于避免观点重复。
        """
        if not question or not question.get("title"):
            raise ValueError("question 必须包含 title")

        system_prompt = self._get_system_prompt(agent)
        expressiveness_instruction = prompts.ANSWER_EXPRESSIVENESS_INSTRUCTIONS.get(
            agent.expressiveness, prompts.ANSWER_EXPRESSIVENESS_INSTRUCTIONS["balanced"]
        )
        search_results_section = self._format_search_results(search_results)

        # 构建已有回答区块
        existing_answers_section = ""
        if existing_answers:
            existing_answers_text = "\n".join(existing_answers)
            existing_answers_section = prompts.EXISTING_ANSWERS_SECTION.format(
                existing_answers_text=existing_answers_text
            )

        chain = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", prompts.ANSWER_USER_PROMPT)]
        ) | (await self._build_llm()).with_structured_output(
            AnswerOutput, include_raw=False
        )

        try:
            result = await chain.ainvoke(
                {
                    "question_title": question.get("title", ""),
                    "question_content": question.get("content", "")[:300],
                    "search_results_section": search_results_section,
                    "expressiveness_instruction": expressiveness_instruction,
                    "existing_answers_section": existing_answers_section,
                }
            )
            result.content = self._clean_markdown_formatting(result.content)
            logger.info(f"✓ [{agent.username}] 生成回答: {result.viewpoint[:50]}...")
            return result

        except Exception as e:
            logger.error(f"LLM 生成回答失败: {e}", exc_info=True)
            return AnswerOutput(
                content=f"作为一个{agent.persona}，我认为这个问题值得深入探讨。",
                viewpoint=f"{agent.persona}的视角分析（LLM 调用失败）",
                evidence=[],
                references=[],
            )

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: Optional[float] = None,
    ) -> str:
        """通用文本生成方法（用于 Agent 优化器等场景）"""
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))

        try:
            llm_with_limit = await self._build_llm(
                max_tokens=max_tokens,
                temperature=temperature,
            )
            chain = ChatPromptTemplate.from_messages(messages) | llm_with_limit
            result = await chain.ainvoke({})
            return result.content
        except Exception as e:
            logger.error(f"LLM 生成失败: {e}", exc_info=True)
            raise


# 全局单例
llm_client = LLMClient()
