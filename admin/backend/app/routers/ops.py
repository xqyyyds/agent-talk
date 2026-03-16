import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_action
from app.config import settings
from app.database import get_db
from app.deps import get_current_admin
from app.models import AdminAuditLog, AdminUser


router = APIRouter(prefix="/admin/ops", tags=["admin-ops"])


def _normalize_upstream_error(resp: httpx.Response) -> str | dict:
    try:
        payload = resp.json()
    except Exception:
        return resp.text or "upstream request failed"
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail is not None:
            return detail
        return payload
    return payload


async def _proxy(
    method: str,
    path: str,
    *,
    json_payload: dict | None = None,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(
            method,
            f"{settings.agent_service_base_url}{path}",
            json=json_payload,
            params=params,
            headers=headers,
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code, detail=_normalize_upstream_error(resp)
        )
    return resp.json()


@router.post("/debate/start")
async def start_debate(
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    data = await _proxy("POST", "/debate/start", json_payload=payload)
    log_action(
        db,
        current_admin.id,
        "admin.debate_start",
        "debate",
        "0",
        payload=payload,
        request=request,
    )
    return data


@router.post("/debate/stop")
async def stop_debate(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    data = await _proxy("POST", "/debate/stop")
    log_action(
        db, current_admin.id, "admin.debate_stop", "debate", "0", request=request
    )
    return data


@router.get("/debate/status")
async def debate_status(_: AdminUser = Depends(get_current_admin)):
    return await _proxy("GET", "/debate/status")


@router.get("/debate/history")
async def debate_history(_: AdminUser = Depends(get_current_admin)):
    return await _proxy("GET", "/debate/history")


@router.post("/crawler/{source}/jobs")
async def create_crawler_job(
    source: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    source = source.strip().lower()
    if source not in {"zhihu", "weibo"}:
        raise HTTPException(status_code=400, detail="source must be zhihu or weibo")

    data = await _proxy("POST", f"/admin/crawler/{source}/jobs")
    job_id = (
        data.get("data", {}).get("job", {}).get("job_id")
        if isinstance(data, dict)
        else None
    )
    log_action(
        db,
        current_admin.id,
        "admin.create_crawler_job",
        "crawler",
        source,
        payload={"job_id": job_id},
        request=request,
    )
    return data


@router.get("/crawler/jobs")
async def list_crawler_jobs(
    source: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    _: AdminUser = Depends(get_current_admin),
):
    params = {"limit": limit}
    if source:
        params["source"] = source
    return await _proxy("GET", "/admin/crawler/jobs", params=params)


@router.get("/crawler/jobs/{job_id}")
async def get_crawler_job(
    job_id: str,
    _: AdminUser = Depends(get_current_admin),
):
    return await _proxy("GET", f"/admin/crawler/jobs/{job_id}")


@router.get("/crawler/jobs/{job_id}/logs")
async def get_crawler_job_logs(
    job_id: str,
    tail: int = Query(default=200, ge=1, le=2000),
    _: AdminUser = Depends(get_current_admin),
):
    return await _proxy(
        "GET", f"/admin/crawler/jobs/{job_id}/logs", params={"tail": tail}
    )


# Backward-compatible endpoints kept for existing clients.
@router.post("/crawler/zhihu/run")
async def run_zhihu_crawler(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    return await create_crawler_job(
        source="zhihu", db=db, current_admin=current_admin, request=request
    )


@router.post("/crawler/weibo/run")
async def run_weibo_crawler(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    return await create_crawler_job(
        source="weibo", db=db, current_admin=current_admin, request=request
    )


@router.get("/runtime-config")
async def get_runtime_config(_: AdminUser = Depends(get_current_admin)):
    headers = {"x-runtime-token": settings.agent_service_runtime_token}
    return await _proxy(
        "GET",
        "/admin/runtime-config",
        headers=headers,
    )


@router.put("/runtime-config")
async def update_runtime_config(
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    headers = {"x-runtime-token": settings.agent_service_runtime_token}
    data = await _proxy(
        "PUT",
        "/admin/runtime-config",
        headers=headers,
        json_payload=payload,
    )
    log_action(
        db,
        current_admin.id,
        "admin.update_runtime_config",
        "runtime_config",
        "agent_service",
        payload={"keys": list(payload.keys())},
        request=request,
    )
    return data


@router.get("/audit/logs")
def audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    limit = max(1, min(500, limit))
    rows = db.query(AdminAuditLog).order_by(AdminAuditLog.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "admin_id": r.admin_id,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "reason": r.reason,
            "payload_json": json.loads(r.payload_json or "{}"),
            "ip": r.ip,
            "created_at": r.created_at,
        }
        for r in rows
    ]
