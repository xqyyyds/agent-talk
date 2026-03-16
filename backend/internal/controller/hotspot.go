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

type HotspotInput struct {
	Source      string `json:"source" binding:"required,oneof=zhihu weibo"`
	SourceID    string `json:"source_id" binding:"required"`
	Title       string `json:"title" binding:"required,max=500"`
	Content     string `json:"content"`
	URL         string `json:"url"`
	Rank        int    `json:"rank"`
	Heat        string `json:"heat"`
	HotspotDate string `json:"hotspot_date" binding:"required"`
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

func BatchCreateHotspots(c *gin.Context) {
	var req BatchCreateHotspotsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	inserted := 0
	updated := 0

	for _, input := range req.Hotspots {
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
		Message: "ok",
		Data: gin.H{
			"inserted": inserted,
			"updated":  updated,
		},
	})

	publishStreamEvent("hotspots", "hotspots_upserted", gin.H{
		"inserted": inserted,
		"updated":  updated,
	})
}

func BatchCreateHotspotAnswers(c *gin.Context) {
	hotspotID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "invalid hotspot id"})
		return
	}

	var hotspot model.Hotspot
	if err := database.DB.First(&hotspot, hotspotID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "hotspot not found"})
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
		Message: "ok",
		Data: gin.H{
			"inserted": inserted,
			"skipped":  skipped,
		},
	})

	publishStreamEvent("hotspots", "hotspot_answers_upserted", gin.H{
		"hotspot_id": hotspotID,
		"inserted":   inserted,
		"skipped":    skipped,
	})
}

func GetHotspots(c *gin.Context) {
	source := c.Query("source")
	status := c.Query("status")
	date := c.Query("date")

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

func UpdateHotspotStatus(c *gin.Context) {
	hotspotID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "invalid hotspot id"})
		return
	}

	var req UpdateHotspotStatusRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	updates := map[string]interface{}{"status": req.Status}
	if req.Status == string(model.HotspotStatusCompleted) || req.Status == string(model.HotspotStatusSkipped) {
		now := time.Now()
		updates["processed_at"] = now
	}
	if req.QuestionID != nil {
		updates["question_id"] = *req.QuestionID
	}

	result := database.DB.Model(&model.Hotspot{}).Where("id = ?", hotspotID).Updates(updates)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: result.Error.Error()})
		return
	}
	if result.RowsAffected == 0 {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "hotspot not found"})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 200, Message: "ok"})

	publishStreamEvent("hotspots", "hotspot_status_updated", gin.H{
		"hotspot_id":  hotspotID,
		"status":      req.Status,
		"question_id": req.QuestionID,
	})
}

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

func GetHotspotDetail(c *gin.Context) {
	hotspotID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "invalid hotspot id"})
		return
	}

	var hotspot model.Hotspot
	if err := database.DB.Preload("Answers", func(db *gorm.DB) *gorm.DB {
		return db.Where("deleted_at IS NULL").Order("rank ASC")
	}).First(&hotspot, hotspotID).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "hotspot not found"})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 200, Data: hotspot})
}
