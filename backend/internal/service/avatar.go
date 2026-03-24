package service

import (
	"backend/internal/database"
	"backend/internal/model"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	maxAvatarSizeBytes = 15 * 1024 * 1024
	avatarPublicPrefix = "/api/uploads/avatars/"
)

var avatarMimeExtensions = map[string]string{
	"image/gif":     ".gif",
	"image/jpeg":    ".jpg",
	"image/jpg":     ".jpg",
	"image/png":     ".png",
	"image/svg+xml": ".svg",
	"image/webp":    ".webp",
}

var avatarFileExtensions = map[string]string{
	".gif":  ".gif",
	".jpeg": ".jpg",
	".jpg":  ".jpg",
	".png":  ".png",
	".svg":  ".svg",
	".webp": ".webp",
}

func NormalizeAvatarInput(raw string) (string, error) {
	return normalizeAvatarValue(strings.TrimSpace(raw))
}

func PersistAvatarFile(payload []byte, originalName string, contentType string) (string, error) {
	if len(payload) == 0 {
		return "", errors.New("empty avatar payload")
	}
	if len(payload) > maxAvatarSizeBytes {
		return "", fmt.Errorf("avatar payload exceeds %d bytes", maxAvatarSizeBytes)
	}

	ext, err := detectAvatarExtension(payload, originalName, contentType)
	if err != nil {
		return "", err
	}

	return persistAvatarBytes(payload, ext)
}

func NormalizeUserAvatar(user *model.User) string {
	if user == nil {
		return ""
	}

	normalized, err := normalizeAvatarValue(strings.TrimSpace(user.Avatar))
	if err != nil {
		return ""
	}
	if normalized != user.Avatar {
		user.Avatar = normalized
		if user.ID > 0 {
			_ = database.DB.Model(&model.User{}).Where("id = ?", user.ID).Update("avatar", normalized).Error
		}
	}
	return normalized
}

func normalizeAvatarValue(raw string) (string, error) {
	if raw == "" {
		return "", nil
	}
	if !strings.HasPrefix(raw, "data:") {
		return canonicalizeAvatarPath(raw), nil
	}
	return persistAvatarDataURL(raw)
}

func canonicalizeAvatarPath(raw string) string {
	switch {
	case strings.HasPrefix(raw, avatarPublicPrefix):
		return raw
	case strings.HasPrefix(raw, "/uploads/"):
		return "/api" + raw
	case strings.HasPrefix(raw, "uploads/"):
		return "/api/" + raw
	default:
		return raw
	}
}

func persistAvatarDataURL(raw string) (string, error) {
	mimeType, encoded, err := splitDataURL(raw)
	if err != nil {
		return "", err
	}

	ext, ok := avatarMimeExtensions[mimeType]
	if !ok {
		return "", fmt.Errorf("unsupported avatar mime type: %s", mimeType)
	}

	payload, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return "", fmt.Errorf("decode avatar data: %w", err)
	}
	return persistAvatarBytes(payload, ext)
}

func splitDataURL(raw string) (mimeType string, encoded string, err error) {
	comma := strings.Index(raw, ",")
	if comma <= 0 {
		return "", "", errors.New("invalid data url")
	}

	header := raw[:comma]
	encoded = raw[comma+1:]
	if !strings.HasPrefix(header, "data:") || !strings.HasSuffix(header, ";base64") {
		return "", "", errors.New("avatar must be base64 data url")
	}

	mimeType = strings.TrimSuffix(strings.TrimPrefix(header, "data:"), ";base64")
	if mimeType == "" {
		return "", "", errors.New("missing avatar mime type")
	}
	return mimeType, encoded, nil
}

func randomFilename(ext string) (string, error) {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return "", fmt.Errorf("generate avatar filename: %w", err)
	}
	return fmt.Sprintf("%x%s", buf, ext), nil
}

func persistAvatarBytes(payload []byte, ext string) (string, error) {
	if len(payload) == 0 {
		return "", errors.New("empty avatar payload")
	}
	if len(payload) > maxAvatarSizeBytes {
		return "", fmt.Errorf("avatar payload exceeds %d bytes", maxAvatarSizeBytes)
	}

	now := time.Now()
	relativeDir := filepath.Join("uploads", "avatars", now.Format("2006"), now.Format("01"))
	if err := os.MkdirAll(relativeDir, 0o755); err != nil {
		return "", fmt.Errorf("create avatar dir: %w", err)
	}

	filename, err := randomFilename(ext)
	if err != nil {
		return "", err
	}
	relativePath := filepath.Join(relativeDir, filename)
	if err := os.WriteFile(relativePath, payload, 0o644); err != nil {
		return "", fmt.Errorf("write avatar file: %w", err)
	}

	return fmt.Sprintf(
		"%s%s/%s/%s",
		avatarPublicPrefix,
		now.Format("2006"),
		now.Format("01"),
		filename,
	), nil
}

func detectAvatarExtension(payload []byte, originalName string, contentType string) (string, error) {
	normalizedType := normalizeMimeType(contentType)
	if ext, ok := avatarMimeExtensions[normalizedType]; ok {
		return ext, nil
	}

	detectedType := normalizeMimeType(http.DetectContentType(payload))
	if ext, ok := avatarMimeExtensions[detectedType]; ok {
		return ext, nil
	}

	ext := strings.ToLower(filepath.Ext(originalName))
	if normalizedExt, ok := avatarFileExtensions[ext]; ok {
		return normalizedExt, nil
	}

	return "", fmt.Errorf("unsupported avatar mime type: %s", normalizedType)
}

func normalizeMimeType(raw string) string {
	base := strings.TrimSpace(strings.ToLower(raw))
	if idx := strings.Index(base, ";"); idx >= 0 {
		base = strings.TrimSpace(base[:idx])
	}
	return base
}
