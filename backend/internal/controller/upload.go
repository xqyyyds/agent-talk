package controller

import (
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
)

const avatarPlaceholderSVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="32" fill="#e5e7eb"/><circle cx="32" cy="24" r="12" fill="#9ca3af"/><path d="M14 54c3-10 11-16 18-16s15 6 18 16" fill="#9ca3af"/></svg>`

func ServeUpload(c *gin.Context) {
	requestPath := strings.TrimPrefix(c.Param("filepath"), "/")
	if requestPath == "" {
		c.Status(http.StatusNotFound)
		return
	}

	cleanPath := filepath.Clean(filepath.FromSlash(requestPath))
	if cleanPath == "." || cleanPath == "" || strings.HasPrefix(cleanPath, "..") {
		c.Status(http.StatusBadRequest)
		return
	}

	fullPath := filepath.Join("uploads", cleanPath)
	if info, err := os.Stat(fullPath); err == nil && !info.IsDir() {
		c.File(fullPath)
		return
	}

	normalized := filepath.ToSlash(cleanPath)
	if strings.HasPrefix(normalized, "avatars/") {
		c.Data(http.StatusOK, "image/svg+xml; charset=utf-8", []byte(avatarPlaceholderSVG))
		return
	}

	c.Status(http.StatusNotFound)
}
