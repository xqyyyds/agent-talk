from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.config import settings
from app.core.debate import debate_orchestrator, MAX_CYCLE_COUNT
from app.schemas.models import DebateStartRequest, DebateStatusResponse

router = APIRouter(prefix="/debate", tags=["圆桌辩论"])


@router.post("/start", response_model=dict)
async def start_debate(request: DebateStartRequest, background_tasks: BackgroundTasks):
    if debate_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="辩论会话已在运行中")

    cycle_count = request.cycle_count or settings.debate_default_cycle_count
    if cycle_count > MAX_CYCLE_COUNT:
        raise HTTPException(
            status_code=400, detail=f"单次最多 {MAX_CYCLE_COUNT} 场辩论"
        )

    resume = request.resume
    background_tasks.add_task(
        debate_orchestrator.start_debate_session, cycle_count, resume
    )

    return {
        "code": 200,
        "message": f"辩论会话已启动，计划 {cycle_count} 场",
        "data": {
            "total_cycles": cycle_count,
            "interval_mode": settings.interval_mode,
            "rounds": settings.debate_rounds,
            "speakers_per_round": settings.debate_speakers_per_round,
        },
    }


@router.post("/stop", response_model=dict)
async def stop_debate():
    if not debate_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="没有正在运行的辩论会话")

    debate_orchestrator.stop()
    return {"code": 200, "message": "辩论会话已停止"}


@router.get("/status", response_model=DebateStatusResponse)
async def get_debate_status():
    status = debate_orchestrator.get_status()
    logs = [
        f"[{h.get('cycle','')}] {h.get('topic','')}"
        for h in status.get("history", [])[-20:]
    ]

    return DebateStatusResponse(
        status=status["status"],
        current_cycle=status["current_cycle"],
        total_cycles=status["total_cycles"],
        history_count=status["history_count"],
        logs=logs,
    )


@router.get("/history")
async def get_debate_history(limit: int = 10, offset: int = 0):
    history = debate_orchestrator.history
    total = len(history)
    items = history[offset : offset + limit]
    return {"code": 200, "data": {"total": total, "items": items}}
