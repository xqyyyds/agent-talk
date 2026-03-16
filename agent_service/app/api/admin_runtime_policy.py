from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.core.operations_engine import operations_engine
from app.core.runtime_policy import (
    POLICY_DEBATE,
    POLICY_QA,
    POLICY_REALTIME,
    POLICY_SCHEDULER,
    get_runtime_policy,
    get_runtime_policies,
    update_runtime_policy,
)


router = APIRouter(prefix="/admin/runtime", tags=["admin-runtime-policy"])


def _verify_runtime_token(token: str | None) -> None:
    if not token or token != settings.runtime_config_token:
        raise HTTPException(status_code=401, detail="invalid runtime token")


async def _get_policy(policy_name: str, x_runtime_token: str | None) -> dict:
    _verify_runtime_token(x_runtime_token)
    policy = await get_runtime_policy(policy_name)
    return {"code": 200, "data": policy}


async def _put_policy(policy_name: str, payload: dict, x_runtime_token: str | None) -> dict:
    _verify_runtime_token(x_runtime_token)
    policy = await update_runtime_policy(policy_name, payload or {})
    return {"code": 200, "message": "updated", "data": policy}


@router.get("/qa-policy")
async def get_qa_policy(x_runtime_token: str | None = Header(default=None)):
    return await _get_policy(POLICY_QA, x_runtime_token)


@router.put("/qa-policy")
async def put_qa_policy(payload: dict, x_runtime_token: str | None = Header(default=None)):
    return await _put_policy(POLICY_QA, payload, x_runtime_token)


@router.get("/debate-policy")
async def get_debate_policy(x_runtime_token: str | None = Header(default=None)):
    return await _get_policy(POLICY_DEBATE, x_runtime_token)


@router.put("/debate-policy")
async def put_debate_policy(payload: dict, x_runtime_token: str | None = Header(default=None)):
    return await _put_policy(POLICY_DEBATE, payload, x_runtime_token)


@router.get("/scheduler-policy")
async def get_scheduler_policy(x_runtime_token: str | None = Header(default=None)):
    return await _get_policy(POLICY_SCHEDULER, x_runtime_token)


@router.put("/scheduler-policy")
async def put_scheduler_policy(payload: dict, x_runtime_token: str | None = Header(default=None)):
    return await _put_policy(POLICY_SCHEDULER, payload, x_runtime_token)


@router.get("/realtime-policy")
async def get_realtime_policy(x_runtime_token: str | None = Header(default=None)):
    return await _get_policy(POLICY_REALTIME, x_runtime_token)


@router.put("/realtime-policy")
async def put_realtime_policy(payload: dict, x_runtime_token: str | None = Header(default=None)):
    return await _put_policy(POLICY_REALTIME, payload, x_runtime_token)


@router.get("/capacity")
async def get_capacity_snapshot(x_runtime_token: str | None = Header(default=None)):
    _verify_runtime_token(x_runtime_token)
    policies = await get_runtime_policies()
    snapshot = operations_engine.snapshot()
    return {
        "code": 200,
        "data": {
            "targets": {
                "online_users": 2000,
                "login_peak_per_second": 80,
                "sustained_qps": 500,
            },
            "policies": policies,
            "engine": snapshot,
        },
    }
