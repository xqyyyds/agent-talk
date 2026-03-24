package controller

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestServeUploadServesExistingFile(t *testing.T) {
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

	fullPath := filepath.Join("uploads", "avatars", "2026", "03", "sample.png")
	if err := os.MkdirAll(filepath.Dir(fullPath), 0o755); err != nil {
		t.Fatalf("MkdirAll() error = %v", err)
	}
	if err := os.WriteFile(fullPath, []byte("png-bytes"), 0o644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	router := gin.New()
	router.GET("/uploads/*filepath", ServeUpload)

	req := httptest.NewRequest(http.MethodGet, "/uploads/avatars/2026/03/sample.png", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	if body := rec.Body.String(); body != "png-bytes" {
		t.Fatalf("unexpected body: %q", body)
	}
}

func TestServeUploadReturnsPlaceholderForMissingAvatar(t *testing.T) {
	t.Setenv("GIN_MODE", "test")
	gin.SetMode(gin.TestMode)

	router := gin.New()
	router.GET("/uploads/*filepath", ServeUpload)

	req := httptest.NewRequest(http.MethodGet, "/uploads/avatars/2026/03/missing.png", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	if contentType := rec.Header().Get("Content-Type"); !strings.Contains(contentType, "image/svg+xml") {
		t.Fatalf("unexpected content type: %s", contentType)
	}
	if !strings.Contains(rec.Body.String(), "<svg") {
		t.Fatalf("expected svg placeholder body")
	}
}

func TestServeUploadRejectsTraversal(t *testing.T) {
	t.Setenv("GIN_MODE", "test")
	gin.SetMode(gin.TestMode)

	router := gin.New()
	router.GET("/uploads/*filepath", ServeUpload)

	req := httptest.NewRequest(http.MethodGet, "/uploads/../../secret.txt", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
}
