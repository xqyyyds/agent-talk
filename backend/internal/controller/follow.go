package controller

import (
	"backend/internal/database"
	"backend/internal/dto"
	"backend/internal/middleware"
	"backend/internal/model"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

// FollowRequest 关注/取消关注请求参数
type FollowRequest struct {
	TargetType uint8 `json:"target_type" binding:"required,oneof=1 4"` // 1=问题, 4=用户
	TargetID   uint  `json:"target_id" binding:"required"`
	Action     bool  `json:"action"` // true=关注, false=取消关注
}

// ExecuteFollow 关注/取消关注
// @Summary 关注/取消关注
// @Description 关注或取消关注问题/用户
// @Tags 关注管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param request body FollowRequest true "关注参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"操作成功\"}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /follow [post]
func ExecuteFollow(c *gin.Context) {
	var req FollowRequest
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

	uid := uint(userID.(float64))

	// 不能关注自己
	if req.TargetType == model.TargetTypeUser && req.TargetID == uid {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "不能关注自己",
		})
		return
	}

	// 验证目标是否存在
	if err := validateTarget(req.TargetType, req.TargetID); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: err.Error(),
		})
		return
	}

	if req.Action {
		// 检查是否已经关注
		var count int64
		database.DB.Model(&model.Follow{}).
			Where("user_id = ? AND target_type = ? AND target_id = ?",
				uid, req.TargetType, req.TargetID).
			Count(&count)

		if count > 0 {
			// 已经关注过了，返回成功（幂等操作）
			c.JSON(http.StatusOK, Response{
				Code:    200,
				Message: "已经关注过了",
			})
			return
		}

		// 关注
		follow := model.Follow{
			UserID:     uid,
			TargetType: req.TargetType,
			TargetID:   req.TargetID,
		}
		if err := database.DB.Create(&follow).Error; err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "关注失败",
			})
			return
		}
		c.JSON(http.StatusOK, Response{
			Code:    200,
			Message: "关注成功",
		})
	} else {
		// 取消关注
		if err := database.DB.Where("user_id = ? AND target_type = ? AND target_id = ?",
			uid, req.TargetType, req.TargetID).Delete(&model.Follow{}).Error; err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "取消关注失败",
			})
			return
		}
		c.JSON(http.StatusOK, Response{
			Code:    200,
			Message: "取消关注成功",
		})
	}
}

// GetFollowingList 获取关注列表
// @Summary 获取关注列表
// @Description 获取用户关注的用户/问题列表
// @Tags 关注管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param target_type query int false "目标类型(1=问题,4=用户)" default(4)
// @Param cursor query int false "游标"
// @Param limit query int false "每页数量" default(20)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Router /follow/following [get]
func GetFollowingList(c *gin.Context) {
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	targetType, _ := strconv.Atoi(c.DefaultQuery("target_type", "4"))
	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	if limit < 1 || limit > 100 {
		limit = 20
	}

	var follows []model.Follow
	query := database.DB.Where("user_id = ? AND target_type = ?", uint(userID.(float64)), targetType)

	if cursor > 0 {
		query = query.Where("id < ?", cursor)
	}

	if err := query.Order("id DESC").Limit(limit + 1).Find(&follows).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	hasMore := len(follows) > limit
	if hasMore {
		follows = follows[:limit]
	}

	var nextCursor uint
	if len(follows) > 0 {
		nextCursor = follows[len(follows)-1].ID
	}

	// 预加载目标数据
	list := loadFollowTargets(follows, uint8(targetType))

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: dto.PaginatedResponse{
			List:       list,
			NextCursor: nextCursor,
			HasMore:    hasMore,
		},
	})
}

// GetFollowerList 获取粉丝列表
// @Summary 获取粉丝列表
// @Description 获取关注当前用户的粉丝列表
// @Tags 关注管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param cursor query int false "游标"
// @Param limit query int false "每页数量" default(20)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Router /follow/followers [get]
func GetFollowerList(c *gin.Context) {
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	if limit < 1 || limit > 100 {
		limit = 20
	}

	var follows []model.Follow
	query := database.DB.Where("target_type = ? AND target_id = ?",
		model.TargetTypeUser, uint(userID.(float64)))

	if cursor > 0 {
		query = query.Where("id < ?", cursor)
	}

	if err := query.Order("id DESC").Limit(limit + 1).Find(&follows).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	hasMore := len(follows) > limit
	if hasMore {
		follows = follows[:limit]
	}

	var nextCursor uint
	if len(follows) > 0 {
		nextCursor = follows[len(follows)-1].ID
	}

	// 加载用户信息
	userIDs := make([]uint, len(follows))
	for i, f := range follows {
		userIDs[i] = f.UserID
	}

	var users []model.User
	database.DB.Where("id IN ?", userIDs).Find(&users)

	userMap := make(map[uint]model.User)
	for _, u := range users {
		userMap[u.ID] = u
	}

	list := make([]map[string]interface{}, len(follows))
	for i, f := range follows {
		u := userMap[f.UserID]
		list[i] = map[string]interface{}{
			"follow":   dto.ToFollowResponse(&f),
			"follower": dto.ToUserResponse(&u),
		}
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: dto.PaginatedResponse{
			List:       list,
			NextCursor: nextCursor,
			HasMore:    hasMore,
		},
	})
}

// GetFollowStatus 检查关注状态
// @Summary 检查关注状态
// @Description 检查是否关注了指定目标
// @Tags 关注管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param target_type query int true "目标类型(1=问题,4=用户)"
// @Param target_id query int true "目标ID"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"is_following\": true}}"
// @Router /follow/status [get]
func GetFollowStatus(c *gin.Context) {
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	targetType := c.Query("target_type")
	targetID := c.Query("target_id")

	if targetType == "" || targetID == "" {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "缺少参数",
		})
		return
	}

	var count int64
	database.DB.Model(&model.Follow{}).Where(
		"user_id = ? AND target_type = ? AND target_id = ?",
		uint(userID.(float64)), targetType, targetID,
	).Count(&count)

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: gin.H{
			"is_following": count > 0,
		},
	})
}

// BatchGetFollowStatus 批量检查关注状态
// @Summary 批量检查关注状态
// @Description 批量检查是否关注了指定目标列表
// @Tags 关注管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param target_type query int true "目标类型(1=问题,4=用户)"
// @Param target_ids query string true "目标ID列表，逗号分隔"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"1\": true, \"2\": false}}"
// @Router /follow/batch-status [get]
func BatchGetFollowStatus(c *gin.Context) {
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	targetType := c.Query("target_type")
	targetIDsStr := c.Query("target_ids")

	if targetType == "" || targetIDsStr == "" {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "缺少参数",
		})
		return
	}

	var follows []model.Follow
	if err := database.DB.Where(
		"user_id = ? AND target_type = ? AND target_id IN (?)",
		uint(userID.(float64)), targetType, targetIDsStr,
	).Find(&follows).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	result := make(map[uint]bool)
	for _, f := range follows {
		result[f.TargetID] = true
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: result,
	})
}

// validateTarget 验证目标是否存在
func validateTarget(targetType uint8, targetID uint) error {
	switch targetType {
	case model.TargetTypeQuestion:
		var count int64
		database.DB.Model(&model.Question{}).Where("id = ?", targetID).Count(&count)
		if count == 0 {
			return gin.Error{Err: nil, Type: gin.ErrorTypePublic, Meta: "问题不存在"}
		}
	case model.TargetTypeUser:
		var count int64
		database.DB.Model(&model.User{}).Where("id = ?", targetID).Count(&count)
		if count == 0 {
			return gin.Error{Err: nil, Type: gin.ErrorTypePublic, Meta: "用户不存在"}
		}
	default:
		return gin.Error{Err: nil, Type: gin.ErrorTypePublic, Meta: "不支持的目标类型"}
	}
	return nil
}

// loadFollowTargets 加载关注目标的详细信息
func loadFollowTargets(follows []model.Follow, targetType uint8) []map[string]interface{} {
	if len(follows) == 0 {
		return []map[string]interface{}{}
	}

	targetIDs := make([]uint, len(follows))
	for i, f := range follows {
		targetIDs[i] = f.TargetID
	}

	list := make([]map[string]interface{}, len(follows))

	switch targetType {
	case model.TargetTypeQuestion:
		var questions []model.Question
		database.DB.Preload("User").Preload("Tags").Where("id IN ?", targetIDs).Find(&questions)

		questionMap := make(map[uint]model.Question)
		for _, q := range questions {
			questionMap[q.ID] = q
		}

		for i, f := range follows {
			q := questionMap[f.TargetID]
			list[i] = map[string]interface{}{
				"follow":   dto.ToFollowResponse(&f),
				"question": dto.ToQuestionResponse(&q, nil),
			}
		}

	case model.TargetTypeUser:
		var users []model.User
		database.DB.Where("id IN ?", targetIDs).Find(&users)

		userMap := make(map[uint]model.User)
		for _, u := range users {
			userMap[u.ID] = u
		}

		for i, f := range follows {
			u := userMap[f.TargetID]
			list[i] = map[string]interface{}{
				"follow": dto.ToFollowResponse(&f),
				"user":   dto.ToUserResponse(&u),
			}
		}
	}

	return list
}
