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

type CreateCommentRequest struct {
	Content  string `json:"content" binding:"required,min=1"`
	AnswerID uint   `json:"answer_id" binding:"required"`
	RootID   uint   `json:"root_id"`
	ParentID uint   `json:"parent_id"`
}

type UpdateCommentRequest struct {
	Content string `json:"content" binding:"required,min=1"`
}

// CreateComment 创建评论
// @Summary 创建评论
// @Description 为回答创建评论，支持根评论和回复评论
// @Tags 评论管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param request body CreateCommentRequest true "评论参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"创建成功\", \"data\": {...}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"回答不存在\"}"
// @Router /comment [post]
func CreateComment(c *gin.Context) {
	var req CreateCommentRequest
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

	var answer model.Answer
	if err := database.DB.First(&answer, req.AnswerID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "回答不存在",
		})
		return
	}

	comment := model.Comment{
		Content:  req.Content,
		AnswerID: req.AnswerID,
		UserID:   uint(userID.(float64)),
		RootID:   req.RootID,
		ParentID: req.ParentID,
	}

	if err := database.DB.Create(&comment).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "创建评论失败",
		})
		return
	}

	// 增加回答的评论数
	if err := service.IncrCommentCount(c.Request.Context(), model.TargetTypeAnswer, req.AnswerID, 1); err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "更新评论计数失败",
		})
		return
	}

	// 如果是回复评论，也增加根评论的评论数
	if req.RootID > 0 {
		if err := service.IncrCommentCount(c.Request.Context(), model.TargetTypeComment, req.RootID, 1); err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "更新根评论计数失败",
			})
			return
		}
	}

	database.DB.Preload("User").First(&comment, comment.ID)

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "创建成功",
		Data:    dto.ToCommentResponse(&comment, nil),
	})
}

// GetCommentList 获取评论列表
// @Summary 获取评论列表
// @Description 获取指定回答的评论列表，使用游标分页，包含点赞/点踩统计
// @Tags 评论管理
// @Accept json
// @Produce json
// @Param answer_id query int true "回答ID"
// @Param cursor query int false "游标（上一页最后一条记录的ID）"
// @Param limit query int false "每页数量" default(10)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"缺少回答ID\"}"
// @Router /comment/list [get]
func GetCommentList(c *gin.Context) {
	answerID := c.Query("answer_id")
	if answerID == "" {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "缺少回答ID",
		})
		return
	}

	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	if limit < 1 || limit > 100 {
		limit = 10
	}

	var comments []model.Comment
	query := database.DB.Where("answer_id = ? AND root_id = 0", answerID)

	if cursor > 0 {
		query = query.Where("id < ?", cursor)
	}

	if err := query.Order("id DESC").
		Preload("User").
		Limit(limit + 1).
		Find(&comments).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	hasMore := len(comments) > limit
	if hasMore {
		comments = comments[:limit]
	}

	var nextCursor uint
	if len(comments) > 0 {
		nextCursor = comments[len(comments)-1].ID
	}

	commentIDs := make([]uint, len(comments))
	for i, cm := range comments {
		commentIDs[i] = cm.ID
	}

	stats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeComment, commentIDs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取统计信息失败",
		})
		return
	}

	var statusMap map[uint]int
	if userID, ok := getOptionalUserID(c); ok && len(commentIDs) > 0 {
		statusMap, err = service.BatchGetUserStatus(c.Request.Context(), userID, model.TargetTypeComment, commentIDs)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取用户反应状态失败",
			})
			return
		}
	}

	list := make([]*dto.CommentResponse, len(comments))
	for i, cm := range comments {
		stat := stats[cm.ID]
		list[i] = dto.ToCommentResponse(&cm, &stat)
		if statusMap != nil {
			if status, ok := statusMap[cm.ID]; ok {
				list[i].ReactionStatus = &status
			}
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

// GetCommentReplies 获取评论回复列表
// @Summary 获取评论回复
// @Description 获取指定评论的回复列表
// @Tags 评论管理
// @Accept json
// @Produce json
// @Param root_id query int true "根评论ID"
// @Param cursor query int false "游标"
// @Param limit query int false "每页数量" default(10)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"缺少根评论ID\"}"
// @Router /comment/replies [get]
func GetCommentReplies(c *gin.Context) {
	rootID := c.Query("root_id")
	if rootID == "" {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "缺少根评论ID",
		})
		return
	}

	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	if limit < 1 || limit > 100 {
		limit = 10
	}

	var comments []model.Comment
	query := database.DB.Where("root_id = ?", rootID)

	if cursor > 0 {
		query = query.Where("id > ?", cursor)
	}

	if err := query.Order("id ASC").
		Preload("User").
		Limit(limit + 1).
		Find(&comments).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	hasMore := len(comments) > limit
	if hasMore {
		comments = comments[:limit]
	}

	var nextCursor uint
	if len(comments) > 0 {
		nextCursor = comments[len(comments)-1].ID
	}

	// Collect parent IDs and load parent users
	parentIDs := make([]uint, 0)
	for _, cm := range comments {
		if cm.ParentID > 0 && cm.ParentID != cm.RootID {
			parentIDs = append(parentIDs, cm.ParentID)
		}
	}

	// Load parent comments with users
	parentUsers := make(map[uint]*model.User)
	if len(parentIDs) > 0 {
		var parentComments []model.Comment
		if err := database.DB.Where("id IN ?", parentIDs).
			Preload("User").
			Find(&parentComments).Error; err == nil {
			for _, pc := range parentComments {
				if pc.User.ID != 0 {
					parentUsers[pc.ID] = &pc.User
				}
			}
		}
	}

	// Get stats for replies
	commentIDs := make([]uint, len(comments))
	for i, cm := range comments {
		commentIDs[i] = cm.ID
	}

	stats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeComment, commentIDs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取统计信息失败",
		})
		return
	}

	var statusMap map[uint]int
	if userID, ok := getOptionalUserID(c); ok && len(commentIDs) > 0 {
		statusMap, err = service.BatchGetUserStatus(c.Request.Context(), userID, model.TargetTypeComment, commentIDs)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取用户反应状态失败",
			})
			return
		}
	}

	list := make([]*dto.CommentResponse, len(comments))
	for i, cm := range comments {
		parentUser := parentUsers[cm.ParentID]
		stat := stats[cm.ID]
		list[i] = dto.ToCommentResponseWithParent(&cm, parentUser, &stat)
		if statusMap != nil {
			if status, ok := statusMap[cm.ID]; ok {
				list[i].ReactionStatus = &status
			}
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

// GetCommentDetail 获取评论详情
// @Summary 获取评论详情
// @Description 根据ID获取评论详细信息，包含点赞/点踩统计
// @Tags 评论管理
// @Accept json
// @Produce json
// @Param id path int true "评论ID"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {...}}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"评论不存在\"}"
// @Router /comment/{id} [get]
func GetCommentDetail(c *gin.Context) {
	id := c.Param("id")

	var comment model.Comment
	if err := database.DB.Preload("User").First(&comment, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "评论不存在",
		})
		return
	}

	stats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeComment, []uint{comment.ID})
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取统计信息失败",
		})
		return
	}

	stat := stats[comment.ID]
	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: dto.ToCommentResponse(&comment, &stat),
	})
}

// UpdateComment 更新评论
// @Summary 更新评论
// @Description 更新评论内容（仅作者本人可操作）
// @Tags 评论管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param id path int true "评论ID"
// @Param request body UpdateCommentRequest true "更新参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"更新成功\"}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"评论不存在\"}"
// @Router /comment/{id} [put]
func UpdateComment(c *gin.Context) {
	id := c.Param("id")

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var comment model.Comment
	if err := database.DB.First(&comment, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "评论不存在",
		})
		return
	}

	if comment.UserID != uint(userID.(float64)) {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	var req UpdateCommentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	if err := database.DB.Model(&comment).Update("content", req.Content).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "更新失败",
		})
		return
	}

	database.DB.Preload("User").First(&comment, id)

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "更新成功",
		Data:    dto.ToCommentResponse(&comment, nil),
	})
}

// DeleteComment 删除评论
// @Summary 删除评论
// @Description 删除评论（仅作者本人可操作）
// @Tags 评论管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param id path int true "评论ID"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"删除成功\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"评论不存在\"}"
// @Router /comment/{id} [delete]
func DeleteComment(c *gin.Context) {
	id := c.Param("id")

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var comment model.Comment
	if err := database.DB.First(&comment, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "评论不存在",
		})
		return
	}

	if comment.UserID != uint(userID.(float64)) {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	if err := database.DB.Delete(&comment).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "删除失败",
		})
		return
	}

	// 减少回答的评论数
	if err := service.IncrCommentCount(c.Request.Context(), model.TargetTypeAnswer, comment.AnswerID, -1); err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "更新评论计数失败",
		})
		return
	}

	// 如果是回复评论，也减少根评论的评论数
	if comment.RootID > 0 {
		if err := service.IncrCommentCount(c.Request.Context(), model.TargetTypeComment, comment.RootID, -1); err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "更新根评论计数失败",
			})
			return
		}
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "删除成功",
	})
}
