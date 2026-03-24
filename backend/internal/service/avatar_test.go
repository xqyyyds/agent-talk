package service

import (
	"encoding/base64"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNormalizeAvatarInputConvertsDataURLToPublicPath(t *testing.T) {
	tmpDir := t.TempDir()
	originalDir, err := os.Getwd()
	if err != nil {
		t.Fatalf("Getwd() error = %v", err)
	}
	if err := os.Chdir(tmpDir); err != nil {
		t.Fatalf("Chdir() error = %v", err)
	}
	defer func() {
		_ = os.Chdir(originalDir)
	}()

	payload := base64.StdEncoding.EncodeToString([]byte("png-bytes"))
	avatar, err := NormalizeAvatarInput("data:image/png;base64," + payload)
	if err != nil {
		t.Fatalf("NormalizeAvatarInput() error = %v", err)
	}
	if !strings.HasPrefix(avatar, avatarPublicPrefix) {
		t.Fatalf("expected avatar public path, got %s", avatar)
	}

	diskPath := filepath.FromSlash(strings.TrimPrefix(avatar, "/api/"))
	if _, err := os.Stat(diskPath); err != nil {
		t.Fatalf("expected avatar file to exist, got %v", err)
	}
}

func TestNormalizeAvatarInputCanonicalizesUploadsPath(t *testing.T) {
	got, err := NormalizeAvatarInput("/uploads/avatars/a.png")
	if err != nil {
		t.Fatalf("NormalizeAvatarInput() error = %v", err)
	}
	if got != "/api/uploads/avatars/a.png" {
		t.Fatalf("unexpected canonical path: %s", got)
	}
}

func TestPersistAvatarFileStoresBytesAsPublicPath(t *testing.T) {
	tmpDir := t.TempDir()
	originalDir, err := os.Getwd()
	if err != nil {
		t.Fatalf("Getwd() error = %v", err)
	}
	if err := os.Chdir(tmpDir); err != nil {
		t.Fatalf("Chdir() error = %v", err)
	}
	defer func() {
		_ = os.Chdir(originalDir)
	}()

	payload := []byte{0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n', 0, 0, 0, 0}
	avatar, err := PersistAvatarFile(payload, "avatar.png", "image/png")
	if err != nil {
		t.Fatalf("PersistAvatarFile() error = %v", err)
	}
	if !strings.HasPrefix(avatar, avatarPublicPrefix) {
		t.Fatalf("expected avatar public path, got %s", avatar)
	}

	diskPath := filepath.FromSlash(strings.TrimPrefix(avatar, "/api/"))
	if _, err := os.Stat(diskPath); err != nil {
		t.Fatalf("expected avatar file to exist, got %v", err)
	}
}
