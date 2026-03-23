from __future__ import annotations

import base64
import json
from hashlib import sha256
from os import getenv
from typing import Any

from app.core.agent_model_catalog import get_default_system_model, get_system_model_catalog


def _secret() -> str:
    return (getenv("AGENT_MODEL_SECRET") or getenv("JWT_SECRET_KEY") or "").strip()


def decrypt_custom_model_config(ciphertext: str) -> dict[str, Any] | None:
    raw = (ciphertext or "").strip()
    if not raw:
        return None
    secret = _secret()
    if not secret:
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = sha256(secret.encode("utf-8")).digest()
        data = base64.b64decode(raw)
        nonce_size = 12
        if len(data) <= nonce_size:
            return None
        nonce, payload = data[:nonce_size], data[nonce_size:]
        plaintext = AESGCM(key).decrypt(nonce, payload, None)
        parsed = json.loads(plaintext.decode("utf-8"))
        if not isinstance(parsed, dict):
            return None
        return parsed
    except Exception:
        return None


def resolve_agent_model(
    agent: dict[str, Any],
    runtime_cfg: dict[str, Any],
) -> dict[str, Any]:
    catalog = get_system_model_catalog(runtime_cfg)
    default_model = get_default_system_model(catalog)
    model_source = str(agent.get("model_source") or "system").strip() or "system"

    def _fallback(source: str, warning: str) -> dict[str, Any]:
        if default_model:
            return {
                "source": source,
                "configured_model_id": str(agent.get("model_id") or "").strip(),
                "effective_model_id": default_model["id"],
                "label": default_model["label"],
                "provider_type": default_model["provider_type"],
                "base_url": default_model["base_url"],
                "api_key": default_model["api_key"],
                "model": default_model["model"],
                "is_fallback": True,
                "warning": warning,
            }
        return {
            "source": source,
            "configured_model_id": str(agent.get("model_id") or "").strip(),
            "effective_model_id": "",
            "label": "default",
            "provider_type": "openai_compatible",
            "base_url": "",
            "api_key": "",
            "model": "",
            "is_fallback": True,
            "warning": warning,
        }

    if model_source == "custom":
        config = decrypt_custom_model_config(str(agent.get("model_config") or ""))
        if config:
            label = str(config.get("label") or "").strip() or str(config.get("model") or "").strip()
            base_url = str(config.get("base_url") or "").strip()
            api_key = str(config.get("api_key") or "").strip()
            model = str(config.get("model") or "").strip()
            if label and base_url and api_key and model:
                return {
                    "source": "custom",
                    "configured_model_id": "",
                    "effective_model_id": "",
                    "label": label,
                    "provider_type": str(config.get("provider_type") or "openai_compatible").strip() or "openai_compatible",
                    "base_url": base_url,
                    "api_key": api_key,
                    "model": model,
                    "is_fallback": False,
                    "warning": "",
                }
        return _fallback("custom", "自定义模型无效，已自动切换为默认模型")

    configured_id = str(agent.get("model_id") or "").strip()
    if not configured_id and default_model:
        configured_id = default_model["id"]

    for item in catalog:
        if item.get("enabled") and item["id"] == configured_id:
            return {
                "source": "system",
                "configured_model_id": configured_id,
                "effective_model_id": item["id"],
                "label": item["label"],
                "provider_type": item["provider_type"],
                "base_url": item["base_url"],
                "api_key": item["api_key"],
                "model": item["model"],
                "is_fallback": False,
                "warning": "",
            }

    return _fallback("system", "原系统模型已失效，已自动切换为默认模型")
