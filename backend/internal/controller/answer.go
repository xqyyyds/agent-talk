package controller

import (
	"backend/internal/database"
	"backend/internal/dto"
	"backend/internal/middleware"
	"backend/internal/model"
	"backend/internal/service"
	"fmt"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

type CreateAnswerRequest struct {
	Content    string `json:"content" binding:"required,min=10"`
	QuestionID uint   `json:"question_id" binding:"required"`
}

type UpdateAnswerRequest struct {
	Content string `json:"content" binding:"required,min=10"`
}

// CreateAnswer 创建回答
// @Summary 创建回答
// @Description 为问题创建一个新回答
// @Tags 回答管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param request body CreateAnswerRequest true "回答参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"创建成功\", \"data\": {...}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"问题不存在\"}"
// @Router /answer [post]
func CreateAnswer(c *gin.Context) {
	var req CreateAnswerRequest
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

	// 验证问题是否存在
	var question model.Question
	if err := database.DB.First(&question, req.QuestionID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "问题不存在",
		})
		return
	}

	answer := model.Answer{
		Content:    req.Content,
		QuestionID: req.QuestionID,
		UserID:     uint(userID.(float64)),
	}

	if err := database.DB.Create(&answer).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "创建回答失败",
		})
		return
	}

	database.DB.Preload("User").First(&answer, answer.ID)

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "创建成功",
		Data:    dto.ToAnswerResponse(&answer, nil),
	})

	publishStreamEvent("questions", "answer_created", gin.H{
		"answer_id":   answer.ID,
		"question_id": answer.QuestionID,
		"user_id":     answer.UserID,
	})
}

// GetAnswerList 获取回答列表
// @Summary 获取回答列表
// @Description 获取指定问题的回答列表，使用游标分页，包含点赞/点踩/评论统计
// @Tags 回答管理
// @Accept json
// @Produce json
// @Param question_id query int true "问题ID"
// @Param cursor query int false "游标（上一页最后一条记录的ID）"
// @Param limit query int false "每页数量" default(10)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"缺少问题ID\"}"
// @Router /answer/list [get]
func GetAnswerList(c *gin.Context) {
	questionID := c.Query("question_id")
	if questionID == "" {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "缺少问题ID",
		})
		return
	}

	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	if limit < 1 || limit > 100 {
		limit = 10
	}

	var answers []model.Answer
	query := database.DB.Where("question_id = ?", questionID)

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
				Message: "获取关注状态失败",
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

// GetAnswerFeed 获取回答Feed流
// @Summary 获取回答Feed流
// @Description 获取回答列表（包含问题信息），使用游标分页，用于首页推荐/最新
// @Tags 回答管理
// @Accept json
// @Produce json
// @Param cursor query int false "游标（上一页最后一条记录的ID）"
// @Param limit query int false "每页数量" default(10)
// @Success 200 {object} Response "{\"code\": 200, \"data\": {\"list\": [...], \"next_cursor\": 123, \"has_more\": true}}"
// @Router /answer/feed [get]
func GetAnswerFeed(c *gin.Context) {
	cursor, _ := strconv.ParseUint(c.Query("cursor"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	if limit < 1 || limit > 100 {
		limit = 10
	}

	var answers []model.Answer
	query := database.DB.Model(&model.Answer{})

	if cursor > 0 {
		query = query.Where("id < ?", cursor)
	}

	// Add Distinct to prevent duplicates from joins
	if err := query.Distinct().Order("id DESC").
		Preload("User").
		Preload("Question").
		Preload("Question.User").
		Preload("Question.Tags").
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

	// 收集所有需要的ID
	answerIDs := make([]uint, len(answers))
	questionIDs := make([]uint, 0, len(answers))
	questionIDSet := make(map[uint]struct{})

	for i, a := range answers {
		answerIDs[i] = a.ID
		if _, exists := questionIDSet[a.QuestionID]; !exists {
			questionIDs = append(questionIDs, a.QuestionID)
			questionIDSet[a.QuestionID] = struct{}{}
		}
	}

	// 批量获取回答统计信息
	answerStats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeAnswer, answerIDs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取回答统计信息失败",
		})
		return
	}

	// 批量获取问题统计信息
	questionStats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeQuestion, questionIDs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取问题统计信息失败",
		})
		return
	}

	// 获取当前用户的点赞状态
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

	// 组装响应数据
	list := make([]*dto.AnswerWithQuestionResponse, len(answers))
	for i, a := range answers {
		aStat := answerStats[a.ID]
		qStat := questionStats[a.QuestionID]
		resp := dto.ToAnswerWithQuestionResponse(&a, &aStat, &qStat)
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

// GetAnswerDetail 获取回答详情
// @Summary 获取回答详情
// @Description 根据ID获取回答详细信息，包含点赞/点踩/评论统计
// @Tags 回答管理
// @Accept json
// @Produce json
// @Param id path int true "回答ID"
// @Success 200 {object} Response "{\"code\": 200, \"data\": {...}}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"回答不存在\"}"
// @Router /answer/{id} [get]
func GetAnswerDetail(c *gin.Context) {
	id := c.Param("id")

	var answer model.Answer
	if err := database.DB.Preload("User").First(&answer, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "回答不存在",
		})
		return
	}

	stats, err := service.BatchGetStats(c.Request.Context(), model.TargetTypeAnswer, []uint{answer.ID})
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "获取统计信息失败",
		})
		return
	}

	stat := stats[answer.ID]
	resp := dto.ToAnswerResponse(&answer, &stat)
	if userID, ok := getOptionalUserID(c); ok {
		status, err := service.GetUserStatus(c.Request.Context(), userID, model.TargetTypeAnswer, answer.ID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取点赞状态失败",
			})
			return
		}
		resp.ReactionStatus = &status
	}
	if userID, ok := getOptionalUserID(c); ok && answer.UserID != 0 && resp.User != nil {
		isFollowing, err := getFollowStatus(c.Request.Context(), userID, model.TargetTypeUser, answer.UserID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, Response{
				Code:    500,
				Message: "获取关注状态失败",
			})
			return
		}
		resp.User.IsFollowing = &isFollowing
	}
	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: resp,
	})
}

// UpdateAnswer 更新回答
// @Summary 更新回答
// @Description 更新回答内容（仅作者本人可操作）
// @Tags 回答管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param id path int true "回答ID"
// @Param request body UpdateAnswerRequest true "更新参数"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"更新成功\"}"
// @Failure 400 {object} Response "{\"code\": 400, \"message\": \"参数错误\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"回答不存在\"}"
// @Router /answer/{id} [put]
func UpdateAnswer(c *gin.Context) {
	id := c.Param("id")

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var answer model.Answer
	if err := database.DB.First(&answer, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "回答不存在",
		})
		return
	}

	// 检查权限：作者本人或Admin可以修改
	userRole, _ := c.Get("role")
	if answer.UserID != uint(userID.(float64)) && userRole.(string) != "admin" {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	var req UpdateAnswerRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	if err := database.DB.Model(&answer).Update("content", req.Content).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "更新失败",
		})
		return
	}

	database.DB.Preload("User").First(&answer, id)

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "更新成功",
		Data:    dto.ToAnswerResponse(&answer, nil),
	})
}

// DeleteAnswer 删除回答
// @Summary 删除回答
// @Description 删除回答（仅作者本人可操作）
// @Tags 回答管理
// @Accept json
// @Produce json
// @Security BearerAuth
// @Param id path int true "回答ID"
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"删除成功\"}"
// @Failure 401 {object} Response "{\"code\": 401, \"message\": \"未授权\"}"
// @Failure 403 {object} Response "{\"code\": 403, \"message\": \"无权限操作\"}"
// @Failure 404 {object} Response "{\"code\": 404, \"message\": \"回答不存在\"}"
// @Router /answer/{id} [delete]
func DeleteAnswer(c *gin.Context) {
	id := c.Param("id")

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	var answer model.Answer
	if err := database.DB.First(&answer, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "回答不存在",
		})
		return
	}

	// 检查权限：作者本人或Admin可以删除
	userRole, _ := c.Get("role")
	if answer.UserID != uint(userID.(float64)) && userRole.(string) != "admin" {
		c.JSON(http.StatusForbidden, Response{
			Code:    403,
			Message: "无权限操作",
		})
		return
	}

	if err := database.DB.Delete(&answer).Error; err != nil {
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

// ResetAllNegativeStats 重置所有负数的统计数据（临时修复工具）
// @Summary 重置所有负数的统计数据
// @Description 扫描所有 Redis stats 键，重置负数为0（临时修复工具）
// @Tags 系统管理
// @Accept json
// @Produce json
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"重置完成，修复了 X 条记录\"}"
// @Router /admin/reset-stats [post]
func ResetAllNegativeStats(c *gin.Context) {
	ctx := c.Request.Context()
	resetCount := 0

	// 扫描所有 stats: 开头的键
	iter := database.RedisClient.Scan(ctx, 0, "stats:*", 0).Iterator()
	for iter.Next(ctx) {
		key := iter.Val()
		// 获取当前统计数据
		statsMap, err := database.RedisClient.HGetAll(ctx, key).Result()
		if err != nil {
			continue
		}

		// 检查是否有负数
		hasNegative := false
		for field, valStr := range statsMap {
			if val, err := strconv.ParseInt(valStr, 10, 64); err == nil && val < 0 {
				database.RedisClient.HSet(ctx, key, field, 0)
				hasNegative = true
			}
		}

		if hasNegative {
			resetCount++
			fmt.Printf("Reset negative stats for key: %s\n", key)
		}
	}

	if err := iter.Err(); err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "扫描失败",
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: fmt.Sprintf("重置完成，修复了 %d 条记录", resetCount),
	})
}

// ResetAllStats 完全重置所有统计数据（清空 bitmap 和 stats，用于修复不一致问题）
// @Summary 完全重置所有统计数据
// @Description 清空所有 Redis bitmap 和 stats，强制重新计算（临时修复工具）
// @Tags 系统管理
// @Accept json
// @Produce json
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"重置完成\"}"
// @Router /admin/reset-all-stats [post]
func ResetAllStats(c *gin.Context) {
	ctx := c.Request.Context()

	// 清空所有 bitmap 和 stats
	patterns := []string{
		"ulike:*", "plike:*", "udislike:*", "pdislike:*", "stats:*",
	}

	totalDeleted := 0
	for _, pattern := range patterns {
		iter := database.RedisClient.Scan(ctx, 0, pattern, 0).Iterator()
		for iter.Next(ctx) {
			key := iter.Val()
			if err := database.RedisClient.Del(ctx, key).Err(); err == nil {
				totalDeleted++
				fmt.Printf("Deleted key: %s\n", key)
			}
		}
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: fmt.Sprintf("完全重置完成，清空了 %d 条记录", totalDeleted),
	})
}

// ResetAllInteractionData 清空所有用户互动数据（保留问题和回答内容）
// @Summary 清空所有用户互动数据
// @Description 清空点赞、点踩、关注、粉丝、收藏、评论数据，保留问题和回答内容
// @Tags 系统管理
// @Accept json
// @Produce json
// @Success 200 {object} Response "{\"code\": 200, \"message\": \"重置完成\"}"
// @Router /admin/reset-interactions [post]
func ResetAllInteractionData(c *gin.Context) {
	ctx := c.Request.Context()
	result := map[string]int64{}

	// 1. 清空 Redis 所有相关数据
	patterns := []string{"ulike:*", "plike:*", "udislike:*", "pdislike:*", "stats:*"}
	for _, pattern := range patterns {
		iter := database.RedisClient.Scan(ctx, 0, pattern, 0).Iterator()
		for iter.Next(ctx) {
			if err := database.RedisClient.Del(ctx, iter.Val()).Err(); err == nil {
				result["redis_keys"]++
			}
		}
	}

	// 2. 清空数据库 Like 表（点赞/点踩记录）
	var likesCount int64
	database.DB.Exec("DELETE FROM likes").Count(&likesCount)
	result["likes_deleted"] = likesCount

	// 3. 清空数据库 Follow 表（关注/粉丝记录）
	var followsCount int64
	database.DB.Table("follows").Count(&followsCount)
	database.DB.Exec("DELETE FROM follows")
	result["follows_deleted"] = followsCount

	// 4. 清空数据库 CollectionItem 表（收藏记录）
	var collectionsCount int64
	database.DB.Table("collection_items").Count(&collectionsCount)
	database.DB.Exec("DELETE FROM collection_items")
	result["collection_items_deleted"] = collectionsCount

	// 5. 清空数据库 Comment 表（评论记录）
	var commentsCount int64
	database.DB.Table("comments").Count(&commentsCount)
	database.DB.Exec("DELETE FROM comments")
	result["comments_deleted"] = commentsCount

	// 保留：Questions（问题）、Answers（回答）、Users（用户）、Tags（标签）

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Message: fmt.Sprintf("互动数据清空完成 - Redis: %d, Likes: %d, Follows: %d, Collections: %d, Comments: %d",
			result["redis_keys"], result["likes_deleted"], result["follows_deleted"],
			result["collection_items_deleted"], result["comments_deleted"]),
	})
}
