package controller

import (
	"backend/internal/middleware"
	"backend/internal/model"
	"backend/internal/service"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

// ReactionRequest 点赞/点踩请求参数
type ReactionRequest struct {
	TargetType uint8 `json:"target_type" binding:"required,min=1,max=4"`
	TargetID   uint  `json:"target_id" binding:"required,min=1"`
	Action     int   `json:"action" binding:"oneof=0 1 2"`
}

// ExecuteReaction 执行点赞/点踩操作
// @Summary 执行点赞/点踩操作
// @Description 对问题、回答或评论进行点赞(1)、点踩(2)或取消(0)操作
// @Tags 互动管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param request body ReactionRequest true "操作参数 (target_type: 1=问题 2=回答 3=评论, action: 0=取消 1=点赞 2=点踩)"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"操作成功\"}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /reaction [post]
func ExecuteReaction(c *gin.Context) {
	var req ReactionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	if err := service.ExecuteAction(
		c.Request.Context(),
		uint(userID.(float64)),
		model.TargetType(req.TargetType),
		req.TargetID,
		req.Action,
	); err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "操作失败: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "操作成功",
	})
}

// GetReactionStatus 获取用户对某对象的点赞/点踩状态
// @Summary 获取点赞/点踩状态
// @Description 获取当前用户对指定对象的状态 (0=无 1=点赞 2=点踩)
// @Tags 互动管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param target_type query int true "对象类型 (1=问题 2=回答 3=评论)"
// @Param target_id query int true "对象ID"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"status\": 1}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /reaction/status [get]
func GetReactionStatus(c *gin.Context) {
	targetType, err := strconv.ParseUint(c.Query("target_type"), 10, 8)
	if err != nil || targetType < 1 || targetType > 4 {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: target_type 必须为 1-4",
		})
		return
	}

	targetID, err := strconv.ParseUint(c.Query("target_id"), 10, 32)
	if err != nil || targetID == 0 {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: target_id 必须为正整数",
		})
		return
	}

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	status, err := service.GetUserStatus(
		c.Request.Context(),
		uint(userID.(float64)),
		model.TargetType(targetType),
		uint(targetID),
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: gin.H{
			"status": status,
		},
	})
}
