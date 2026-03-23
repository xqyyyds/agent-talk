package service

import (
	"backend/internal/database"
	"backend/internal/model"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
)

const (
	ModelSourceSystem = "system"
	ModelSourceCustom = "custom"

	defaultRuntimeConfigKey = "agent_service:runtime_config"
	legacyPrimaryModelID    = "legacy-primary"
	legacySecondaryModelID  = "legacy-secondary"
	openAICompatibleType    = "openai_compatible"
)

type SystemModelCatalogItem struct {
	ID           string `json:"id"`
	Label        string `json:"label"`
	ProviderType string `json:"provider_type"`
	BaseURL      string `json:"base_url"`
	APIKey       string `json:"api_key"`
	Model        string `json:"model"`
	Enabled      bool   `json:"enabled"`
	IsDefault    bool   `json:"is_default"`
	SortOrder    int    `json:"sort_order"`
}

type SystemModelOption struct {
	ID           string `json:"id"`
	Label        string `json:"label"`
	ProviderType string `json:"provider_type"`
	IsDefault    bool   `json:"is_default"`
}

type CustomModelConfig struct {
	Label        string `json:"label"`
	ProviderType string `json:"provider_type"`
	BaseURL      string `json:"base_url"`
	APIKey       string `json:"api_key,omitempty"`
	Model        string `json:"model"`
}

type AgentModelInfo struct {
	Source            string `json:"source"`
	ConfiguredModelID string `json:"configured_model_id,omitempty"`
	EffectiveModelID  string `json:"effective_model_id,omitempty"`
	Label             string `json:"label"`
	Model             string `json:"model,omitempty"`
	BaseURL           string `json:"base_url,omitempty"`
	APIKeyMasked      string `json:"api_key_masked,omitempty"`
	IsFallback        bool   `json:"is_fallback"`
	Warning           string `json:"warning,omitempty"`
}

type AgentModelOptionsResponse struct {
	SystemModels   []SystemModelOption `json:"system_models"`
	DefaultModelID string              `json:"default_model_id"`
}

func normalizeSystemModelCatalog(items []SystemModelCatalogItem) []SystemModelCatalogItem {
	normalized := make([]SystemModelCatalogItem, 0, len(items))
	for _, item := range items {
		item.ID = strings.TrimSpace(item.ID)
		item.Label = strings.TrimSpace(item.Label)
		item.ProviderType = strings.TrimSpace(item.ProviderType)
		item.BaseURL = strings.TrimSpace(item.BaseURL)
		item.APIKey = strings.TrimSpace(item.APIKey)
		item.Model = strings.TrimSpace(item.Model)
		if item.ID == "" || item.Label == "" || item.BaseURL == "" || item.APIKey == "" || item.Model == "" {
			continue
		}
		if item.ProviderType == "" {
			item.ProviderType = openAICompatibleType
		}
		normalized = append(normalized, item)
	}
	sort.SliceStable(normalized, func(i, j int) bool {
		if normalized[i].SortOrder == normalized[j].SortOrder {
			return normalized[i].ID < normalized[j].ID
		}
		return normalized[i].SortOrder < normalized[j].SortOrder
	})
	return normalized
}

func runtimeConfigKey() string {
	key := strings.TrimSpace(os.Getenv("RUNTIME_CONFIG_KEY"))
	if key == "" {
		return defaultRuntimeConfigKey
	}
	return key
}

func loadRuntimeConfigMap() (map[string]string, error) {
	if database.RedisClient == nil {
		return nil, fmt.Errorf("redis client not initialized")
	}
	result, err := database.RedisClient.HGetAll(context.Background(), runtimeConfigKey()).Result()
	if err != nil {
		return nil, err
	}
	return result, nil
}

func deriveLegacySystemModelCatalog(runtimeCfg map[string]string) []SystemModelCatalogItem {
	items := make([]SystemModelCatalogItem, 0, 2)

	primaryModel := strings.TrimSpace(parseJSONString(runtimeCfg["llm_model"]))
	primaryBase := strings.TrimSpace(parseJSONString(runtimeCfg["openai_api_base"]))
	primaryKey := strings.TrimSpace(parseJSONString(runtimeCfg["openai_api_key"]))
	if primaryModel != "" && primaryBase != "" && primaryKey != "" {
		items = append(items, SystemModelCatalogItem{
			ID:           legacyPrimaryModelID,
			Label:        primaryModel,
			ProviderType: openAICompatibleType,
			BaseURL:      primaryBase,
			APIKey:       primaryKey,
			Model:        primaryModel,
			Enabled:      true,
			IsDefault:    true,
			SortOrder:    1,
		})
	}

	secondaryModel := strings.TrimSpace(parseJSONString(runtimeCfg["llm_model_secondary"]))
	secondaryBase := strings.TrimSpace(parseJSONString(runtimeCfg["openai_api_base_secondary"]))
	secondaryKey := strings.TrimSpace(parseJSONString(runtimeCfg["openai_api_key_secondary"]))
	if secondaryModel != "" && secondaryBase != "" && secondaryKey != "" {
		items = append(items, SystemModelCatalogItem{
			ID:           legacySecondaryModelID,
			Label:        secondaryModel,
			ProviderType: openAICompatibleType,
			BaseURL:      secondaryBase,
			APIKey:       secondaryKey,
			Model:        secondaryModel,
			Enabled:      true,
			IsDefault:    len(items) == 0,
			SortOrder:    2,
		})
	}

	return items
}

func parseJSONString(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}
	var parsed string
	if err := json.Unmarshal([]byte(raw), &parsed); err == nil {
		return parsed
	}
	return raw
}

func LoadSystemModelCatalog() ([]SystemModelCatalogItem, error) {
	runtimeCfg, err := loadRuntimeConfigMap()
	if err != nil {
		return nil, err
	}

	if rawCatalog := strings.TrimSpace(runtimeCfg["agent_model_catalog"]); rawCatalog != "" {
		var items []SystemModelCatalogItem
		if err := json.Unmarshal([]byte(rawCatalog), &items); err == nil {
			normalized := normalizeSystemModelCatalog(items)
			if len(normalized) > 0 {
				return normalized, nil
			}
		}
	}

	return normalizeSystemModelCatalog(deriveLegacySystemModelCatalog(runtimeCfg)), nil
}

func FindDefaultSystemModel(items []SystemModelCatalogItem) *SystemModelCatalogItem {
	for i := range items {
		if items[i].Enabled && items[i].IsDefault {
			return &items[i]
		}
	}
	for i := range items {
		if items[i].Enabled {
			return &items[i]
		}
	}
	return nil
}

func BuildAgentModelOptions() (*AgentModelOptionsResponse, error) {
	catalog, err := LoadSystemModelCatalog()
	if err != nil {
		return nil, err
	}
	options := make([]SystemModelOption, 0, len(catalog))
	defaultItem := FindDefaultSystemModel(catalog)
	defaultID := ""
	if defaultItem != nil {
		defaultID = defaultItem.ID
	}
	for _, item := range catalog {
		if !item.Enabled {
			continue
		}
		options = append(options, SystemModelOption{
			ID:           item.ID,
			Label:        item.Label,
			ProviderType: item.ProviderType,
			IsDefault:    item.ID == defaultID,
		})
	}
	return &AgentModelOptionsResponse{
		SystemModels:   options,
		DefaultModelID: defaultID,
	}, nil
}

func MaskAPIKey(key string) string {
	key = strings.TrimSpace(key)
	if key == "" {
		return ""
	}
	if len(key) <= 8 {
		return key[:2] + "***"
	}
	return key[:3] + "***" + key[len(key)-4:]
}

func ResolveAgentModelInfo(agent *model.User) *AgentModelInfo {
	if agent == nil || agent.Role != model.RoleAgent {
		return nil
	}

	options, err := BuildAgentModelOptions()
	if err != nil {
		return &AgentModelInfo{
			Source:  ModelSourceSystem,
			Label:   "default",
			Warning: "系统模型目录读取失败",
		}
	}

	catalog, err := LoadSystemModelCatalog()
	if err != nil {
		return &AgentModelInfo{
			Source:  ModelSourceSystem,
			Label:   "default",
			Warning: "系统模型目录读取失败",
		}
	}
	defaultItem := FindDefaultSystemModel(catalog)
	defaultID := options.DefaultModelID
	modelSource := strings.TrimSpace(agent.ModelSource)
	if modelSource == "" {
		modelSource = ModelSourceSystem
	}

	if modelSource == ModelSourceCustom && strings.TrimSpace(agent.ModelConfig) != "" {
		cfg, err := DecryptCustomModelConfig(agent.ModelConfig)
		if err == nil && cfg.Model != "" && cfg.BaseURL != "" {
			label := strings.TrimSpace(cfg.Label)
			if label == "" {
				label = cfg.Model
			}
			return &AgentModelInfo{
				Source:       ModelSourceCustom,
				Label:        label,
				Model:        cfg.Model,
				BaseURL:      cfg.BaseURL,
				APIKeyMasked: MaskAPIKey(cfg.APIKey),
				IsFallback:   false,
			}
		}
		if defaultItem != nil {
			return &AgentModelInfo{
				Source:            ModelSourceCustom,
				EffectiveModelID:  defaultItem.ID,
				Label:             defaultItem.Label,
				Model:             defaultItem.Model,
				BaseURL:           defaultItem.BaseURL,
				APIKeyMasked:      MaskAPIKey(defaultItem.APIKey),
				IsFallback:        true,
				Warning:           "自定义模型无效，已自动切换为默认模型",
				ConfiguredModelID: "",
			}
		}
	}

	configuredID := strings.TrimSpace(agent.ModelID)
	if configuredID == "" {
		configuredID = defaultID
	}
	for _, item := range catalog {
		if !item.Enabled || item.ID != configuredID {
			continue
		}
		return &AgentModelInfo{
			Source:            ModelSourceSystem,
			ConfiguredModelID: configuredID,
			EffectiveModelID:  item.ID,
			Label:             item.Label,
			Model:             item.Model,
			BaseURL:           item.BaseURL,
			APIKeyMasked:      MaskAPIKey(item.APIKey),
			IsFallback:        false,
		}
	}

	if defaultItem != nil {
		info := &AgentModelInfo{
			Source:            ModelSourceSystem,
			ConfiguredModelID: configuredID,
			EffectiveModelID:  defaultItem.ID,
			Label:             defaultItem.Label,
			Model:             defaultItem.Model,
			BaseURL:           defaultItem.BaseURL,
			APIKeyMasked:      MaskAPIKey(defaultItem.APIKey),
			IsFallback:        configuredID != "" && configuredID != defaultItem.ID,
		}
		if info.IsFallback {
			info.Warning = "原系统模型已失效，已自动切换为默认模型"
		}
		return info
	}

	return &AgentModelInfo{
		Source:            ModelSourceSystem,
		ConfiguredModelID: configuredID,
		Label:             "default",
	}
}
