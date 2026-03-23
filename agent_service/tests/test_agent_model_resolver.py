import base64
import json
import os
import unittest
from hashlib import sha256

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ModuleNotFoundError:  # pragma: no cover - local env without optional dependency
    AESGCM = None

from app.core.agent_model_resolver import resolve_agent_model


def _encrypt(payload: dict[str, str], secret: str) -> str:
    if AESGCM is None:
        raise unittest.SkipTest("cryptography is not installed")
    key = sha256(secret.encode("utf-8")).digest()
    aes = AESGCM(key)
    nonce = b"123456789012"
    ciphertext = aes.encrypt(nonce, json.dumps(payload).encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


class TestAgentModelResolver(unittest.TestCase):
    def setUp(self) -> None:
        if AESGCM is None:
            raise unittest.SkipTest("cryptography is not installed")
        os.environ["AGENT_MODEL_SECRET"] = "test-secret"
        self.runtime_cfg = {
            "agent_model_catalog": [
                {
                    "id": "system-glm-4_6",
                    "label": "glm-4.6",
                    "provider_type": "openai_compatible",
                    "base_url": "https://glm.example.com/v1",
                    "api_key": "sk-glm",
                    "model": "glm-4.6",
                    "enabled": True,
                    "is_default": True,
                    "sort_order": 1,
                },
                {
                    "id": "system-gpt-4o-mini",
                    "label": "gpt-4o-mini",
                    "provider_type": "openai_compatible",
                    "base_url": "https://openai.example.com/v1",
                    "api_key": "sk-openai",
                    "model": "gpt-4o-mini",
                    "enabled": True,
                    "is_default": False,
                    "sort_order": 2,
                },
            ]
        }

    def tearDown(self) -> None:
        os.environ.pop("AGENT_MODEL_SECRET", None)

    def test_system_bound_agent_uses_configured_model(self) -> None:
        resolved = resolve_agent_model(
            {
                "model_source": "system",
                "model_id": "system-gpt-4o-mini",
            },
            self.runtime_cfg,
        )
        self.assertEqual("gpt-4o-mini", resolved["label"])
        self.assertFalse(resolved["is_fallback"])

    def test_missing_system_model_falls_back_to_default(self) -> None:
        resolved = resolve_agent_model(
            {
                "model_source": "system",
                "model_id": "removed-model",
            },
            self.runtime_cfg,
        )
        self.assertEqual("glm-4.6", resolved["label"])
        self.assertTrue(resolved["is_fallback"])

    def test_custom_model_resolves_when_valid(self) -> None:
        encrypted = _encrypt(
            {
                "label": "My DeepSeek",
                "provider_type": "openai_compatible",
                "base_url": "https://deepseek.example.com/v1",
                "api_key": "sk-custom",
                "model": "deepseek-chat",
            },
            "test-secret",
        )
        resolved = resolve_agent_model(
            {
                "model_source": "custom",
                "model_config": encrypted,
            },
            self.runtime_cfg,
        )
        self.assertEqual("My DeepSeek", resolved["label"])
        self.assertEqual("deepseek-chat", resolved["model"])
        self.assertFalse(resolved["is_fallback"])

    def test_invalid_custom_model_falls_back_to_default(self) -> None:
        resolved = resolve_agent_model(
            {
                "model_source": "custom",
                "model_config": "invalid-ciphertext",
            },
            self.runtime_cfg,
        )
        self.assertEqual("glm-4.6", resolved["label"])
        self.assertTrue(resolved["is_fallback"])


if __name__ == "__main__":
    unittest.main()
