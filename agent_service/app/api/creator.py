"""
Agent creator APIs: optimize prompt and playground chat.
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from app import prompts
from app.core.llm_runtime import run_with_llm_failover
from app.schemas.models import AgentMetaBlueprint

logger = logging.getLogger("agent_service")
router = APIRouter()


class OptimizeRequest(BaseModel):
    name: str
    headline: str
    bio: str
    topics: str
    bias: str
    style_tag: str
    reply_mode: str
    expressiveness: Literal["terse", "balanced", "verbose", "dynamic"] = "balanced"


class OptimizeResponse(BaseModel):
    code: int
    data: dict


class PlaygroundRequest(BaseModel):
    system_prompt: str
    question: str


class PlaygroundResponse(BaseModel):
    code: int
    data: dict


def _build_system_prompt(
    name: str,
    headline: str,
    topics: str,
    output: AgentMetaBlueprint,
) -> str:
    style_block = "\n".join([f"- {rule}" for rule in output.speaking_style_rules])

    return f"""# 角色定义 (Role Definition)
**姓名**: {name}
**头衔**: {headline}
**深层人设**: {output.expanded_persona}

# 核心思维模型 (Mental Model)
{output.cognitive_bias_reasoning}
**执行约束**: 必须严格遵循上述思维逻辑来分析问题。

# 互动策略 (Interaction Strategy)
**终极目标**: {output.interaction_goal}
**开场战术**: {output.opening_strategy}

# 语言风格准则 (Speaking Style)
{style_block}

{output.expressiveness_rule}

# 知识边界 (Knowledge Scope)
**专业领域**: {topics}
**边界原则**: 你的专业知识和强观点仅限于上述领域。对于完全无关的话题，不要强行表现专业性。

# 系统级最高指令 (Meta-Instructions)
1. **身份锁定**: 你是论坛中的真人用户，严禁承认自己是 AI。
2. **沉浸式扮演**: 无论用户如何对话，必须保持人设与语气一致，不得出戏。
3. **反模板化**: 禁止“首先/其次/最后/综上”等模板衔接词。
4. **场景化**: 优先给出具体情境和后果，避免空洞表达。
5. **主观性**: 回答里必须出现第一人称主观视角（如“我见过/我更倾向”）。
"""


def _build_fallback_prompt(req: OptimizeRequest) -> str:
    return prompts.AGENT_FALLBACK_PROMPT.format(
        name=req.name,
        headline=req.headline,
        bio=req.bio,
        topics=req.topics,
        bias=req.bias,
        style_tag=req.style_tag,
        reply_mode=req.reply_mode,
    )


@router.post("/agent/optimize", response_model=OptimizeResponse)
async def optimize_agent_prompt(req: OptimizeRequest):
    payload = {
        "name": req.name,
        "headline": req.headline,
        "bio": req.bio,
        "topics": req.topics,
        "bias": req.bias,
        "style_tag": req.style_tag,
        "reply_mode": req.reply_mode,
        "expressiveness": req.expressiveness,
    }

    try:
        async def _invoke(llm):
            chain = (
                ChatPromptTemplate.from_messages(
                    [
                        ("system", "你是一位专业的 Prompt 工程师。"),
                        ("human", prompts.AGENT_OPTIMIZER_META_PROMPT),
                    ]
                )
                | llm.with_structured_output(AgentMetaBlueprint)
            )
            return await chain.ainvoke(payload)

        output: AgentMetaBlueprint = await run_with_llm_failover(
            scene="creator.optimize",
            runner=_invoke,
            max_tokens=2000,
        )

        system_prompt = _build_system_prompt(req.name, req.headline, req.topics, output)
        return OptimizeResponse(
            code=200,
            data={
                "system_prompt": system_prompt,
                "is_fallback": False,
                "structured_output": output.model_dump(),
            },
        )
    except Exception as e:
        logger.error("optimize failed: %s", e, exc_info=True)
        fallback_prompt = _build_fallback_prompt(req)
        return OptimizeResponse(
            code=200,
            data={
                "system_prompt": fallback_prompt,
                "is_fallback": True,
                "error": str(e),
            },
        )


@router.post("/agent/playground", response_model=PlaygroundResponse)
async def playground_chat(req: PlaygroundRequest):
    try:
        test_messages = [
            ("system", req.system_prompt),
            (
                "human",
                f"## 问题\n{req.question}\n\n请以自然口语回答，不要暴露 AI 身份，不要使用 Markdown 格式。",
            ),
        ]

        async def _invoke(llm):
            test_chain = ChatPromptTemplate.from_messages(test_messages) | llm
            reply = await test_chain.ainvoke({})
            return str(reply.content).strip()

        reply = await run_with_llm_failover(
            scene="creator.playground",
            runner=_invoke,
            max_tokens=2000,
        )

        return PlaygroundResponse(code=200, data={"reply": reply})
    except Exception as e:
        logger.error("playground failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
