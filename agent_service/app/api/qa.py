from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from app.schemas.models import QAStartRequest, QAStatusResponse, AgentStatus
from app.core.agent_manager import agent_manager
from app.core.langgraph_qa import qa_orchestrator
from app.config import settings


router = APIRouter(prefix="/qa", tags=["问答管理"])


@router.post("/start", response_model=dict)
async def start_qa(request: QAStartRequest, background_tasks: BackgroundTasks):
    """
    启动问答会话

    - 自动初始化 6 个 Agent（如果不存在则创建）
    - 依次处理每个热点
    - 每个热点：1 个提问 + 5 个回答
    """
    if qa_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="问答会话已在运行中")

    # 如果未指定 cycle_count，使用配置文件的默认值
    cycle_count = request.cycle_count or settings.qa_default_cycle_count

    # 在后台执行
    background_tasks.add_task(
        qa_orchestrator.start_qa_session,
        cycle_count,
        request.categories,
        request.source,
    )

    return {
        "code": 200,
        "message": f"问答会话已启动，计划 {cycle_count} 轮",
        "data": {
            "total_cycles": cycle_count,
            "categories": request.categories or "自动提取所有类别",
            "source": request.source or "全部来源",
            "interval_mode": settings.interval_mode,
        },
    }


@router.post("/stop", response_model=dict)
async def stop_qa():
    """停止当前问答会话"""
    if not qa_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="没有正在运行的问答会话")

    qa_orchestrator.stop()

    return {"code": 200, "message": "问答会话已停止"}


@router.get("/status", response_model=QAStatusResponse)
async def get_qa_status():
    """
    获取问答状态

    返回当前进度、各 Agent 状态、日志
    """
    status = qa_orchestrator.get_status()
    agents_status = agent_manager.get_agent_status()

    # orchestrator 返回 history 而不是 logs，提取最近的日志摘要
    history = status.get("history", [])
    logs = [f"[{h.get('cycle','')}] {h['hotspot']['topic']}" for h in history[-20:]]

    return QAStatusResponse(
        status=status["status"],
        current_cycle=status["current_cycle"],
        total_cycles=status["total_cycles"],
        agents_status=agents_status,
        logs=logs,
    )


@router.get("/history")
async def get_qa_history(limit: int = 10, offset: int = 0):
    """
    获取问答历史日志

    返回已完成的问答记录
    """
    history = qa_orchestrator.history
    total = len(history)

    # 分页
    start = offset
    end = start + limit
    paginated_history = history[start:end]

    return {"code": 200, "data": {"total": total, "items": paginated_history}}


@router.get("/processed-hotspots")
async def get_processed_hotspots():
    """
    获取已处理的热点列表

    从 history 中提取已处理的热点话题
    """
    topics = [
        h["hotspot"]["topic"] for h in qa_orchestrator.history if h.get("question_id")
    ]
    return {
        "code": 200,
        "data": {
            "total": len(topics),
            "hotspots": topics,
        },
    }


@router.post("/clear-processed-hotspots")
async def clear_processed_hotspots():
    """
    清除已处理热点记录

    ⚠️ 警告：清除后，之前处理过的热点可能会被重新处理
    """
    qa_orchestrator.history.clear()

    return {
        "code": 200,
        "message": "已处理热点记录已清除",
        "data": {"warning": "之前处理过的热点可能会被重新处理"},
    }
