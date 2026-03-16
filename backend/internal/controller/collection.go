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

type CreateCollectionRequest struct {
	Name string `json:"name" binding:"required,min=1,max=50"`
}

type AddToCollectionRequest struct {
	CollectionID uint `json:"collection_id" binding:"required"`
	AnswerID     uint `json:"answer_id" binding:"required"`
}

// CreateCollection 创建收藏夹
// @Summary 创建收藏夹
// @Description 创建一个新的收藏夹
// @Tags 收藏管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param request body CreateCollectionRequest true "收藏夹名称"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"创建成功\", \"data\": {...}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /collection [post]
func CreateCollection(c *gin.Context) {
	var req CreateCollectionRequest
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

	collection := model.Collection{
		UserID: uint(userID.(float64)),
		Name:   req.Name,
	}

	if err := database.DB.Create(&collection).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "创建收藏夹失败",
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "创建成功",
		Data:    dto.ToCollectionResponse(&collection),
	})
}

// GetCollectionList 获取收藏夹列表
// @Summary 获取收藏夹列表
// @Description 获取当前用户的所有收藏夹
// @Tags 收藏管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Success 200 {object} Response "{\"code\": 200, \"data\": [...]}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /collection/list [get]
func GetCollectionList(c *gin.Context) {
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var collections []model.Collection
	if err := database.DB.Where("user_id = ?", userID).
		Order("created_at DESC").
		Find(&collections).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	list := make([]*dto.CollectionResponse, len(collections))
	for i, col := range collections {
		list[i] = dto.ToCollectionResponse(&col)
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: list,
	})
}

// AddToCollection 添加答案到收藏夹
// @Summary 添加答案到收藏夹
// @Description 将答案添加到指定收藏夹
// @Tags 收藏管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param request body AddToCollectionRequest true "收藏参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"收藏成功\"}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"收藏夹或答案不存在\"}"
// @Failure 409 {object} Response "{\"code\": 409, \"message\": \"已经收藏过了\"}"
// @Router /collection/item [post]
func AddToCollection(c *gin.Context) {
	var req AddToCollectionRequest
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

	// 验证收藏夹是否存在且属于当前用户
	var collection model.Collection
	if err := database.DB.First(&collection, req.CollectionID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "收藏夹不存在",
		})
		return
	}

	if collection.UserID != uint(userID.(float64)) {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	// 验证答案是否存在
	var answer model.Answer
	if err := database.DB.First(&answer, req.AnswerID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "答案不存在",
		})
		return
	}

	// 检查是否已经收藏
	var count int64
	database.DB.Model(&model.CollectionItem{}).
		Where("collection_id = ? AND answer_id = ?", req.CollectionID, req.AnswerID).
		Count(&count)

	if count > 0 {
		c.JSON(http.StatusConflict, Response{
			Code:    409,
			Message: "已经收藏过了",
		})
		return
	}

	// 创建收藏项
	item := model.CollectionItem{
		CollectionID: req.CollectionID,
		AnswerID:     req.AnswerID,
	}

	if err := database.DB.Create(&item).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "收藏失败",
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "收藏成功",
	})
}

// RemoveFromCollection 从收藏夹移除答案
// @Summary 从收藏夹移除答案
// @Description 从指定收藏夹中移除答案
// @Tags 收藏管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param collection_id query int true "收藏夹ID"
// @Param answer_id query int true "答案ID"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"移除成功\"}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"收藏夹不存在\"}"
// @Router /collection/item [delete]
func RemoveFromCollection(c *gin.Context) {
	collectionID := c.Query("collection_id")
	answerID := c.Query("answer_id")

	if collectionID == "" || answerID == "" {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误",
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

	// 验证收藏夹是否存在且属于当前用户
	var collection model.Collection
	if err := database.DB.First(&collection, collectionID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "收藏夹不存在",
		})
		return
	}

	if collection.UserID != uint(userID.(float64)) {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	// 删除收藏项
	if err := database.DB.Where("collection_id = ? AND answer_id = ?", collectionID, answerID).
		Delete(&model.CollectionItem{}).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "移除失败",
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "移除成功",
	})
}

// GetCollectionItems 获取收藏夹中的答案列表
// @Summary 获取收藏夹中的答案列表
// @Description 获取指定收藏夹中的所有答案，使用游标分页，包含统计信息
// @Tags 收藏管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param collection_id query int true "收藏夹ID"
// @Param cursor query int false "游标（上一页最后一条记录的ID）"
// @Param limit query int false "每页数量" default(10)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"收藏夹不存在\"}"
// @Router /collection/items [get]
func GetCollectionItems(c *gin.Context) {
	collectionID := c.Query("collection_id")
	if collectionID == "" {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误",
		})
		return
	}

	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	if limit < 1 || limit > 100 {
		limit = 10
	}

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	// 验证收藏夹是否存在且属于当前用户
	var collection model.Collection
	if err := database.DB.First(&collection, collectionID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "收藏夹不存在",
		})
		return
	}

	if collection.UserID != uint(userID.(float64)) {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	// 查询收藏项
	var items []model.CollectionItem
	query := database.DB.Where("collection_id = ?", collectionID)

	if cursor > 0 {
		query = query.Where("id < ?", cursor)
	}

	if err := query.Order("id DESC").
		Limit(limit + 1).
		Find(&items).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	hasMore := len(items) > limit
	if hasMore {
		items = items[:limit]
	}

	var nextCursor uint
	if len(items) > 0 {
		nextCursor = items[len(items)-1].ID
	}

	// 获取答案详情
	answerIDs := make([]uint, len(items))
	for i, item := range items {
		answerIDs[i] = item.AnswerID
	}

	var answers []model.Answer
	if err := database.DB.Where("id IN ?", answerIDs).
		Preload("User").
		Preload("Question").
		Preload("Question.User").
		Preload("Question.Tags").
		Find(&answers).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询答案失败",
		})
		return
	}

	// 获取统计信息
	answerStats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeAnswer, answerIDs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取统计信息失败",
		})
		return
	}

	// 获取问题ID列表用于查询问题统计
	questionIDs := make([]uint, 0, len(answers))
	for _, answer := range answers {
		if answer.Question.ID != 0 {
			questionIDs = append(questionIDs, answer.QuestionID)
		}
	}

	// 获取问题统计信息
	questionStats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeQuestion, questionIDs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取问题统计信息失败",
		})
		return
	}

	// 构建返回结果 - 使用 AnswerWithQuestionResponse 包含问题信息
	list := make([]*dto.AnswerWithQuestionResponse, len(answers))
	for i, answer := range answers {
		aStat := answerStats[answer.ID]
		var qStat *service.ObjectStats
		if answer.Question.ID != 0 {
			stat := questionStats[answer.Question.ID]
			qStat = &stat
		}
		list[i] = dto.ToAnswerWithQuestionResponse(&answer, &aStat, qStat)
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

// DeleteCollection 删除收藏夹
// @Summary 删除收藏夹
// @Description 删除指定收藏夹（仅拥有者可操作）
// @Tags 收藏管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param id path int true "收藏夹ID"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"删除成功\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"收藏夹不存在\"}"
// @Router /collection/{id} [delete]
func DeleteCollection(c *gin.Context) {
	id := c.Param("id")

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var collection model.Collection
	if err := database.DB.First(&collection, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "收藏夹不存在",
		})
		return
	}

	if collection.UserID != uint(userID.(float64)) {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	// 删除收藏夹及其所有收藏项
	tx := database.DB.Begin()

	// 删除所有收藏项
	if err := tx.Where("collection_id = ?", id).Delete(&model.CollectionItem{}).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "删除失败",
		})
		return
	}

	// 删除收藏夹
	if err := tx.Delete(&collection).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "删除失败",
		})
		return
	}

	tx.Commit()

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "删除成功",
	})
}
