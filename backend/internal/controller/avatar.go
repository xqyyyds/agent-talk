package controller

import (
	"backend/internal/service"
	"net/http"

	"github.com/gin-gonic/gin"
)

type normalizeAvatarRequest struct {
	Avatar string `json:"avatar" binding:"required"`
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
