from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.clients.backend_api import backend_client
from app.clients.llm_client import llm_client
from app.config import settings
from app.core.agent_manager import agent_manager
from app.core.langgraph_qa import qa_orchestrator
from app.schemas.models import QAStartRequest, QAStatusResponse


router = APIRouter(prefix="/qa", tags=["问答管理"])
manual_answer_tasks: Dict[str, dict] = {}


@router.post("/start", response_model=dict)
async def start_qa(request: QAStartRequest, background_tasks: BackgroundTasks):
    """启动问答会话（后台任务）。"""
    if qa_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="问答会话已在运行中")

    cycle_count = request.cycle_count or settings.qa_default_cycle_count
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
            "categories": request.categories or "自动提取所有分类",
            "source": request.source or "全部来源",
            "interval_mode": settings.interval_mode,
        },
    }


@router.post("/stop", response_model=dict)
async def stop_qa():
    """停止当前问答会话。"""
    if not qa_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="没有正在运行的问答会话")

    qa_orchestrator.stop()
    return {"code": 200, "message": "问答会话已停止"}


@router.get("/status", response_model=QAStatusResponse)
async def get_qa_status():
    """获取问答状态。"""
    status = qa_orchestrator.get_status()
    agents_status = agent_manager.get_agent_status()

    history = status.get("history", [])
    logs = [f"[{h.get('cycle', '')}] {h['hotspot']['topic']}" for h in history[-20:]]

    return QAStatusResponse(
        status=status["status"],
        current_cycle=status["current_cycle"],
        total_cycles=status["total_cycles"],
        agents_status=agents_status,
        logs=logs,
    )


@router.get("/history")
async def get_qa_history(limit: int = 10, offset: int = 0):
    """获取问答历史记录。"""
    history = qa_orchestrator.history
    total = len(history)
    paginated_history = history[offset : offset + limit]
    return {"code": 200, "data": {"total": total, "items": paginated_history}}


@router.get("/processed-hotspots")
async def get_processed_hotspots():
    """获取已处理热点列表。"""
    topics = [
        h["hotspot"]["topic"] for h in qa_orchestrator.history if h.get("question_id")
    ]
    return {"code": 200, "data": {"total": len(topics), "hotspots": topics}}


@router.post("/clear-processed-hotspots")
async def clear_processed_hotspots():
    """清空已处理热点记录。"""
    qa_orchestrator.history.clear()
    return {
        "code": 200,
        "message": "已处理热点记录已清空",
        "data": {"warning": "之前处理过的热点可能会再次被处理"},
    }


class ManualAnswerRequest(BaseModel):
    question_id: int = Field(..., ge=1)
    agent_ids: List[int] = Field(default_factory=list)


async def _execute_manual_answer(task_id: str, request: ManualAnswerRequest):
    task = manual_answer_tasks.get(task_id)
    if task is None:
        return
    task["status"] = "running"
    task["started_at"] = datetime.utcnow().isoformat()

    if not request.agent_ids:
        task["status"] = "failed"
        task["error"] = "请至少选择一个 Agent"
        task["finished_at"] = datetime.utcnow().isoformat()
        return

    await agent_manager.refresh_agents()
    if not agent_manager.agents:
        await agent_manager.initialize()

    question = await backend_client.get_question_detail(request.question_id)
    if not question:
        task["status"] = "failed"
        task["error"] = "问题不存在"
        task["finished_at"] = datetime.utcnow().isoformat()
        return

    existing_answers = await backend_client.get_answer_list(
        question_id=request.question_id,
        limit=50,
    )
    existing_viewpoints = [str(a.get("content", ""))[:120] for a in existing_answers]

    selected_agents = [
        agent
        for agent in agent_manager.agents
        if agent.user_id in request.agent_ids and agent.token
    ]
    if not selected_agents:
        task["status"] = "failed"
        task["error"] = "未找到可用 Agent"
        task["finished_at"] = datetime.utcnow().isoformat()
        return

    results = []
    for agent in selected_agents:
        try:
            answer_output = await llm_client.generate_answer(
                agent=agent,
                question={
                    "id": question.get("id"),
                    "title": question.get("title", ""),
                    "content": question.get("content", ""),
                },
                existing_answers=existing_viewpoints,
            )

            await backend_client.create_answer(
                token=agent.token,
                question_id=request.question_id,
                content=answer_output.content,
            )
            await agent_manager.update_stats(agent.username, answer_created=True)
            results.append(
                {
                    "agent_id": agent.user_id,
                    "agent_name": agent.username,
                    "status": "success",
                }
            )
        except Exception as e:
            results.append(
                {
                    "agent_id": agent.user_id,
                    "agent_name": agent.username,
                    "status": "failed",
                    "error": str(e),
                }
            )

    success_count = len([item for item in results if item.get("status") == "success"])
    task["status"] = "completed"
    task["finished_at"] = datetime.utcnow().isoformat()
    task["results"] = results
    task["success_count"] = success_count
    task["total_count"] = len(results)
    task["question_id"] = request.question_id


@router.post("/manual-answer", response_model=dict)
async def manual_answer(request: ManualAnswerRequest, background_tasks: BackgroundTasks):
    """手动触发指定 Agent 回答某个问题。"""
    if not request.agent_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个 Agent")

    task_id = uuid4().hex
    manual_answer_tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "question_id": request.question_id,
        "agent_ids": request.agent_ids,
        "created_at": datetime.utcnow().isoformat(),
        "results": [],
        "success_count": 0,
        "total_count": len(request.agent_ids),
    }
    background_tasks.add_task(_execute_manual_answer, task_id, request)

    return {
        "code": 200,
        "message": "任务已提交，Agent 将在后台继续回答",
        "data": {
            "task_id": task_id,
            "status": "queued",
            "question_id": request.question_id,
            "agent_ids": request.agent_ids,
        },
    }


@router.get("/manual-answer/status/{task_id}", response_model=dict)
async def get_manual_answer_status(task_id: str):
    task = manual_answer_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "code": 200,
        "data": task,
    }
