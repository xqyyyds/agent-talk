from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.core.agent_model_catalog import (
    get_default_system_model,
    get_selectable_system_models,
    get_system_model_catalog,
    normalize_system_model_catalog,
)
from app.core.runtime_config import get_runtime_config, update_runtime_config


router = APIRouter(prefix="/admin/model-catalog", tags=["管理员模型目录"])


def _verify_runtime_token(token: str | None) -> None:
    if not token or token != settings.runtime_config_token:
        raise HTTPException(status_code=401, detail="invalid runtime token")


class ModelCatalogItemPayload(BaseModel):
    id: str
    label: str
    provider_type: str = "openai_compatible"
    base_url: str
    api_key: str
    model: str
    enabled: bool = True
    is_default: bool = False
    sort_order: int = 0


class ReorderModelCatalogPayload(BaseModel):
    ids: list[str] = Field(default_factory=list)


def _catalog_response(runtime_cfg: dict[str, Any]) -> dict[str, Any]:
    catalog = get_system_model_catalog(runtime_cfg)
    default_model = get_default_system_model(catalog)
    return {
        "models": catalog,
        "selectable_models": get_selectable_system_models(runtime_cfg),
        "default_model_id": default_model["id"] if default_model else "",
        "agent_model_catalog": catalog,
    }


def _merge_catalog_item(
    catalog: list[dict[str, Any]],
    item_id: str,
    payload: ModelCatalogItemPayload,
) -> list[dict[str, Any]]:
    item = payload.model_dump()
    updated = False
    merged: list[dict[str, Any]] = []
    for entry in catalog:
        if entry["id"] == item_id:
            merged.append(item)
            updated = True
        else:
            merged.append(entry)
    if not updated:
        merged.append(item)
    return normalize_system_model_catalog(merged)


def _with_default(catalog: list[dict[str, Any]], model_id: str) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    for entry in catalog:
        next_entry = dict(entry)
        next_entry["is_default"] = entry["id"] == model_id and entry.get("enabled", True)
        updated.append(next_entry)
    return normalize_system_model_catalog(updated)


@router.get("")
async def get_model_catalog(x_runtime_token: str | None = Header(default=None)):
    _verify_runtime_token(x_runtime_token)
    runtime_cfg = await get_runtime_config(force_refresh=True)
    return {"code": 200, "data": _catalog_response(runtime_cfg)}


@router.post("")
async def create_model_catalog_item(
    payload: ModelCatalogItemPayload,
    x_runtime_token: str | None = Header(default=None),
):
    _verify_runtime_token(x_runtime_token)
    runtime_cfg = await get_runtime_config(force_refresh=True)
    catalog = get_system_model_catalog(runtime_cfg)
    if any(entry["id"] == payload.id for entry in catalog):
        raise HTTPException(status_code=409, detail="model id already exists")
    next_catalog = normalize_system_model_catalog(catalog + [payload.model_dump()])
    if payload.is_default:
        next_catalog = _with_default(next_catalog, payload.id)
    updated = await update_runtime_config({"agent_model_catalog": next_catalog})
    return {"code": 200, "message": "created", "data": _catalog_response(updated)}


@router.put("/{item_id}")
async def update_model_catalog_item(
    item_id: str,
    payload: ModelCatalogItemPayload,
    x_runtime_token: str | None = Header(default=None),
):
    _verify_runtime_token(x_runtime_token)
    runtime_cfg = await get_runtime_config(force_refresh=True)
    catalog = get_system_model_catalog(runtime_cfg)
    if not any(entry["id"] == item_id for entry in catalog):
        raise HTTPException(status_code=404, detail="model not found")
    next_catalog = _merge_catalog_item(catalog, item_id, payload)
    if payload.is_default:
        next_catalog = _with_default(next_catalog, payload.id)
    updated = await update_runtime_config({"agent_model_catalog": next_catalog})
    return {"code": 200, "message": "updated", "data": _catalog_response(updated)}


@router.post("/{item_id}/enable")
async def enable_model_catalog_item(
    item_id: str,
    x_runtime_token: str | None = Header(default=None),
):
    _verify_runtime_token(x_runtime_token)
    runtime_cfg = await get_runtime_config(force_refresh=True)
    catalog = get_system_model_catalog(runtime_cfg)
    next_catalog = []
    found = False
    for entry in catalog:
        next_entry = dict(entry)
        if entry["id"] == item_id:
            next_entry["enabled"] = True
            found = True
        next_catalog.append(next_entry)
    if not found:
        raise HTTPException(status_code=404, detail="model not found")
    updated = await update_runtime_config({"agent_model_catalog": normalize_system_model_catalog(next_catalog)})
    return {"code": 200, "message": "enabled", "data": _catalog_response(updated)}


@router.post("/{item_id}/disable")
async def disable_model_catalog_item(
    item_id: str,
    x_runtime_token: str | None = Header(default=None),
):
    _verify_runtime_token(x_runtime_token)
    runtime_cfg = await get_runtime_config(force_refresh=True)
    catalog = get_system_model_catalog(runtime_cfg)
    next_catalog = []
    found = False
    for entry in catalog:
        next_entry = dict(entry)
        if entry["id"] == item_id:
            next_entry["enabled"] = False
            next_entry["is_default"] = False
            found = True
        next_catalog.append(next_entry)
    if not found:
        raise HTTPException(status_code=404, detail="model not found")
    updated = await update_runtime_config({"agent_model_catalog": normalize_system_model_catalog(next_catalog)})
    return {"code": 200, "message": "disabled", "data": _catalog_response(updated)}


@router.post("/{item_id}/set-default")
async def set_default_model_catalog_item(
    item_id: str,
    x_runtime_token: str | None = Header(default=None),
):
    _verify_runtime_token(x_runtime_token)
    runtime_cfg = await get_runtime_config(force_refresh=True)
    catalog = get_system_model_catalog(runtime_cfg)
    if not any(entry["id"] == item_id for entry in catalog):
        raise HTTPException(status_code=404, detail="model not found")
    next_catalog = _with_default(catalog, item_id)
    updated = await update_runtime_config({"agent_model_catalog": next_catalog})
    return {"code": 200, "message": "default updated", "data": _catalog_response(updated)}


@router.post("/reorder")
async def reorder_model_catalog(
    payload: ReorderModelCatalogPayload,
    x_runtime_token: str | None = Header(default=None),
):
    _verify_runtime_token(x_runtime_token)
    runtime_cfg = await get_runtime_config(force_refresh=True)
    catalog = get_system_model_catalog(runtime_cfg)
    order_map = {item_id: index + 1 for index, item_id in enumerate(payload.ids)}
    next_catalog = []
    for entry in catalog:
        next_entry = dict(entry)
        if entry["id"] in order_map:
            next_entry["sort_order"] = order_map[entry["id"]]
        next_catalog.append(next_entry)
    updated = await update_runtime_config({"agent_model_catalog": normalize_system_model_catalog(next_catalog)})
    return {"code": 200, "message": "reordered", "data": _catalog_response(updated)}
