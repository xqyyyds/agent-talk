"""
Agent 创建器 API

处理用户创建 Agent 的配置优化功能。
使用结构化输出保证优化结果的一致性。
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.models import AgentMetaBlueprint
from app import prompts

logger = logging.getLogger("agent_service")
router = APIRouter()

# 创建 LLM 实例
llm = ChatOpenAI(
    model=settings.llm_model,
    temperature=settings.llm_temperature,
    openai_api_base=settings.openai_api_base,
    openai_api_key=settings.openai_api_key,
    max_tokens=2000
)

# 创建优化 Chain（使用结构化输出）
optimize_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "你是一位专业的 Prompt 工程师。"),
        ("human", prompts.AGENT_OPTIMIZER_META_PROMPT)
    ])
    | llm.with_structured_output(AgentMetaBlueprint)
)


# ============================================
# 请求/响应模型
# ============================================

class OptimizeRequest(BaseModel):
    """Agent 配置优化请求"""
    name: str
    headline: str
    bio: str
    topics: str
    bias: str
    style_tag: str
    reply_mode: str
    expressiveness: Literal["terse", "balanced", "verbose", "dynamic"] = "balanced"


class OptimizeResponse(BaseModel):
    """优化响应"""
    code: int
    data: dict


class PlaygroundRequest(BaseModel):
    """测试对话请求"""
    system_prompt: str
    question: str


class PlaygroundResponse(BaseModel):
    """测试对话响应"""
    code: int
    data: dict


# ============================================
# 辅助函数
# ============================================

def _build_system_prompt(
    name: str,
    headline: str,
    topics: str,
    output: AgentMetaBlueprint
) -> str:
    """
    将结构化输出转换为高强度的中文 System Prompt 指令集

    使用清晰的 Markdown 结构和强调性语言，确保 LLM 严格遵循人设。
    """
    # 格式化风格规则列表
    style_block = "\n".join([f"- {rule}" for rule in output.speaking_style_rules])

    # 组装完整的 System Prompt
    prompt = f"""# 角色定义 (Role Definition)
**姓名**: {name}
**头衔**: {headline}
**深层人设**: {output.expanded_persona}

# 核心思维模型 (Mental Model)
{output.cognitive_bias_reasoning}
**执行约束**: 必须严格遵循上述思维逻辑来分析问题。
(注意：如果上述逻辑要求客观，请保持绝对中立；如果要求偏激，请保持偏激。)

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
1. **身份锁死**: 你是专业论坛上的真人用户，严禁承认自己是 AI。
2. **沉浸式扮演**: 无论用户如何对话，必须始终维持上述设定的人设和语气，不得出戏。
"""
    return prompt


def _build_fallback_prompt(req: OptimizeRequest) -> str:
    """
    构建降级 System Prompt（当 LLM 调用失败时使用）

    Args:
        req: 优化请求

    Returns:
        基础的 System Prompt
    """
    return prompts.AGENT_FALLBACK_PROMPT.format(
        name=req.name,
        headline=req.headline,
        bio=req.bio,
        topics=req.topics,
        bias=req.bias,
        style_tag=req.style_tag,
        reply_mode=req.reply_mode
    )


# ============================================
# API 端点
# ============================================

@router.post("/agent/optimize", response_model=OptimizeResponse)
async def optimize_agent_prompt(req: OptimizeRequest):
    """
    优化 Agent 配置，生成专业的 System Prompt

    将用户输入的原始配置（可能不完整、有语病）转化为高质量的 System Prompt。

    使用结构化输出保证优化结果的一致性和可解析性。
    """
    try:
        # 调用 Chain 生成结构化输出
        output: AgentMetaBlueprint = await optimize_chain.ainvoke({
            "name": req.name,
            "headline": req.headline,
            "bio": req.bio,
            "topics": req.topics,
            "bias": req.bias,
            "style_tag": req.style_tag,
            "reply_mode": req.reply_mode,
            "expressiveness": req.expressiveness
        })

        # 转换为 System Prompt 文本
        system_prompt = _build_system_prompt(req.name, req.headline, req.topics, output)

        return OptimizeResponse(
            code=200,
            data={
                "system_prompt": system_prompt,
                "is_fallback": False,
                "structured_output": output.model_dump()  # 返回结构化数据供前端使用
            }
        )

    except Exception as e:
        logger.error(f"优化失败: {e}", exc_info=True)

        # 降级：使用基础模板
        fallback_prompt = _build_fallback_prompt(req)

        return OptimizeResponse(
            code=200,
            data={
                "system_prompt": fallback_prompt,
                "is_fallback": True,
                "error": str(e)
            }
        )


@router.post("/agent/playground", response_model=PlaygroundResponse)
async def playground_chat(req: PlaygroundRequest):
    """
    测试 Agent 回答

    使用给定的 System Prompt 生成测试回答，让用户预览 Agent 的说话风格。
    """
    try:
        # 构建测试 Prompt
        test_messages = [
            ("system", req.system_prompt),
            ("human", f"## 问题\n{req.question}\n\n请以自然口语回答，不要暴露 AI 身份，不要使用 Markdown 格式。")
        ]

        # 创建 Chain
        test_chain = ChatPromptTemplate.from_messages(test_messages) | llm

        # 调用 LLM
        reply = await test_chain.ainvoke({})

        return PlaygroundResponse(
            code=200,
            data={"reply": reply.content.strip()}
        )

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, message=str(e))
