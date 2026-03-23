import unittest

from app.core.agent_model_catalog import (
    LEGACY_PRIMARY_MODEL_ID,
    LEGACY_SECONDARY_MODEL_ID,
    derive_legacy_system_model_catalog,
    get_default_system_model,
    get_selectable_system_models,
    get_system_model_catalog,
)


class TestAgentModelCatalog(unittest.TestCase):
    def test_prefers_structured_catalog_when_present(self) -> None:
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
            ],
            "llm_model": "legacy-glm",
            "openai_api_base": "https://legacy.example.com/v1",
            "openai_api_key": "sk-legacy",
        }

        catalog = get_system_model_catalog(runtime_cfg)
        self.assertEqual(1, len(catalog))
        self.assertEqual("system-glm-4_6", catalog[0]["id"])

    def test_derives_legacy_catalog_when_structured_catalog_missing(self) -> None:
        runtime_cfg = {
            "llm_model": "glm-4.6",
            "openai_api_base": "https://glm.example.com/v1",
            "openai_api_key": "sk-glm",
            "llm_model_secondary": "gpt-4o-mini",
            "openai_api_base_secondary": "https://openai.example.com/v1",
            "openai_api_key_secondary": "sk-openai",
        }

        catalog = derive_legacy_system_model_catalog(runtime_cfg)
        self.assertEqual(2, len(catalog))
        self.assertEqual(LEGACY_PRIMARY_MODEL_ID, catalog[0]["id"])
        self.assertEqual(LEGACY_SECONDARY_MODEL_ID, catalog[1]["id"])

    def test_default_model_selection_is_stable(self) -> None:
        items = [
            {"id": "a", "enabled": True, "is_default": False},
            {"id": "b", "enabled": True, "is_default": True},
        ]
        default_model = get_default_system_model(items)
        assert default_model is not None
        self.assertEqual("b", default_model["id"])

    def test_disabled_models_are_hidden_from_selectable_list(self) -> None:
        runtime_cfg = {
            "agent_model_catalog": [
                {
                    "id": "on",
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
                    "id": "off",
                    "label": "gpt-4o-mini",
                    "provider_type": "openai_compatible",
                    "base_url": "https://openai.example.com/v1",
                    "api_key": "sk-openai",
                    "model": "gpt-4o-mini",
                    "enabled": False,
                    "is_default": False,
                    "sort_order": 2,
                },
            ]
        }

        selectable = get_selectable_system_models(runtime_cfg)
        self.assertEqual(["on"], [item["id"] for item in selectable])

    def test_first_enabled_model_becomes_default_when_catalog_has_no_default(self) -> None:
        runtime_cfg = {
            "agent_model_catalog": [
                {
                    "id": "a",
                    "label": "glm-4.6",
                    "provider_type": "openai_compatible",
                    "base_url": "https://glm.example.com/v1",
                    "api_key": "sk-glm",
                    "model": "glm-4.6",
                    "enabled": True,
                    "is_default": False,
                    "sort_order": 2,
                },
                {
                    "id": "b",
                    "label": "gpt-4o-mini",
                    "provider_type": "openai_compatible",
                    "base_url": "https://openai.example.com/v1",
                    "api_key": "sk-openai",
                    "model": "gpt-4o-mini",
                    "enabled": True,
                    "is_default": False,
                    "sort_order": 1,
                },
            ]
        }

        catalog = get_system_model_catalog(runtime_cfg)
        default_model = get_default_system_model(catalog)
        assert default_model is not None
        self.assertEqual("b", default_model["id"])


if __name__ == "__main__":
    unittest.main()
