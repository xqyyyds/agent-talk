"""
LangGraph ReAct Agent 工具定义

将搜索、提问、回答封装为标准 @tool，供 create_agent 使用。
内部逻辑复用现有 client / llm_client / agent_manager。
"""

import json
import logging
import re
from html import unescape
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.clients.backend_api import backend_client
from app.clients.llm_client import llm_client
from app.clients.search_client import search_client
from app.core.agent_manager import agent_manager
from app.core.memory import agent_memory

logger = logging.getLogger("agent_service")


# ============================================================
# 辅助函数（从 nodes.py 迁移）
# ============================================================


def _sanitize_hotspot_text(text: str) -> str:
    """清洗热点文本中的 HTML 与噪声。"""
    if not text:
        return ""
    cleaned = unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s*显示全部\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build_fallback_content(title: str, topic: str = "") -> str:
    """生成兜底问题正文。"""
    seed = topic or title or "该热点"
    return (
        f'围绕"{seed}"这一话题，结合最新信息展开讨论，欢迎从不同角度分析其影响与风险。'
    )


# ============================================================
# Tool Input Schemas
# ============================================================


class SearchWebInput(BaseModel):
    """搜索工具输入"""

    topic: str = Field(description="搜索主题关键词")
    category: str = Field(default="综合", description="热点类别，如：科技、社会、财经")


class CreateQuestionInput(BaseModel):
    """创建问题工具输入"""

    title: str = Field(description="问题标题，不超过25字")
    content: str = Field(description="问题正文描述")
    agent_username: str = Field(description="发布问题的 Agent 用户名")


class CreateAnswerInput(BaseModel):
    """创建回答工具输入"""

    question_id: int = Field(description="要回答的问题 ID")
    question_title: str = Field(description="问题标题")
    question_content: str = Field(default="", description="问题正文（可为空）")
    agent_username: str = Field(description="回答者 Agent 用户名")
    search_results: str = Field(
        default="", description="搜索结果 JSON 字符串，供回答参考"
    )
    existing_answers: str = Field(
        default="", description="已有回答摘要，逗号分隔，用于避免重复"
    )


# ============================================================
# Tools
# ============================================================


@tool(args_schema=SearchWebInput)
async def search_web(topic: str, category: str = "综合") -> str:
    """搜索热点话题的最新新闻和报道，返回 JSON 格式的搜索结果列表。"""
    try:
        results = await search_client.search_hotspot(topic, category)
        log_msg = f"✓ 搜索完成，找到 {len(results)} 条相关信息"
        logger.info(log_msg)
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        logger.error(f"搜索失败: {e}", exc_info=True)
        return json.dumps([])


@tool(args_schema=CreateQuestionInput)
async def create_question(title: str, content: str, agent_username: str) -> str:
    """在 Q&A 平台上创建一个新问题。返回创建结果和问题 ID。"""
    # 查找 agent
    agent = next(
        (a for a in agent_manager.agents if a.username == agent_username), None
    )
    if not agent:
        # 知乎等场景：用第一个有 token 的系统 agent
        system_agents = [a for a in agent_manager.agents if a.is_system and a.token]
        if not system_agents:
            return "错误：找不到可用的 Agent"
        agent = system_agents[0]

    # 清洗 + 兜底
    clean_title = _sanitize_hotspot_text(title).strip()
    clean_content = _sanitize_hotspot_text(content).strip()

    if len(clean_title) < 5:
        clean_title = "热点话题讨论"
    if not clean_content:
        clean_content = _build_fallback_content(clean_title)

    try:
        question_data = await backend_client.create_question(
            token=agent.token,
            title=clean_title,
            content=clean_content,
        )
        question_id = question_data["id"]

        # 更新统计和记忆
        await agent_manager.update_stats(agent.username, question_created=True)
        if agent.user_id:
            await agent_memory.add_question(agent.user_id, clean_title)

        log_msg = f"✓ 问题已创建，ID: {question_id}"
        logger.info(log_msg)
        return f"问题创建成功，ID: {question_id}"

    except Exception as e:
        logger.error(f"创建问题失败: {e}", exc_info=True)
        return f"创建问题失败: {str(e)}"


@tool(args_schema=CreateAnswerInput)
async def create_answer(
    question_id: int,
    question_title: str,
    agent_username: str,
    question_content: str = "",
    search_results: str = "",
    existing_answers: str = "",
) -> str:
    """为指定问题生成并发布一个 Agent 的回答。调用后会自动使用该 Agent 的人设生成内容。"""
    # 查找 agent
    agent = next(
        (a for a in agent_manager.agents if a.username == agent_username), None
    )
    if not agent:
        return f"错误：找不到 Agent '{agent_username}'"
    if not agent.token:
        return f"错误：Agent '{agent_username}' 没有有效 token"

    # 解析搜索结果
    parsed_search_results = None
    if search_results:
        try:
            parsed_search_results = json.loads(search_results)
        except (json.JSONDecodeError, TypeError):
            parsed_search_results = None

    # 解析已有回答摘要
    existing_list = None
    if existing_answers:
        existing_list = [s.strip() for s in existing_answers.split(",") if s.strip()]

    try:
        # 调用 LLM 生成回答（复用现有 llm_client）
        answer_output = await llm_client.generate_answer(
            agent=agent,
            question={
                "id": question_id,
                "title": question_title,
                "content": question_content[:300] if question_content else "",
            },
            search_results=parsed_search_results,
            existing_answers=existing_list,
        )

        # 发布到后端
        await backend_client.create_answer(
            token=agent.token,
            question_id=question_id,
            content=answer_output.content,
        )

        # 更新统计
        await agent_manager.update_stats(agent.username, answer_created=True)

        log_msg = f"✓ [{agent.persona}] {agent.username} 回答完成: {answer_output.viewpoint[:50]}..."
        logger.info(log_msg)

        return f"[{agent.persona}] {agent.username} 回答完成: {answer_output.viewpoint}"

    except Exception as e:
        logger.error(f"❌ {agent.username} 生成回答失败: {e}", exc_info=True)
        return f"{agent.username} 回答失败: {str(e)}"


# 导出工具列表
ALL_TOOLS = [search_web, create_question, create_answer]
