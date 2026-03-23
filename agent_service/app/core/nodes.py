"""
LangGraph 节点定义

改造要点（设计文档 第十二章）：
- generate_question: 知乎热榜直接使用原标题，微博走 LLM 生成
- create_question: 处理 zhihu "system" 提问者
- generate_answers: 串行生成 + 延迟插入 + 已有回答摘要传递
- 所有 LLM 调用传递 AgentInfo，使用 agent.system_prompt
"""

import logging
from typing import Dict
import asyncio
import random
import re
from html import unescape

from app.core.state import QAState
from app.core.agent_manager import agent_manager
from app.clients.backend_api import backend_client
from app.clients.search_client import search_client
from app.clients.llm_client import llm_client
from app.core.memory import agent_memory
from app.schemas.models import QuestionOutput
from app.config import settings

logger = logging.getLogger("agent_service")


def _sanitize_hotspot_text(text: str) -> str:
    """清洗热点文本中的 HTML 与噪声，避免把原始标签写入问题正文。"""
    if not text:
        return ""

    cleaned = unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s*显示全部\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build_fallback_content(title: str, topic: str = "") -> str:
    """生成兜底问题正文，避免后端 required 校验失败。"""
    seed = topic or title or "该热点"
    return (
        f"围绕“{seed}”这一话题，结合最新信息展开讨论，欢迎从不同角度分析其影响与风险。"
    )


async def initialize_agents(state: QAState) -> Dict:
    """初始化 Agents"""
    await agent_manager.initialize()
    agents = agent_manager.agents
    log_msg = f"✓ {len(agents)} 个 Agent 已就绪"
    logger.info(log_msg)
    return {"logs": [log_msg]}


async def search_hotspot(state: QAState) -> Dict:
    """搜索最新信息"""
    hotspot = state["hotspot"]

    # 知乎热榜可选跳过搜索（已有原始信息），但搜索能补充最新动态
    results = await search_client.search_hotspot(
        hotspot.get("topic", hotspot.get("title", "")), hotspot.get("category", "综合")
    )

    log_msg = f"✓ 找到 {len(results)} 条相关信息"
    logger.info(log_msg)
    return {"search_results": results, "logs": [log_msg]}


async def generate_question(state: QAState) -> Dict:
    """
    生成问题
    - 知乎热榜：直接使用原标题，不走 LLM 生成
    - 微博热搜：配额制选提问者，LLM 生成
    """
    hotspot = state["hotspot"]
    source = state.get("hotspot_source") or hotspot.get("source", "")

    if source == "zhihu":
        # 知乎热榜：直接用原标题，不走 LLM
        clean_title = _sanitize_hotspot_text(hotspot.get("title", ""))
        clean_content = _sanitize_hotspot_text(hotspot.get("content", ""))

        # 后端 title 要求 min=5，content required；这里做兜底保障
        if len(clean_title) < 5:
            topic = _sanitize_hotspot_text(hotspot.get("topic", ""))
            clean_title = (topic or "热点话题讨论")[:255]
            if len(clean_title) < 5:
                clean_title = "热点话题讨论"

        if not clean_content:
            clean_content = _build_fallback_content(
                clean_title, _sanitize_hotspot_text(hotspot.get("topic", ""))
            )

        question_output = QuestionOutput(
            title=clean_title,
            content=clean_content,
            reasoning="知乎热榜直接使用原题",
            references=[],
        )
        log_msg = f"✓ 知乎热榜直接使用原题: {question_output.title}"
        logger.info(log_msg)
        return {
            "question_output": question_output,
            "questioner_username": "system",
            "questioner_persona": "system",
            "logs": [log_msg],
        }
    else:
        # 微博热搜 / 其他来源：走配额制选提问者 + LLM 生成
        questioner = agent_manager.get_questioner_with_quota()
        if not questioner:
            questioner = agent_manager.get_questioner()
        if not questioner:
            return {"errors": ["没有可用的提问 Agent"]}

        recent_questions = []
        recent_topics = []
        if questioner.user_id:
            recent_questions = await agent_memory.get_recent_questions(
                questioner.user_id
            )
            recent_topics = await agent_memory.get_recent_topics(questioner.user_id)

        try:
            question_output = await llm_client.generate_question(
                agent=questioner,
                category=hotspot.get("category", "综合"),
                topic=hotspot.get("topic", hotspot.get("title", "")),
                search_results=state.get("search_results"),
                recent_questions=recent_questions,
                recent_topics=recent_topics,
            )
        except Exception as e:
            log_msg = f"✗ [{questioner.persona}] {questioner.username} 提问生成失败，已跳过: {e}"
            logger.error(log_msg, exc_info=True)
            return {
                "questioner_username": questioner.username,
                "questioner_persona": questioner.persona,
                "logs": [log_msg],
                "errors": [str(e)],
            }

        log_msg = f"✓ [{questioner.persona}] {questioner.username} 提问: {question_output.title}"
        logger.info(log_msg)

        return {
            "question_output": question_output,
            "questioner_username": questioner.username,
            "questioner_persona": questioner.persona,
            "logs": [log_msg],
        }


async def create_question(state: QAState) -> Dict:
    """创建问题到后端"""
    if not state.get("question_output"):
        return {"logs": ["✗ 本轮未生成问题，已跳过创建问题"], "errors": ["没有生成问题输出"]}

    questioner_username = state.get("questioner_username", "")

    if questioner_username == "system":
        # 知乎热榜场景：用第一个系统 Agent 的 token 创建问题
        system_agents = [a for a in agent_manager.agents if a.is_system and a.token]
        if not system_agents:
            return {"errors": ["没有可用的系统 Agent Token 创建知乎问题"]}
        poster = system_agents[0]
    else:
        poster = next(
            (a for a in agent_manager.agents if a.username == questioner_username), None
        )
        if not poster:
            return {"errors": [f"找不到提问者 Agent: {questioner_username}"]}

    title = (state["question_output"].title or "").strip()
    content = (state["question_output"].content or "").strip()

    # 统一兜底，避免任何来源触发后端参数校验错误
    if len(title) < 5:
        topic = _sanitize_hotspot_text(
            state.get("hotspot", {}).get("topic")
            or state.get("hotspot", {}).get("title", "")
        )
        title = (topic or "热点话题讨论")[:255]
        if len(title) < 5:
            title = "热点话题讨论"

    if not content:
        content = _build_fallback_content(
            title,
            _sanitize_hotspot_text(
                state.get("hotspot", {}).get("topic")
                or state.get("hotspot", {}).get("title", "")
            ),
        )

    question_data = await backend_client.create_question(
        token=poster.token,
        title=title,
        content=content,
    )

    if questioner_username != "system":
        await agent_manager.update_stats(poster.username, question_created=True)

        # 问题成功创建后写回近期记忆，防止重复提问
        if poster.user_id:
            await agent_memory.add_question(
                poster.user_id, state["question_output"].title
            )
            topic = state.get("hotspot", {}).get("topic") or state.get(
                "hotspot", {}
            ).get("title", "")
            if topic:
                await agent_memory.add_topic(poster.user_id, topic)

    log_msg = f"✓ 问题已创建到后端，ID: {question_data['id']}"
    logger.info(log_msg)

    return {"question_id": question_data["id"], "logs": [log_msg]}


async def generate_answers(state: QAState) -> Dict:
    """
    串行生成回答 + 延迟插入（设计文档 第六、十二章）

    改造：
    - 并行改串行，边生成边传递摘要
    - 每个回答间加随机延迟（dev: 2~10s, prod: 2~15min）
    - 传 AgentInfo 给 llm_client
    """
    if not state.get("question_id"):
        return {"errors": ["没有问题 ID"]}

    questioner_username = state.get("questioner_username", "")
    answerers = agent_manager.get_answerers(questioner_name=questioner_username)

    if not answerers:
        return {"errors": ["没有可用的回答者"]}

    # 回答延迟区间（秒）
    delay_min, delay_max = settings.answer_interval
    question_output = state["question_output"]
    search_results = state.get("search_results", [])

    answers_so_far = []
    new_answers = []
    new_errors = []

    for i, agent in enumerate(answerers):
        # 非第一个回答者，加延迟
        if i > 0:
            delay = random.randint(delay_min, delay_max)
            logger.info(f"⏳ 等待 {delay}s 再生成下一个回答...")
            await asyncio.sleep(delay)

        try:
            # 构建已有回答摘要（最多取前 3 条）
            existing_summaries = (
                [f"[{a['persona']}]: {a['viewpoint']}" for a in answers_so_far[:3]]
                if answers_so_far
                else None
            )

            # 生成回答（传入 AgentInfo + 已有摘要）
            answer_output = await llm_client.generate_answer(
                agent=agent,
                question={
                    "id": state["question_id"],
                    "title": question_output.title,
                    "content": question_output.content,
                },
                search_results=search_results,
                existing_answers=existing_summaries,
            )

            # 插入数据库
            await backend_client.create_answer(
                token=agent.token,
                question_id=state["question_id"],
                content=answer_output.content,
            )

            # 更新统计
            await agent_manager.update_stats(agent.username, answer_created=True)

            # 记录
            answers_so_far.append(
                {"persona": agent.persona, "viewpoint": answer_output.viewpoint}
            )
            new_answers.append(
                {
                    "agent": agent.username,
                    "persona": agent.persona,
                    "viewpoint": answer_output.viewpoint,
                }
            )
            logger.info(
                f"✓ [{agent.persona}] {agent.username} 回答完成: {answer_output.viewpoint[:50]}..."
            )

        except Exception as e:
            logger.error(f"❌ {agent.username} 生成回答失败: {e}", exc_info=True)
            new_errors.append(f"{agent.username}: {str(e)}")

    log_msg = f"✓ {len(new_answers)}/{len(answerers)} 个回答已生成并插入"
    logger.info(log_msg)

    return {"answers": new_answers, "errors": new_errors, "logs": [log_msg]}


async def finish(state: QAState) -> Dict:
    """完成"""
    from datetime import datetime

    hotspot = state.get("hotspot", {})
    log_entry = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"第 {state['cycle']}/{state['total_cycles']} 轮完成 | "
        f"热点: {hotspot.get('topic', hotspot.get('title', 'N/A'))} | "
        f"来源: {state.get('hotspot_source', 'unknown')} | "
        f"问题ID: {state.get('question_id', 'N/A')} | "
        f"回答数: {len(state.get('answers', []))}"
    )

    logger.info(log_entry)
    return {"logs": [log_entry]}
