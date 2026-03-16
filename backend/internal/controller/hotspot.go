package controller

import (
	"errors"
	"net/http"
	"strconv"
	"time"

	"backend/internal/database"
	"backend/internal/model"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// ============================================
// 请求结构体
// ============================================

type HotspotInput struct {
	Source      string `json:"source" binding:"required,oneof=zhihu weibo"`
	SourceID    string `json:"source_id" binding:"required"`
	Title       string `json:"title" binding:"required,max=500"`
	Content     string `json:"content"`
	URL         string `json:"url"`
	Rank        int    `json:"rank"`
	Heat        string `json:"heat"`
	HotspotDate string `json:"hotspot_date" binding:"required"` // "2026-03-05"
}

type BatchCreateHotspotsRequest struct {
	Hotspots []HotspotInput `json:"hotspots" binding:"required,min=1"`
}

type HotspotAnswerInput struct {
	AuthorName    string `json:"author_name" binding:"required,max=200"`
	AuthorURL     string `json:"author_url"`
	Content       string `json:"content" binding:"required"`
	UpvoteCount   int    `json:"upvote_count"`
	CommentCount  int    `json:"comment_count"`
	Rank          int    `json:"rank"`
	ZhihuAnswerID string `json:"zhihu_answer_id" binding:"required"`
}

type BatchCreateAnswersRequest struct {
	Answers []HotspotAnswerInput `json:"answers" binding:"required,min=1"`
}

type UpdateHotspotStatusRequest struct {
	Status     string `json:"status" binding:"required,oneof=pending processing completed skipped"`
	QuestionID *uint  `json:"question_id"`
}

// ============================================
// 内部 API：爬虫写入
// ============================================

// BatchCreateHotspots 批量写入热点（知乎/微博通用）
// 供爬虫调用，不走 JWT 认证
func BatchCreateHotspots(c *gin.Context) {
	var req BatchCreateHotspotsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	inserted := 0
	updated := 0

	for _, input := range req.Hotspots {
		// 解析日期
		hotspotDate, err := time.Parse("2006-01-02", input.HotspotDate)
		if err != nil {
			hotspotDate = time.Now()
		}

		hotspot := model.Hotspot{
			Source:      model.HotspotSource(input.Source),
			SourceID:    input.SourceID,
			Title:       input.Title,
			Content:     input.Content,
			URL:         input.URL,
			Rank:        input.Rank,
			Heat:        input.Heat,
			Status:      model.HotspotStatusPending,
			HotspotDate: hotspotDate,
			CrawledAt:   time.Now(),
		}

		var existing model.Hotspot
		result := database.DB.Where(model.Hotspot{Source: hotspot.Source, SourceID: hotspot.SourceID}).First(&existing)
		if result.Error == nil {
			if err := database.DB.Model(&existing).Updates(map[string]any{
				"title":        hotspot.Title,
				"content":      hotspot.Content,
				"url":          hotspot.URL,
				"rank":         hotspot.Rank,
				"heat":         hotspot.Heat,
				"hotspot_date": hotspot.HotspotDate,
				"crawled_at":   hotspot.CrawledAt,
			}).Error; err != nil {
				c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: err.Error()})
				return
			}
			updated++
			continue
		}

		if !errors.Is(result.Error, gorm.ErrRecordNotFound) {
			c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: result.Error.Error()})
			return
		}

		if err := database.DB.Create(&hotspot).Error; err != nil {
			c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: err.Error()})
			return
		}
		inserted++
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "成功写入 " + strconv.Itoa(inserted) + " 条热点，更新 " + strconv.Itoa(updated) + " 条热点",
		Data:    gin.H{"inserted": inserted, "updated": updated},
	})
}

// BatchCreateHotspotAnswers 为知乎热点批量添加原始回答
// 供爬虫调用，不走 JWT 认证
func BatchCreateHotspotAnswers(c *gin.Context) {
	hotspotID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "无效的 hotspot_id"})
		return
	}

	// 确认热点存在
	var hotspot model.Hotspot
	if err := database.DB.First(&hotspot, hotspotID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "热点不存在"})
		return
	}

	var req BatchCreateAnswersRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	inserted := 0
	skipped := 0

	for _, input := range req.Answers {
		answer := model.HotspotAnswer{
			HotspotID:     uint(hotspotID),
			AuthorName:    input.AuthorName,
			AuthorURL:     input.AuthorURL,
			Content:       input.Content,
			UpvoteCount:   input.UpvoteCount,
			CommentCount:  input.CommentCount,
			Rank:          input.Rank,
			ZhihuAnswerID: input.ZhihuAnswerID,
		}

		result := database.DB.
			Where(model.HotspotAnswer{HotspotID: uint(hotspotID), ZhihuAnswerID: input.ZhihuAnswerID}).
			FirstOrCreate(&answer)

		if result.Error != nil {
			c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: result.Error.Error()})
			return
		}

		if result.RowsAffected > 0 {
			inserted++
		} else {
			skipped++
		}
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "成功写入 " + strconv.Itoa(inserted) + " 条回答，跳过 " + strconv.Itoa(skipped) + " 条重复",
		Data:    gin.H{"inserted": inserted, "skipped": skipped},
	})
}

// ============================================
// 内部 API：Agent Service 读取与更新
// ============================================

// GetHotspots 获取热点列表
// 支持 source / status / date 筛选，供 Agent Service 使用
func GetHotspots(c *gin.Context) {
	source := c.Query("source") // "zhihu" | "weibo"
	status := c.Query("status") // "pending" | "processing" | "completed" | "skipped"
	date := c.Query("date")     // "2026-03-05"

	query := database.DB.Model(&model.Hotspot{})

	if source != "" {
		query = query.Where("source = ?", source)
	}
	if status != "" {
		query = query.Where("status = ?", status)
	}
	if date != "" {
		query = query.Where("hotspot_date = ?", date)
	}

	var hotspots []model.Hotspot
	if err := query.Order("rank ASC").Find(&hotspots).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 200, Data: hotspots})
}

// UpdateHotspotStatus 更新热点处理状态
// pending → processing → completed / skipped
func UpdateHotspotStatus(c *gin.Context) {
	hotspotID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "无效的 hotspot_id"})
		return
	}

	var req UpdateHotspotStatusRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	updates := map[string]interface{}{"status": req.Status}
	if req.Status == "completed" || req.Status == "skipped" {
		now := time.Now()
		updates["processed_at"] = now
	}
	if req.QuestionID != nil {
		updates["question_id"] = *req.QuestionID
	}

	result := database.DB.Model(&model.Hotspot{}).
		Where("id = ?", hotspotID).
		Updates(updates)

	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: result.Error.Error()})
		return
	}
	if result.RowsAffected == 0 {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "热点不存在"})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 200, Message: "状态更新成功"})
}

// ============================================
// 前端展示 API（走 JWT 认证）
// ============================================

// GetHotspotDates 获取有数据的日期列表（前端期次导航用）
func GetHotspotDates(c *gin.Context) {
	source := c.Query("source")

	query := database.DB.Model(&model.Hotspot{}).
		Select("DISTINCT DATE(hotspot_date) as d").
		Order("d DESC")

	if source != "" {
		query = query.Where("source = ?", source)
	}

	var dates []string
	query.Pluck("d", &dates)

	c.JSON(http.StatusOK, Response{Code: 200, Data: dates})
}

// GetHotspotList 获取热点列表（分页，前端展示用）
func GetHotspotList(c *gin.Context) {
	source := c.Query("source")
	dateStr := c.Query("date")
	pageStr := c.DefaultQuery("page", "1")
	pageSizeStr := c.DefaultQuery("page_size", "20")

	page, _ := strconv.Atoi(pageStr)
	pageSize, _ := strconv.Atoi(pageSizeStr)
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 20
	}

	// 默认返回今日热点
	if dateStr == "" {
		dateStr = time.Now().Format("2006-01-02")
	}

	query := database.DB.Model(&model.Hotspot{}).Where("hotspot_date = ?", dateStr)
	if source != "" {
		query = query.Where("source = ?", source)
	}

	var total int64
	query.Count(&total)

	var hotspots []model.Hotspot
	query.Order("source ASC, rank ASC").
		Offset((page - 1) * pageSize).
		Limit(pageSize).
		Find(&hotspots)

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: gin.H{
			"hotspots":  hotspots,
			"total":     total,
			"page":      page,
			"page_size": pageSize,
		},
	})
}

// GetHotspotDetail 获取热点详情 + 知乎原始回答
func GetHotspotDetail(c *gin.Context) {
	hotspotID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "无效的 hotspot_id"})
		return
	}

	var hotspot model.Hotspot
	if err := database.DB.Preload("Answers", func(db *gorm.DB) *gorm.DB {
		return db.Where("deleted_at IS NULL").Order("rank ASC")
	}).First(&hotspot, hotspotID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "热点不存在"})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 200, Data: hotspot})
}
