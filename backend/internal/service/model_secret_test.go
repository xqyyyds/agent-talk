package service

import (
	"os"
	"testing"
)

func TestModelSecretRoundTrip(t *testing.T) {
	t.Setenv("AGENT_MODEL_SECRET", "unit-test-secret")
	cfg := CustomModelConfig{
		Label:        "My DeepSeek",
		ProviderType: openAICompatibleType,
		BaseURL:      "https://example.com/v1",
		APIKey:       "sk-test-123456",
		Model:        "deepseek-chat",
	}

	ciphertext, err := EncryptCustomModelConfig(cfg)
	if err != nil {
		t.Fatalf("EncryptCustomModelConfig() error = %v", err)
	}
	if ciphertext == "" {
		t.Fatalf("expected non-empty ciphertext")
	}

	decoded, err := DecryptCustomModelConfig(ciphertext)
	if err != nil {
		t.Fatalf("DecryptCustomModelConfig() error = %v", err)
	}
	if decoded.Model != cfg.Model || decoded.APIKey != cfg.APIKey || decoded.BaseURL != cfg.BaseURL {
		t.Fatalf("decoded config mismatch: %#v", decoded)
	}
}

func TestMaskAPIKey(t *testing.T) {
	if got := MaskAPIKey("sk-1234567890"); got != "sk-***7890" {
		t.Fatalf("unexpected mask result: %s", got)
	}
}

func TestEncryptionSecretFallbackToJWT(t *testing.T) {
	_ = os.Unsetenv("AGENT_MODEL_SECRET")
	t.Setenv("JWT_SECRET_KEY", "jwt-fallback-secret")
	if encryptionSecret() != "jwt-fallback-secret" {
		t.Fatalf("expected JWT secret fallback")
	}
}
