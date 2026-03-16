package controller

import (
	"backend/internal/database"
	"backend/internal/dto"
	"backend/internal/middleware"
	"backend/internal/model"
	"backend/internal/service"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

// CreateQuestionRequest 创建问题请求参数
type CreateQuestionRequest struct {
	Title   string `json:"title" binding:"required,min=5,max=255"`
	Content string `json:"content" binding:"required"`
	Type    string `json:"type" binding:"omitempty,oneof=qa debate"`
	TagIDs  []uint `json:"tag_ids"`
}

// UpdateQuestionRequest 更新问题请求参数
type UpdateQuestionRequest struct {
	Title   string `json:"title" binding:"omitempty,min=5,max=255"`
	Content string `json:"content"`
	TagIDs  []uint `json:"tag_ids"`
}

// CreateQuestion 创建问题
// @Summary 创建问题
// @Description 创建一个新问题
// @Tags 问题管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param request body CreateQuestionRequest true "问题参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"创建成功\", \"data\": {...}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /question [post]
func CreateQuestion(c *gin.Context) {
	var req CreateQuestionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	// 获取用户 ID
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	// 创建问题
	question := model.Question{
		Title:   req.Title,
		Content: req.Content,
		Type:    "qa",
		UserID:  uint(userID.(float64)),
	}
	if req.Type != "" {
		question.Type = req.Type
	}

	// 如果有标签，需要先查询标签
	if len(req.TagIDs) > 0 {
		var tags []model.Tag
		if err := database.DB.Where("id IN ?", req.TagIDs).Find(&tags).Error; err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "查询标签失败",
			})
			return
		}
		question.Tags = tags
	}

	if err := database.DB.Create(&question).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "创建问题失败",
		})
		return
	}

	// 预加载用户和标签信息
	database.DB.Preload("User").Preload("Tags").First(&question, question.ID)

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "创建成功",
		Data:    dto.ToQuestionResponse(&question, nil),
	})

	publishStreamEvent("questions", "question_created", gin.H{
		"question_id": question.ID,
		"type":        question.Type,
		"user_id":     question.UserID,
		"title":       question.Title,
	})
}

// GetQuestionList 获取问题列表
// @Summary 获取问题列表
// @Description 获取问题列表，使用游标分页，包含点赞/点踩/评论统计
// @Tags 问题管理
// @Accept json
// @Produce json
// @Param cursor query int false "游标（上一页最后一条记录的ID）"
// @Param limit query int false "每页数量" default(10)
// @Param tag_id query int false "标签ID筛选"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Router /question/list [get]
func GetQuestionList(c *gin.Context) {
	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))
	tagID := c.Query("tag_id")
	questionType := c.DefaultQuery("type", "qa")

	if limit < 1 || limit > 100 {
		limit = 10
	}

	var questions []model.Question
	query := database.DB.Model(&model.Question{})

	if tagID != "" {
		query = query.Joins("JOIN question_tags ON questions.id = question_tags.question_id").
			Where("question_tags.tag_id = ?", tagID)
	}

	if questionType == "qa" {
		query = query.Where("questions.type = ? OR questions.type = ''", "qa")
	} else if questionType == "debate" {
		query = query.Where("questions.type = ?", "debate")
	}

	if cursor > 0 {
		query = query.Where("questions.id < ?", cursor)
	}
	query = query.Order("questions.id DESC")

	if err := query.Preload("User").Preload("Tags").
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

// GetQuestionDetail 获取问题详情
// @Summary 获取问题详情
// @Description 根据ID获取问题详细信息，包含点赞/点踩/评论统计
// @Tags 问题管理
// @Accept json
// @Produce json
// @Param id path int true "问题ID"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {...}}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"问题不存在\"}"
// @Router /question/{id} [get]
func GetQuestionDetail(c *gin.Context) {
	id := c.Param("id")

	var question model.Question
	if err := database.DB.Preload("User").Preload("Tags").First(&question, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "问题不存在",
		})
		return
	}

	stats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeQuestion, []uint{question.ID})
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取统计信息失败",
		})
		return
	}

	stat := stats[question.ID]
	resp := dto.ToQuestionResponse(&question, &stat)
	if userID, ok := getOptionalUserID(c); ok {
		status, err := service.GetUserStatus(c.Request.Context(), userID, model.TargetTypeQuestion, question.ID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取点赞状态失败",
			})
			return
		}
		resp.ReactionStatus = &status
	}
	if userID, ok := getOptionalUserID(c); ok {
		isFollowing, err := getFollowStatus(c.Request.Context(), userID, model.TargetTypeQuestion, question.ID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取关注状态失败",
			})
			return
		}
		resp.IsFollowing = &isFollowing
	}
	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: resp,
	})
}

// UpdateQuestion 更新问题
// @Summary 更新问题
// @Description 更新问题信息（仅作者本人可操作）
// @Tags 问题管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param id path int true "问题ID"
// @Param request body UpdateQuestionRequest true "更新参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"更新成功\"}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"问题不存在\"}"
// @Router /question/{id} [put]
func UpdateQuestion(c *gin.Context) {
	id := c.Param("id")

	// 获取用户 ID
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var question model.Question
	if err := database.DB.First(&question, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "问题不存在",
		})
		return
	}

	// 检查权限：作者本人或Admin可以修改
	userRole, _ := c.Get("role")
	if question.UserID != uint(userID.(float64)) && userRole.(string) != "admin" {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	var req UpdateQuestionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	// 更新字段
	updates := make(map[string]interface{})
	if req.Title != "" {
		updates["title"] = req.Title
	}
	if req.Content != "" {
		updates["content"] = req.Content
	}

	if len(updates) > 0 {
		if err := database.DB.Model(&question).Updates(updates).Error; err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "更新失败",
			})
			return
		}
	}

	// 更新标签
	if req.TagIDs != nil {
		var tags []model.Tag
		if err := database.DB.Where("id IN ?", req.TagIDs).Find(&tags).Error; err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "查询标签失败",
			})
			return
		}
		database.DB.Model(&question).Association("Tags").Replace(tags)
	}

	// 重新加载问题
	database.DB.Preload("User").Preload("Tags").First(&question, id)

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "更新成功",
		Data:    dto.ToQuestionResponse(&question, nil),
	})

	publishStreamEvent("questions", "question_updated", gin.H{
		"question_id": question.ID,
		"type":        question.Type,
		"user_id":     question.UserID,
		"title":       question.Title,
	})
}

// DeleteQuestion 删除问题
// @Summary 删除问题
// @Description 删除问题（仅作者本人可操作）
// @Tags 问题管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param id path int true "问题ID"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"删除成功\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"问题不存在\"}"
// @Router /question/{id} [delete]
func DeleteQuestion(c *gin.Context) {
	id := c.Param("id")

	// 获取用户 ID
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var question model.Question
	if err := database.DB.First(&question, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "问题不存在",
		})
		return
	}

	// 检查权限：作者本人或Admin可以删除
	userRole, _ := c.Get("role")
	if question.UserID != uint(userID.(float64)) && userRole.(string) != "admin" {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	// 删除问题（软删除）
	if err := database.DB.Delete(&question).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "删除失败",
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "删除成功",
	})
}
