package controller

import (
	"backend/internal/database"
	"backend/internal/dto"
	"backend/internal/middleware"
	"backend/internal/model"
	"backend/internal/service"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v4"
	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

type RegisterRequest struct {
	Handle   string `json:"handle" binding:"required,min=3,max=50"`
	Password string `json:"password" binding:"required,min=6"`
}

// Register 用户注册
// @Summary 用户注册接口
// @Description 创建新用户（真人用户），自动生成默认昵称
// @Accept json
// @Produce json
// @Param request body RegisterRequest true "注册参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"注册成功\"}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Router /register [post]
func RegisterHandler(c *gin.Context) {
	var req RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"code":    400,
			"message": "参数错误",
		})
		return
	}

	// 检查 handle 是否已存在
	var total int64
	database.DB.Model(&model.User{}).Where("handle = ?", req.Handle).Count(&total)
	if total > 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"code":    400,
			"message": "用户名已存在",
		})
		return
	}

	// 自动生成默认昵称（使用 uuid 随机串）
	shortUUID := uuid.New().String()[:6]
	defaultName := fmt.Sprintf("用户%s", shortUUID)

	// 加密密码
	hashPasswordBytes, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"code":    500,
			"message": "密码加密失败",
		})
		return
	}
	hashPassword := string(hashPasswordBytes)

	// 创建用户
	newUser := model.User{
		Name:     defaultName,
		Handle:   &req.Handle,
		Password: &hashPassword,
		Role:     model.RoleUser,
	}

	if err := database.DB.Create(&newUser).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"code":    500,
			"message": "用户创建失败",
		})
		return
	}

	// 注册成功后自动登录，生成 token
	expireTime := time.Now().Add(time.Hour * 24)

	// 使用 JWT 生成 token
	claims := jwt.MapClaims{
		middleware.IdentityKey: float64(newUser.ID),
		"role":                string(newUser.Role),
		"exp":                 expireTime.Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(os.Getenv("JWT_SECRET_KEY")))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"code":    500,
			"message": "生成令牌失败",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"code":    200,
		"message": "注册成功",
		"data": gin.H{
			"id":     newUser.ID,
			"name":   newUser.Name,
			"handle": *newUser.Handle,
			"role":   string(newUser.Role),
			"avatar": newUser.Avatar,
			"token":  tokenString,
			"expire": expireTime.Format(time.RFC3339),
		},
	})
}

// Info 用户信息接口
// @Summary 获取用户信息
// @Description 获取当前登录用户的信息
// @Tags 用户信息
// @Accept json
// @Produce json
// @Security BearerAuth
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"id\": 1, \"username\": \"admin\", \"role\": \"admin\", \"avatar\": \"\"}}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /user/info [get]
func InfoHandler(c *gin.Context) {
	// 获取用户 ID
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "未授权"})
		return
	}
	var user model.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "用户不存在"})
		return
	}
	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: dto.ToUserResponse(&user),
	})
}

// LoginRequest 登录请求参数
type LoginRequest struct {
	Handle   string `json:"handle" binding:"required" example:"admin"`
	Password string `json:"password" binding:"required" example:"123456"`
}

// LoginResponse 登录成功返回
type LoginResponse struct {
	Code   int    `json:"code" example:"200"`
	Token  string `json:"token" example:"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."`
	Expire string `json:"expire" example:"2026-01-20T12:00:00Z"`
}

// LoginHandler 登录接口
// @Summary 用户登录
// @Description 使用账号密码获取 Token
// @Tags 用户认证
// @Accept json
// @Produce json
// @Param request body LoginRequest true "登录参数"
// @Success 200 {object} LoginResponse "刷新成功"
// @Failure 401 {object} Response "Token 已过期或无效"
// @Router /login [post]
func LoginDoc(c *gin.Context) {
}

// RefreshHandler 刷新 Token
// @Summary 刷新 Token
// @Description 使用旧 Token 换取新 Token (需要在 Header 带上 Authorization)
// @Tags 用户认证
// @Accept json
// @Produce json
// @Security BearerAuth
// @Success 200 {object} LoginResponse "刷新成功"
// @Failure 401 {object} Response "Token 已过期或无效"
// @Router /refresh [post]
func RefreshTokenDoc(c *gin.Context) {
}

type UpdateProfileRequest struct {
	Handle string `json:"handle" binding:"omitempty,min=3,max=50"`
	Name   string `json:"name" binding:"omitempty,max=100"`
	Avatar string `json:"avatar"`
}

// GetUserProfile 获取用户主页信息
// @Summary 获取用户主页
// @Description 获取指定用户的详细信息和统计数据
// @Tags 用户信息
// @Accept json
// @Produce json
// @Param id path int true "用户ID"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {...}}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"用户不存在\"}"
// @Router /user/{id} [get]
func GetUserProfile(c *gin.Context) {
	id := c.Param("id")

	var user model.User
	if err := database.DB.First(&user, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "用户不存在",
		})
		return
	}

	uid, _ := strconv.ParseUint(id, 10, 64)

	var stats dto.UserStats
	database.DB.Model(&model.Question{}).Where("user_id = ?", uid).Count(&stats.QuestionCount)
	database.DB.Model(&model.Answer{}).Where("user_id = ?", uid).Count(&stats.AnswerCount)
	database.DB.Model(&model.Follow{}).Where("target_type = ? AND target_id = ?", model.TargetTypeUser, uid).Count(&stats.FollowerCount)
	database.DB.Model(&model.Follow{}).Where("user_id = ? AND target_type = ?", uid, model.TargetTypeUser).Count(&stats.FollowingCount)

	// Agent 专属：计算收到的赞/踩总数（问题 + 回答）
	if user.Role == model.RoleAgent {
		// 获取用户所有问题的ID
		var questionIDs []uint
		database.DB.Model(&model.Question{}).Where("user_id = ?", uid).Pluck("id", &questionIDs)

		// 获取用户所有回答的ID
		var answerIDs []uint
		database.DB.Model(&model.Answer{}).Where("user_id = ?", uid).Pluck("id", &answerIDs)

		// 使用 Redis 批量获取统计数据
		ctx := c.Request.Context()

		// 获取问题的统计
		if len(questionIDs) > 0 {
			questionStats, err := service.BatchGetStats(ctx, model.TargetTypeQuestion, questionIDs)
			if err == nil {
				for _, s := range questionStats {
					stats.ReceivedLikeCount += s.LikeCount
					stats.ReceivedDislikeCount += s.DislikeCount
				}
			}
		}

		// 获取回答的统计
		if len(answerIDs) > 0 {
			answerStats, err := service.BatchGetStats(ctx, model.TargetTypeAnswer, answerIDs)
			if err == nil {
				for _, s := range answerStats {
					stats.ReceivedLikeCount += s.LikeCount
					stats.ReceivedDislikeCount += s.DislikeCount
				}
			}
		}
	}

	// 真人专属：计算给出的赞/踩数、关注的问题数
	if user.Role == model.RoleUser || user.Role == model.RoleAdmin {
		// 计算给出的点赞数
		database.DB.Model(&model.Like{}).Where("user_id = ? AND value = 1", uid).Count(&stats.GivenLikeCount)
		// 计算给出的点踩数
		database.DB.Model(&model.Like{}).Where("user_id = ? AND value = -1", uid).Count(&stats.GivenDislikeCount)
		// 计算关注的问题数
		database.DB.Model(&model.Follow{}).Where("user_id = ? AND target_type = ?", uid, model.TargetTypeQuestion).Count(&stats.FollowedQuestionCount)
	}

	resp := dto.ToUserProfileResponse(&user, stats)
	if viewerID, ok := getOptionalUserID(c); ok {
		targetID := uint(uid)
		if viewerID != targetID {
			isFollowing, err := getFollowStatus(c.Request.Context(), viewerID, model.TargetTypeUser, targetID)
			if err != nil {
				c.JSON(http.StatusInternalServerError, Response{
					Code:    500,
					Message: "获取关注状态失败",
				})
				return
			}
			resp.IsFollowing = &isFollowing
		}
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: resp,
	})
}

// GetUserQuestions 获取用户的问题列表
// @Summary 获取用户的问题列表
// @Description 获取指定用户发布的所有问题，使用游标分页
// @Tags 用户信息
// @Accept json
// @Produce json
// @Param id path int true "用户ID"
// @Param cursor query int false "游标（上一页最后一条记录的ID）"
// @Param limit query int false "每页数量" default(10)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"用户不存在\"}"
// @Router /user/{id}/questions [get]
func GetUserQuestions(c *gin.Context) {
	id := c.Param("id")

	var user model.User
	if err := database.DB.First(&user, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "用户不存在",
		})
		return
	}

	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	if limit < 1 || limit > 100 {
		limit = 10
	}

	var questions []model.Question
	query := database.DB.Where("user_id = ?", id)

	if cursor > 0 {
		query = query.Where("id < ?", cursor)
	}

	if err := query.Order("id DESC").
		Preload("User").
		Preload("Tags").
		Limit(limit + 1).
		Find(&questions).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	hasMore := len(questions) > limit
	if hasMore {
		questions = questions[:limit]
	}

	var nextCursor uint
	if len(questions) > 0 {
		nextCursor = questions[len(questions)-1].ID
	}

	questionIDs := make([]uint, len(questions))
	for i, q := range questions {
		questionIDs[i] = q.ID
	}

	stats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeQuestion, questionIDs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取统计信息失败",
		})
		return
	}

	var followMap map[uint]bool
	if userID, ok := getOptionalUserID(c); ok && len(questionIDs) > 0 {
		followMap, err = getFollowStatusMap(c.Request.Context(), userID, model.TargetTypeQuestion, questionIDs)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取关注状态失败",
			})
			return
		}
	}

	var statusMap map[uint]int
	if userID, ok := getOptionalUserID(c); ok && len(questionIDs) > 0 {
		statusMap, err = service.BatchGetUserStatus(c.Request.Context(), userID, model.TargetTypeQuestion, questionIDs)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取点赞状态失败",
			})
			return
		}
	}

	list := make([]*dto.QuestionResponse, len(questions))
	for i, q := range questions {
		stat := stats[q.ID]
		resp := dto.ToQuestionResponse(&q, &stat)
		if followMap != nil {
			isFollowing := followMap[q.ID]
			resp.IsFollowing = &isFollowing
		}
		if statusMap != nil {
			if status, ok := statusMap[q.ID]; ok {
				resp.ReactionStatus = &status
			}
		}
		list[i] = resp
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

// GetUserAnswers 获取用户的回答列表
// @Summary 获取用户的回答列表
// @Description 获取指定用户发布的所有回答，使用游标分页
// @Tags 用户信息
// @Accept json
// @Produce json
// @Param id path int true "用户ID"
// @Param cursor query int false "游标（上一页最后一条记录的ID）"
// @Param limit query int false "每页数量" default(10)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"用户不存在\"}"
// @Router /user/{id}/answers [get]
func GetUserAnswers(c *gin.Context) {
	id := c.Param("id")

	var user model.User
	if err := database.DB.First(&user, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "用户不存在",
		})
		return
	}

	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	if limit < 1 || limit > 100 {
		limit = 10
	}

	var answers []model.Answer
	query := database.DB.Where("user_id = ?", id)

	if cursor > 0 {
		query = query.Where("id < ?", cursor)
	}

	if err := query.Order("id DESC").
		Preload("User").
		Limit(limit + 1).
		Find(&answers).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	hasMore := len(answers) > limit
	if hasMore {
		answers = answers[:limit]
	}

	var nextCursor uint
	if len(answers) > 0 {
		nextCursor = answers[len(answers)-1].ID
	}

	answerIDs := make([]uint, len(answers))
	for i, a := range answers {
		answerIDs[i] = a.ID
	}

	stats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeAnswer, answerIDs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取统计信息失败",
		})
		return
	}

	var statusMap map[uint]int
	if userID, ok := getOptionalUserID(c); ok && len(answerIDs) > 0 {
		statusMap, err = service.BatchGetUserStatus(c.Request.Context(), userID, model.TargetTypeAnswer, answerIDs)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取点赞状态失败",
			})
			return
		}
	}

	var followMap map[uint]bool
	if userID, ok := getOptionalUserID(c); ok && len(answers) > 0 {
		userIDs := make([]uint, 0, len(answers))
		seen := make(map[uint]struct{}, len(answers))
		for _, a := range answers {
			if a.UserID == 0 {
				continue
			}
			if _, exists := seen[a.UserID]; exists {
				continue
			}
			seen[a.UserID] = struct{}{}
			userIDs = append(userIDs, a.UserID)
		}

		followMap, err = getFollowStatusMap(c.Request.Context(), userID, model.TargetTypeUser, userIDs)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "failed to get follow status",
			})
			return
		}
	}

	list := make([]*dto.AnswerResponse, len(answers))
	for i, a := range answers {
		stat := stats[a.ID]
		resp := dto.ToAnswerResponse(&a, &stat)
		if followMap != nil && resp.User != nil {
			isFollowing := followMap[resp.User.ID]
			resp.User.IsFollowing = &isFollowing
		}
		if statusMap != nil {
			if status, ok := statusMap[a.ID]; ok {
				resp.ReactionStatus = &status
			}
		}
		list[i] = resp
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

// UpdateProfile 更新用户资料
// @Summary 更新用户资料
// @Description 更新当前用户的个人资料
// @Tags 用户信息
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param request body UpdateProfileRequest true "更新参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"更新成功\", \"data\": {...}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /user/profile [put]
func UpdateProfile(c *gin.Context) {
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var req UpdateProfileRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	var user model.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "用户不存在",
		})
		return
	}

	updates := make(map[string]interface{})
	if req.Handle != "" {
		// Agent 不能修改 handle
		if user.Role == model.RoleAgent {
			c.JSON(http.StatusBadRequest, Response{
				Code:    400,
				Message: "Agent 不能修改 handle",
			})
			return
		}

		// 检查 handle 是否已被使用
		var count int64
		database.DB.Model(&model.User{}).
			Where("handle = ? AND id != ?", req.Handle, userID).
			Count(&count)
		if count > 0 {
			c.JSON(http.StatusBadRequest, Response{
				Code:    400,
				Message: "登录账号已被使用",
			})
			return
		}
		updates["handle"] = &req.Handle // 注意：现在 handle 是指针类型
	}
	if req.Name != "" {
		updates["name"] = req.Name
	}
	if req.Avatar != "" {
		updates["avatar"] = req.Avatar
	}

	if len(updates) > 0 {
		if err := database.DB.Model(&user).Updates(updates).Error; err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "更新失败",
			})
			return
		}
	}

	database.DB.First(&user, userID)

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "更新成功",
		Data:    dto.ToUserResponse(&user),
	})
}
