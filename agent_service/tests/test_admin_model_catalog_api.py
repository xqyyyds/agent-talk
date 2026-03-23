import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent_service"))

from app.api import admin_model_catalog  # noqa: E402


class TestAdminModelCatalogAPI(unittest.TestCase):
    def test_get_model_catalog_returns_selectable_models(self) -> None:
        runtime_cfg = {
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
                }
            ]
        }
        with patch.object(
            admin_model_catalog,
            "get_runtime_config",
            AsyncMock(return_value=runtime_cfg),
        ):
            payload = asyncio.run(admin_model_catalog.get_model_catalog("change-this-runtime-token"))

        self.assertEqual(200, payload["code"])
        self.assertEqual("system-glm-4_6", payload["data"]["models"][0]["id"])

    def test_update_model_catalog_item_persists_changes(self) -> None:
        runtime_cfg = {
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
                }
            ]
        }
        updated_cfg = {
            "agent_model_catalog": [
                {
                    "id": "system-glm-4_6",
                    "label": "glm-4.6-updated",
                    "provider_type": "openai_compatible",
                    "base_url": "https://glm.example.com/v1",
                    "api_key": "sk-glm",
                    "model": "glm-4.6",
                    "enabled": True,
                    "is_default": True,
                    "sort_order": 1,
                }
            ]
        }
        with (
            patch.object(
                admin_model_catalog,
                "get_runtime_config",
                AsyncMock(return_value=runtime_cfg),
            ),
            patch.object(
                admin_model_catalog,
                "update_runtime_config",
                AsyncMock(return_value=updated_cfg),
            ) as mocked_update,
        ):
            payload = asyncio.run(
                admin_model_catalog.update_model_catalog_item(
                    "system-glm-4_6",
                    admin_model_catalog.ModelCatalogItemPayload(
                        id="system-glm-4_6",
                        label="glm-4.6-updated",
                        provider_type="openai_compatible",
                        base_url="https://glm.example.com/v1",
                        api_key="sk-glm",
                        model="glm-4.6",
                        enabled=True,
                        is_default=True,
                        sort_order=1,
                    ),
                    "change-this-runtime-token",
                )
            )

        mocked_update.assert_awaited()
        self.assertEqual(200, payload["code"])
        self.assertEqual("glm-4.6-updated", payload["data"]["agent_model_catalog"][0]["label"])

