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
from app.services.model_secret import (
    decrypt_model_config,
    encrypt_model_config,
    mask_api_key,
)


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


def _resolve_model_binding(payload: dict, row: User | None = None) -> tuple[str, str, str]:
    has_model_fields = any(
        key in payload for key in ("model_source", "model_id", "custom_model")
    )
    if not has_model_fields and row is not None:
        return row.model_source or "system", row.model_id or "", row.model_config or ""

    model_source = str(payload.get("model_source") or (row.model_source if row else "system") or "system").strip().lower()
    if model_source not in {"system", "custom"}:
        raise HTTPException(status_code=400, detail="model_source 非法")

    if model_source == "system":
        model_id = str(payload.get("model_id") or "").strip()
        return "system", model_id, ""

    custom_model = payload.get("custom_model") or {}
    if not isinstance(custom_model, dict):
        raise HTTPException(status_code=400, detail="custom_model 非法")

    existing_config = {}
    if row and row.model_source == "custom" and row.model_config:
        try:
            existing_config = decrypt_model_config(row.model_config)
        except Exception:
            existing_config = {}

    label = str(custom_model.get("label") or existing_config.get("label") or "").strip()
    base_url = str(custom_model.get("base_url") or existing_config.get("base_url") or "").strip()
    model_name = str(custom_model.get("model") or existing_config.get("model") or "").strip()
    raw_api_key = custom_model.get("api_key")
    api_key = str(raw_api_key).strip() if raw_api_key is not None else ""
    if not api_key:
        api_key = str(existing_config.get("api_key") or "").strip()

    if not label:
        raise HTTPException(status_code=400, detail="自定义模型别名不能为空")
    if not base_url:
        raise HTTPException(status_code=400, detail="自定义模型 Base URL 不能为空")
    if not model_name:
        raise HTTPException(status_code=400, detail="自定义模型名称不能为空")
    if not api_key:
        raise HTTPException(status_code=400, detail="自定义模型 API Key 不能为空")

    encrypted = encrypt_model_config(
        {
            "label": label,
            "provider_type": "openai_compatible",
            "base_url": base_url,
            "api_key": api_key,
            "model": model_name,
        }
    )
    return "custom", "", encrypted


def _safe_model_info(row: User) -> dict:
    source = row.model_source or "system"
    if source == "custom":
        try:
            custom_model = decrypt_model_config(row.model_config or "")
        except Exception:
            custom_model = {}
        return {
            "source": "custom",
            "label": str(custom_model.get("label") or "自定义模型"),
            "model": str(custom_model.get("model") or ""),
            "provider_type": str(custom_model.get("provider_type") or "openai_compatible"),
            "base_url": str(custom_model.get("base_url") or ""),
            "api_key_masked": mask_api_key(str(custom_model.get("api_key") or "")),
            "is_fallback": False,
        }
    return {
        "source": "system",
        "configured_model_id": row.model_id or "",
        "effective_model_id": row.model_id or "",
        "label": row.model_id or "默认系统模型",
        "is_fallback": False,
    }


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
            "model_source": r.model_source or "system",
            "model_id": r.model_id or "",
            "model_info": _safe_model_info(r),
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

    model_source, model_id, model_config = _resolve_model_binding(payload)

    row = User(
        role="agent",
        name=name,
        avatar=payload.get("avatar", ""),
        owner_id=int(payload.get("owner_id", 0)),
        is_system=bool(payload.get("is_system", False)),
        raw_config=raw_config,
        system_prompt=payload.get("system_prompt", ""),
        expressiveness=expressiveness,
        model_source=model_source,
        model_id=model_id,
        model_config=model_config,
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

    model_source, model_id, model_config = _resolve_model_binding(payload, row=row)
    row.model_source = model_source
    row.model_id = model_id
    row.model_config = model_config

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
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
        resp = await client.post(
            f"{settings.agent_service_base_url}/agent/playground", json=payload
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
