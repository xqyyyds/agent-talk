import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import log_action
from app.config import settings
from app.database import get_db
from app.delete_utils import hard_delete_user
from app.deps import get_current_admin
from app.models import AdminUser, User


router = APIRouter(prefix="/admin/agents", tags=["admin-agents"])


def _build_raw_config(payload: dict, current: dict | None = None) -> str:
    base = current or {}
    merged = {
        "headline": payload.get("headline", base.get("headline", "")),
        "bio": payload.get("bio", base.get("bio", "")),
        "topics": payload.get("topics", base.get("topics", [])),
        "bias": payload.get("bias", base.get("bias", "")),
        "style_tag": payload.get("style_tag", base.get("style_tag", "")),
        "reply_mode": payload.get("reply_mode", base.get("reply_mode", "balanced")),
        "activity_level": payload.get(
            "activity_level", base.get("activity_level", "medium")
        ),
        "expressiveness": payload.get(
            "expressiveness", base.get("expressiveness", "balanced")
        ),
    }
    return json.dumps(merged, ensure_ascii=False)


@router.get("")
def list_agents(
    db: Session = Depends(get_db), _: AdminUser = Depends(get_current_admin)
):
    rows = (
        db.query(User)
        .filter(User.role == "agent", User.deleted_at.is_(None))
        .order_by(User.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "avatar": r.avatar,
            "owner_id": r.owner_id,
            "is_system": r.is_system,
            "raw_config": r.raw_config,
            "system_prompt": r.system_prompt,
            "expressiveness": r.expressiveness,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("")
def create_agent(
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    name = str(payload.get("name", "")).strip()
    if len(name) < 2 or len(name) > 50:
        raise HTTPException(status_code=400, detail="Agent 名称长度应为 2-50")

    topics = payload.get("topics", [])
    if not isinstance(topics, list) or len(topics) == 0:
        raise HTTPException(status_code=400, detail="topics 至少包含一个话题")

    expressiveness = payload.get("expressiveness", "balanced")
    if expressiveness not in ("terse", "balanced", "verbose", "dynamic"):
        raise HTTPException(status_code=400, detail="expressiveness 非法")

    raw_config = _build_raw_config(payload)

    row = User(
        role="agent",
        name=name,
        avatar=payload.get("avatar", ""),
        owner_id=int(payload.get("owner_id", 0)),
        is_system=bool(payload.get("is_system", False)),
        raw_config=raw_config,
        system_prompt=payload.get("system_prompt", ""),
        expressiveness=expressiveness,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(
        db,
        current_admin.id,
        "admin.create_agent",
        "agent",
        str(row.id),
        request=request,
    )
    return {"message": "创建成功", "id": row.id}


@router.patch("/{agent_id}")
def update_agent(
    agent_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = (
        db.query(User)
        .filter(User.id == agent_id, User.role == "agent", User.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    for key in ("name", "avatar", "system_prompt", "expressiveness"):
        if key in payload:
            setattr(row, key, payload[key])

    try:
        current_raw = json.loads(row.raw_config) if row.raw_config else {}
    except Exception:
        current_raw = {}

    if any(
        k in payload
        for k in (
            "headline",
            "bio",
            "topics",
            "bias",
            "style_tag",
            "reply_mode",
            "activity_level",
            "expressiveness",
        )
    ):
        row.raw_config = _build_raw_config(payload, current=current_raw)

    if "is_system" in payload:
        row.is_system = bool(payload["is_system"])

    db.commit()
    log_action(
        db,
        current_admin.id,
        "admin.update_agent",
        "agent",
        str(agent_id),
        payload={"keys": list(payload.keys())},
        request=request,
    )
    return {"message": "更新成功"}


@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = (
        db.query(User)
        .filter(User.id == agent_id, User.role == "agent", User.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    try:
        hard_delete_user(db, agent_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    log_action(
        db,
        current_admin.id,
        "admin.delete_agent",
        "agent",
        str(agent_id),
        request=request,
    )
    return {"message": "删除成功（硬删除）"}


@router.post("/optimize")
async def optimize_agent_payload(
    payload: dict,
    _: AdminUser = Depends(get_current_admin),
):
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.agent_service_base_url}/agent/optimize", json=payload
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/playground")
async def playground_agent_payload(
    payload: dict,
    _: AdminUser = Depends(get_current_admin),
):
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.agent_service_base_url}/agent/playground", json=payload
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
