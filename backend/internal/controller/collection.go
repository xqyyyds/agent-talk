package controller

import (
	"backend/internal/database"
	"backend/internal/dto"
	"backend/internal/middleware"
	"backend/internal/model"
	"backend/internal/service"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type CreateCollectionRequest struct {
	Name string `json:"name" binding:"required,min=1,max=50"`
}

type AddToCollectionRequest struct {
	CollectionID uint `json:"collection_id" binding:"required"`
	AnswerID     uint `json:"answer_id" binding:"required"`
}

type AnswerCollectionStatusResponse struct {
	AnswerID      uint   `json:"answer_id"`
	CollectionIDs []uint `json:"collection_ids"`
	IsCollected   bool   `json:"is_collected"`
}

type AnswerCollectionBatchStatusResponse struct {
	Items []AnswerCollectionStatusResponse `json:"items"`
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

	// 检查是否已有记录（包含软删除），避免“删后重加”产生重复脏数据
	var existing model.CollectionItem
	err := database.DB.Unscoped().
		Where("collection_id = ? AND answer_id = ?", req.CollectionID, req.AnswerID).
		First(&existing).Error
	if err == nil {
		if existing.DeletedAt.Valid {
			if updateErr := database.DB.Unscoped().
				Model(&existing).
				Update("deleted_at", nil).Error; updateErr != nil {
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
			return
		}

		c.JSON(http.StatusConflict, Response{
			Code:    409,
			Message: "已经收藏过了",
		})
		return
	}
	if err != nil && err != gorm.ErrRecordNotFound {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "收藏失败",
		})
		return
	}

	// 创建收藏项
	item := model.CollectionItem{
		CollectionID: req.CollectionID,
		AnswerID:     req.AnswerID,
	}
	if createErr := database.DB.Create(&item).Error; createErr != nil {
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
	if err := database.DB.Unscoped().
		Where("collection_id = ? AND answer_id = ?", collectionID, answerID).
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

// GetAnswerCollectionStatus 获取回答是否已被当前用户收藏
// @Summary 获取回答收藏状态
// @Description 返回当前用户收藏该回答的收藏夹 ID 列表
// @Tags 收藏管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param answer_id query int true "回答ID"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"answer_id\": 1, \"collection_ids\": [2], \"is_collected\": true}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /collection/answer-status [get]
func GetAnswerCollectionStatus(c *gin.Context) {
	answerID, err := strconv.ParseUint(c.Query("answer_id"), 10, 64)
	if err != nil || answerID == 0 {
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

	uid := uint(userID.(float64))
	var collectionIDs []uint
	if err := database.DB.Table("collection_items").
		Select("collection_items.collection_id").
		Joins("JOIN collections ON collections.id = collection_items.collection_id").
		Where("collections.user_id = ? AND collection_items.answer_id = ? AND collection_items.deleted_at IS NULL AND collections.deleted_at IS NULL", uid, answerID).
		Pluck("collection_items.collection_id", &collectionIDs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: AnswerCollectionStatusResponse{
			AnswerID:      uint(answerID),
			CollectionIDs: collectionIDs,
			IsCollected:   len(collectionIDs) > 0,
		},
	})
}

// GetAnswerCollectionStatusBatch 批量获取回答收藏状态
func GetAnswerCollectionStatusBatch(c *gin.Context) {
	rawIDs := c.Query("answer_ids")
	if rawIDs == "" {
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

	answerIDs := make([]uint, 0)
	seen := make(map[uint]struct{})
	for _, part := range strings.Split(rawIDs, ",") {
		id, err := strconv.ParseUint(strings.TrimSpace(part), 10, 64)
		if err != nil || id == 0 {
			continue
		}
		uid := uint(id)
		if _, ok := seen[uid]; ok {
			continue
		}
		seen[uid] = struct{}{}
		answerIDs = append(answerIDs, uid)
	}
	if len(answerIDs) == 0 {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误",
		})
		return
	}

	type batchRow struct {
		AnswerID     uint `gorm:"column:answer_id"`
		CollectionID uint `gorm:"column:collection_id"`
	}

	uid := uint(userID.(float64))
	var rows []batchRow
	if err := database.DB.Table("collection_items").
		Select("collection_items.answer_id, collection_items.collection_id").
		Joins("JOIN collections ON collections.id = collection_items.collection_id").
		Where("collections.user_id = ? AND collection_items.answer_id IN ? AND collection_items.deleted_at IS NULL AND collections.deleted_at IS NULL", uid, answerIDs).
		Scan(&rows).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "查询失败",
		})
		return
	}

	grouped := make(map[uint][]uint, len(answerIDs))
	for _, row := range rows {
		grouped[row.AnswerID] = append(grouped[row.AnswerID], row.CollectionID)
	}

	items := make([]AnswerCollectionStatusResponse, 0, len(answerIDs))
	for _, answerID := range answerIDs {
		collectionIDs := grouped[answerID]
		items = append(items, AnswerCollectionStatusResponse{
			AnswerID:      answerID,
			CollectionIDs: collectionIDs,
			IsCollected:   len(collectionIDs) > 0,
		})
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: AnswerCollectionBatchStatusResponse{
			Items: items,
		},
	})
}

// RemoveAnswerFromAllCollections 从当前用户全部收藏夹移除回答
// @Summary 从全部收藏夹移除回答
// @Description 删除当前用户所有收藏夹中的该回答
// @Tags 收藏管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param answer_id query int true "回答ID"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"移除成功\", \"data\": {\"removed\": 1}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Router /collection/answer [delete]
func RemoveAnswerFromAllCollections(c *gin.Context) {
	answerID, err := strconv.ParseUint(c.Query("answer_id"), 10, 64)
	if err != nil || answerID == 0 {
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

	uid := uint(userID.(float64))
	subQuery := database.DB.Model(&model.Collection{}).
		Select("id").
		Where("user_id = ?", uid)

	result := database.DB.Unscoped().
		Where("answer_id = ? AND collection_id IN (?)", uint(answerID), subQuery).
		Delete(&model.CollectionItem{})
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "移除失败",
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "移除成功",
		Data: gin.H{
			"removed": result.RowsAffected,
		},
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
