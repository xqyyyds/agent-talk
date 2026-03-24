package controller

import (
	"bytes"
	"encoding/json"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestUploadAvatarHandlesMultipartImage(t *testing.T) {
	t.Setenv("GIN_MODE", "test")
	gin.SetMode(gin.TestMode)

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

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile("file", "avatar.png")
	if err != nil {
		t.Fatalf("CreateFormFile() error = %v", err)
	}
	if _, err := part.Write([]byte{0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n', 0, 0, 0, 0}); err != nil {
		t.Fatalf("Write() error = %v", err)
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}

	router := gin.New()
	router.POST("/upload/avatar", uploadAvatarFromMultipart)

	req := httptest.NewRequest(http.MethodPost, "/upload/avatar", body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d body=%s", rec.Code, rec.Body.String())
	}

	var payload Response
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("Unmarshal() error = %v", err)
	}

	data, ok := payload.Data.(map[string]any)
	if !ok {
		t.Fatalf("expected map payload, got %#v", payload.Data)
	}

	avatar, _ := data["avatar"].(string)
	if !strings.HasPrefix(avatar, "/api/uploads/avatars/") {
		t.Fatalf("unexpected avatar path: %s", avatar)
	}

	diskPath := filepath.FromSlash(strings.TrimPrefix(avatar, "/api/"))
	if _, err := os.Stat(diskPath); err != nil {
		t.Fatalf("expected uploaded avatar file to exist, got %v", err)
	}
}

func TestUploadAvatarRejectsMissingFile(t *testing.T) {
	t.Setenv("GIN_MODE", "test")
	gin.SetMode(gin.TestMode)

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	if err := writer.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}

	router := gin.New()
	router.POST("/upload/avatar", uploadAvatarFromMultipart)

	req := httptest.NewRequest(http.MethodPost, "/upload/avatar", body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d body=%s", rec.Code, rec.Body.String())
	}
}
