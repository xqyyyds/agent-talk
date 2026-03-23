package service

import "testing"

func TestNormalizeSystemModelCatalogDropsInvalidItems(t *testing.T) {
	items := normalizeSystemModelCatalog([]SystemModelCatalogItem{
		{ID: "a", Label: "glm-4.6", ProviderType: "", BaseURL: "https://a/v1", APIKey: "sk-a", Model: "glm-4.6", Enabled: true, SortOrder: 2},
		{ID: "", Label: "bad", BaseURL: "https://bad", APIKey: "sk-b", Model: "bad"},
		{ID: "b", Label: "gpt-4o-mini", ProviderType: openAICompatibleType, BaseURL: "https://b/v1", APIKey: "sk-b", Model: "gpt-4o-mini", Enabled: true, SortOrder: 1},
	})
	if len(items) != 2 {
		t.Fatalf("expected 2 normalized items, got %d", len(items))
	}
	if items[0].ID != "b" || items[1].ID != "a" {
		t.Fatalf("unexpected sort order: %#v", items)
	}
	if items[1].ProviderType != openAICompatibleType {
		t.Fatalf("expected default provider type, got %s", items[1].ProviderType)
	}
}

func TestDeriveLegacySystemModelCatalog(t *testing.T) {
	runtimeCfg := map[string]string{
		"llm_model":                 `"glm-4.6"`,
		"openai_api_base":           `"https://glm.example.com/v1"`,
		"openai_api_key":            `"sk-glm"`,
		"llm_model_secondary":       `"gpt-4o-mini"`,
		"openai_api_base_secondary": `"https://openai.example.com/v1"`,
		"openai_api_key_secondary":  `"sk-openai"`,
	}
	items := deriveLegacySystemModelCatalog(runtimeCfg)
	if len(items) != 2 {
		t.Fatalf("expected 2 legacy catalog items, got %d", len(items))
	}
	if items[0].ID != legacyPrimaryModelID || !items[0].IsDefault {
		t.Fatalf("expected primary default item, got %#v", items[0])
	}
	if items[1].Label != "gpt-4o-mini" {
		t.Fatalf("unexpected secondary label: %#v", items[1])
	}
}
