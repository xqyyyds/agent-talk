package controller

import (
	"backend/internal/service"
	"io"
	"net/http"

	"github.com/gin-gonic/gin"
)

type normalizeAvatarRequest struct {
	Avatar string `json:"avatar" binding:"required"`
}

func UploadAvatar(c *gin.Context) {
	uploadAvatarFromMultipart(c)
}

func InternalUploadAvatar(c *gin.Context) {
	uploadAvatarFromMultipart(c)
}

func IngestAvatar(c *gin.Context) {
	var req normalizeAvatarRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	avatar, err := service.NormalizeAvatarInput(req.Avatar)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "头像处理失败: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: gin.H{"avatar": avatar},
	})
}

func uploadAvatarFromMultipart(c *gin.Context) {
	fileHeader, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "缺少头像文件",
		})
		return
	}

	file, err := fileHeader.Open()
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "头像文件读取失败",
		})
		return
	}
	defer file.Close()

	payload, err := io.ReadAll(file)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "头像文件读取失败",
		})
		return
	}

	avatar, err := service.PersistAvatarFile(payload, fileHeader.Filename, fileHeader.Header.Get("Content-Type"))
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "头像处理失败: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: gin.H{"avatar": avatar},
	})
}
