from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.core.runtime_config import get_runtime_config, update_runtime_config


router = APIRouter(prefix="/admin/runtime-config", tags=["管理员运行时配置"])


def _verify_runtime_token(token: str | None) -> None:
    if not token or token != settings.runtime_config_token:
        raise HTTPException(status_code=401, detail="invalid runtime token")


@router.get("")
async def get_config(x_runtime_token: str | None = Header(default=None)):
    _verify_runtime_token(x_runtime_token)
    config = await get_runtime_config(force_refresh=True)
    return {"code": 200, "data": config}


@router.put("")
async def update_config(payload: dict[str, Any], x_runtime_token: str | None = Header(default=None)):
    _verify_runtime_token(x_runtime_token)
    config = await update_runtime_config(payload)
    return {"code": 200, "message": "updated", "data": config}
