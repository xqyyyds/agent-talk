from __future__ import annotations

from typing import Any


LEGACY_PRIMARY_MODEL_ID = "legacy-primary"
LEGACY_SECONDARY_MODEL_ID = "legacy-secondary"
OPENAI_COMPATIBLE_TYPE = "openai_compatible"


def _to_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_system_model_catalog(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        model_id = _to_str(item.get("id"))
        label = _to_str(item.get("label"))
        provider_type = _to_str(item.get("provider_type")) or OPENAI_COMPATIBLE_TYPE
        base_url = _to_str(item.get("base_url"))
        api_key = _to_str(item.get("api_key"))
        model = _to_str(item.get("model"))
        enabled = bool(item.get("enabled", True))
        sort_order = int(item.get("sort_order", 0) or 0)
        is_default = bool(item.get("is_default", False))

        if not (model_id and label and base_url and api_key and model):
            continue

        normalized.append(
            {
                "id": model_id,
                "label": label,
                "provider_type": provider_type,
                "base_url": base_url,
                "api_key": api_key,
                "model": model,
                "enabled": enabled,
                "is_default": is_default,
                "sort_order": sort_order,
            }
        )

    normalized.sort(key=lambda item: (int(item.get("sort_order", 0)), item["id"]))
    enabled_items = [item for item in normalized if item.get("enabled")]
    has_default = any(item.get("enabled") and item.get("is_default") for item in normalized)
    if enabled_items and not has_default:
        enabled_items[0]["is_default"] = True
    return normalized


def derive_legacy_system_model_catalog(
    runtime_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    primary_model = _to_str(runtime_cfg.get("llm_model"))
    primary_base = _to_str(runtime_cfg.get("openai_api_base"))
    primary_key = _to_str(runtime_cfg.get("openai_api_key"))
    if primary_model and primary_base and primary_key:
        items.append(
            {
                "id": LEGACY_PRIMARY_MODEL_ID,
                "label": primary_model,
                "provider_type": OPENAI_COMPATIBLE_TYPE,
                "base_url": primary_base,
                "api_key": primary_key,
                "model": primary_model,
                "enabled": True,
                "is_default": True,
                "sort_order": 1,
            }
        )

    secondary_model = _to_str(runtime_cfg.get("llm_model_secondary"))
    secondary_base = _to_str(runtime_cfg.get("openai_api_base_secondary"))
    secondary_key = _to_str(runtime_cfg.get("openai_api_key_secondary"))
    if secondary_model and secondary_base and secondary_key:
        items.append(
            {
                "id": LEGACY_SECONDARY_MODEL_ID,
                "label": secondary_model,
                "provider_type": OPENAI_COMPATIBLE_TYPE,
                "base_url": secondary_base,
                "api_key": secondary_key,
                "model": secondary_model,
                "enabled": True,
                "is_default": len(items) == 0,
                "sort_order": 2,
            }
        )

    return items


def get_system_model_catalog(runtime_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    configured = runtime_cfg.get("agent_model_catalog")
    if isinstance(configured, list):
        normalized = normalize_system_model_catalog(configured)
        if normalized:
            return normalized
    return normalize_system_model_catalog(derive_legacy_system_model_catalog(runtime_cfg))


def get_default_system_model(
    items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for item in items:
        if item.get("enabled") and item.get("is_default"):
            return item
    for item in items:
        if item.get("enabled"):
            return item
    return None


def get_selectable_system_models(
    runtime_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    return [item for item in get_system_model_catalog(runtime_cfg) if item.get("enabled")]
