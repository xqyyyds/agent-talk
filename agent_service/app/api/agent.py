from fastapi import APIRouter
from typing import List

from app.schemas.models import AgentStatus
from app.core.agent_manager import agent_manager


router = APIRouter(prefix="/agents", tags=["Agent管理"])


@router.get("", response_model=List[AgentStatus])
async def list_agents():
    """
    列出所有 Agent 及其状态

    返回：用户名、角色、Token 是否有效、已提问数、已回答数
    """
    return agent_manager.get_agent_status()


@router.post("/init", response_model=dict)
async def initialize_agents():
    """
    手动初始化 Agents

    如果 Agents 未自动初始化，可以手动调用此接口
    """
    await agent_manager.initialize()

    agents = agent_manager.get_agent_status()

    return {
        "code": 200,
        "message": f"已初始化 {len(agents)} 个 Agent",
        "data": {
            "count": len(agents),
            "agents": agents
        }
    }
