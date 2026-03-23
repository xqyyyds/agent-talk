package service

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
)

func encryptionSecret() string {
	if secret := strings.TrimSpace(os.Getenv("AGENT_MODEL_SECRET")); secret != "" {
		return secret
	}
	return strings.TrimSpace(os.Getenv("JWT_SECRET_KEY"))
}

func encryptionKey() ([]byte, error) {
	secret := encryptionSecret()
	if secret == "" {
		return nil, fmt.Errorf("missing AGENT_MODEL_SECRET or JWT_SECRET_KEY")
	}
	sum := sha256.Sum256([]byte(secret))
	return sum[:], nil
}

func EncryptCustomModelConfig(cfg CustomModelConfig) (string, error) {
	payload, err := json.Marshal(cfg)
	if err != nil {
		return "", err
	}
	key, err := encryptionKey()
	if err != nil {
		return "", err
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}
	ciphertext := gcm.Seal(nonce, nonce, payload, nil)
	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

func DecryptCustomModelConfig(ciphertext string) (*CustomModelConfig, error) {
	raw := strings.TrimSpace(ciphertext)
	if raw == "" {
		return nil, fmt.Errorf("empty encrypted config")
	}
	key, err := encryptionKey()
	if err != nil {
		return nil, err
	}
	data, err := base64.StdEncoding.DecodeString(raw)
	if err != nil {
		return nil, err
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	if len(data) < gcm.NonceSize() {
		return nil, fmt.Errorf("ciphertext too short")
	}
	nonce, body := data[:gcm.NonceSize()], data[gcm.NonceSize():]
	plaintext, err := gcm.Open(nil, nonce, body, nil)
	if err != nil {
		return nil, err
	}
	var cfg CustomModelConfig
	if err := json.Unmarshal(plaintext, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}
