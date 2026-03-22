package controller

import (
	"errors"
	"net/http"
	"regexp"
	"sort"
	"strconv"
	"strings"
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

var hotspotHeatPattern = regexp.MustCompile(`([0-9]+(?:\.[0-9]+)?)`)

func parseHeatScore(heat string) float64 {
	value := strings.ToLower(strings.TrimSpace(strings.ReplaceAll(heat, ",", "")))
	if value == "" {
		return 0
	}

	match := hotspotHeatPattern.FindStringSubmatch(value)
	if len(match) < 2 {
		return 0
	}

	number, err := strconv.ParseFloat(match[1], 64)
	if err != nil {
		return 0
	}

	switch {
	case strings.Contains(value, "亿"):
		number *= 100000000
	case strings.Contains(value, "万"), strings.Contains(value, "w"):
		number *= 10000
	case strings.Contains(value, "千"), strings.Contains(value, "k"):
		number *= 1000
	}
	return number
}

func hotspotSortLess(a, b model.Hotspot) bool {
	aHeat := parseHeatScore(a.Heat)
	bHeat := parseHeatScore(b.Heat)
	if aHeat != bHeat {
		return aHeat > bHeat
	}
	if !a.CrawledAt.Equal(b.CrawledAt) {
		return a.CrawledAt.After(b.CrawledAt)
	}
	return a.ID > b.ID
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
		result := database.DB.
			Where("source = ? AND source_id = ? AND hotspot_date = ?", hotspot.Source, hotspot.SourceID, hotspot.HotspotDate).
			First(&existing)
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

	recentDates := dates
	if len(recentDates) > 7 {
		recentDates = recentDates[:7]
	}

	minDate := ""
	maxDate := ""
	if len(dates) > 0 {
		maxDate = dates[0]
		minDate = dates[len(dates)-1]
	}

	c.JSON(http.StatusOK, Response{
		Code: 200,
		Data: gin.H{
			"dates":        dates,
			"recent_dates": recentDates,
			"min_date":     minDate,
			"max_date":     maxDate,
		},
	})
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

	allHotspots := make([]model.Hotspot, 0, 128)
	if err := query.Find(&allHotspots).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "query hotspot list failed"})
		return
	}

	if source == "" {
		zhihuList := make([]model.Hotspot, 0, len(allHotspots))
		weiboList := make([]model.Hotspot, 0, len(allHotspots))
		otherList := make([]model.Hotspot, 0, len(allHotspots))

		for _, item := range allHotspots {
			switch item.Source {
			case model.HotspotSourceZhihu:
				zhihuList = append(zhihuList, item)
			case model.HotspotSourceWeibo:
				weiboList = append(weiboList, item)
			default:
				otherList = append(otherList, item)
			}
		}

		sort.SliceStable(zhihuList, func(i, j int) bool {
			return hotspotSortLess(zhihuList[i], zhihuList[j])
		})
		sort.SliceStable(weiboList, func(i, j int) bool {
			return hotspotSortLess(weiboList[i], weiboList[j])
		})
		sort.SliceStable(otherList, func(i, j int) bool {
			return hotspotSortLess(otherList[i], otherList[j])
		})

		merged := make([]model.Hotspot, 0, len(allHotspots))
		zi, wi := 0, 0

		startWithZhihu := true
		if len(zhihuList) > 0 && len(weiboList) > 0 {
			startWithZhihu = hotspotSortLess(zhihuList[0], weiboList[0])
		} else if len(zhihuList) == 0 && len(weiboList) > 0 {
			startWithZhihu = false
		}

		pickZhihu := startWithZhihu
		for zi < len(zhihuList) || wi < len(weiboList) {
			if pickZhihu {
				if zi < len(zhihuList) {
					merged = append(merged, zhihuList[zi])
					zi++
				} else if wi < len(weiboList) {
					merged = append(merged, weiboList[wi])
					wi++
				}
			} else {
				if wi < len(weiboList) {
					merged = append(merged, weiboList[wi])
					wi++
				} else if zi < len(zhihuList) {
					merged = append(merged, zhihuList[zi])
					zi++
				}
			}
			pickZhihu = !pickZhihu
		}
		allHotspots = append(merged, otherList...)
	} else {
		sort.SliceStable(allHotspots, func(i, j int) bool {
			return hotspotSortLess(allHotspots[i], allHotspots[j])
		})
	}

	total := int64(len(allHotspots))
	hotspots := make([]model.Hotspot, 0, pageSize)
	start := (page - 1) * pageSize
	if start < len(allHotspots) {
		end := start + pageSize
		if end > len(allHotspots) {
			end = len(allHotspots)
		}
		hotspots = allHotspots[start:end]
	}

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

func GetHotspotByQuestionID(c *gin.Context) {
	questionID, err := strconv.ParseUint(c.Param("questionId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "invalid question id"})
		return
	}

	hotspot, findErr := findHotspotByQuestionID(uint(questionID))
	if findErr != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "query hotspot failed"})
		return
	}
	if hotspot == nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "hotspot not found"})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 200, Data: hotspot})
}

func findHotspotByQuestionID(questionID uint) (*model.Hotspot, error) {
	var hotspot model.Hotspot
	if err := database.DB.Where("question_id = ?", questionID).
		Order("updated_at DESC").
		First(&hotspot).Error; err == nil {
		return &hotspot, nil
	} else if !errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, err
	}

	linked, relinkErr := relinkHotspotByQuestionTitle(questionID)
	if relinkErr != nil {
		return nil, relinkErr
	}
	if linked != nil {
		return linked, nil
	}

	return findHotspotByQuestionTitle(questionID)
}

func loadHotspotMapForQuestions(questionIDs []uint) (map[uint]*model.Hotspot, error) {
	result := make(map[uint]*model.Hotspot)
	if len(questionIDs) == 0 {
		return result, nil
	}

	var linkedHotspots []model.Hotspot
	if err := database.DB.Where("question_id IN ?", questionIDs).
		Order("updated_at DESC").
		Find(&linkedHotspots).Error; err != nil {
		return nil, err
	}

	for i := range linkedHotspots {
		if linkedHotspots[i].QuestionID == nil {
			continue
		}
		id := *linkedHotspots[i].QuestionID
		if _, exists := result[id]; exists {
			continue
		}
		hotspot := linkedHotspots[i]
		result[id] = &hotspot
	}

	for _, questionID := range questionIDs {
		if _, exists := result[questionID]; exists {
			continue
		}
		hotspot, err := findHotspotByQuestionID(questionID)
		if err != nil {
			return nil, err
		}
		if hotspot != nil {
			result[questionID] = hotspot
		}
	}

	return result, nil
}

func relinkHotspotByQuestionTitle(questionID uint) (*model.Hotspot, error) {
	var question model.Question
	if err := database.DB.First(&question, questionID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}

	title := strings.TrimSpace(question.Title)
	if title == "" {
		return nil, nil
	}

	questionDate := question.CreatedAt.Format("2006-01-02")
	var hotspot model.Hotspot
	matched, err := findBestHotspotCandidate(title, questionDate)
	if err != nil {
		return nil, err
	}
	if matched == nil {
		return nil, nil
	}
	hotspot = *matched

	now := time.Now()
	updates := map[string]any{
		"question_id":  questionID,
		"status":       model.HotspotStatusCompleted,
		"processed_at": &now,
	}
	if err := database.DB.Model(&model.Hotspot{}).Where("id = ?", hotspot.ID).Updates(updates).Error; err != nil {
		return nil, err
	}

	hotspot.QuestionID = &questionID
	hotspot.Status = model.HotspotStatusCompleted
	hotspot.ProcessedAt = &now
	return &hotspot, nil
}

func findHotspotByQuestionTitle(questionID uint) (*model.Hotspot, error) {
	var question model.Question
	if err := database.DB.First(&question, questionID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}

	title := strings.TrimSpace(question.Title)
	if title == "" {
		return nil, nil
	}

	return findBestHotspotDisplayCandidate(title, question.CreatedAt.Format("2006-01-02"))
}

func findBestHotspotCandidate(questionTitle, questionDate string) (*model.Hotspot, error) {
	matchCandidates := func(date string) (*model.Hotspot, error) {
		query := database.DB.
			Where("question_id IS NULL")
		if date != "" {
			query = query.Where("hotspot_date = ?", date)
		}

		var candidates []model.Hotspot
		if err := query.Order("crawled_at DESC").Find(&candidates).Error; err != nil {
			return nil, err
		}

		for i := range candidates {
			if titlesMatch(questionTitle, candidates[i].Title) {
				return &candidates[i], nil
			}
		}
		return nil, nil
	}

	matched, err := matchCandidates(questionDate)
	if err != nil {
		return nil, err
	}
	if matched != nil {
		return matched, nil
	}
	return matchCandidates("")
}

func findBestHotspotDisplayCandidate(questionTitle, questionDate string) (*model.Hotspot, error) {
	matchCandidates := func(date string) (*model.Hotspot, error) {
		query := database.DB.Model(&model.Hotspot{})
		if date != "" {
			query = query.Where("hotspot_date = ?", date)
		}

		var candidates []model.Hotspot
		if err := query.Order("crawled_at DESC").Find(&candidates).Error; err != nil {
			return nil, err
		}

		for i := range candidates {
			if titlesMatch(questionTitle, candidates[i].Title) {
				return &candidates[i], nil
			}
		}
		return nil, nil
	}

	matched, err := matchCandidates(questionDate)
	if err != nil {
		return nil, err
	}
	if matched != nil {
		return matched, nil
	}
	return matchCandidates("")
}

func titlesMatch(questionTitle, hotspotTitle string) bool {
	normalizedQuestion := normalizeComparableTitle(questionTitle)
	normalizedHotspot := normalizeComparableTitle(hotspotTitle)
	if normalizedQuestion == "" || normalizedHotspot == "" {
		return false
	}
	return normalizedQuestion == normalizedHotspot ||
		strings.Contains(normalizedQuestion, normalizedHotspot) ||
		strings.Contains(normalizedHotspot, normalizedQuestion)
}

func normalizeComparableTitle(input string) string {
	s := strings.TrimSpace(strings.ToLower(input))
	replacer := strings.NewReplacer(
		" ", "",
		"　", "",
		"，", "",
		"。", "",
		"；", "",
		"：", "",
		"？", "",
		"！", "",
		"（", "",
		"）", "",
		"【", "",
		"】", "",
		"《", "",
		"》", "",
		"“", "",
		"”", "",
		"‘", "",
		"’", "",
		"(", "",
		")", "",
		"[", "",
		"]", "",
		"{", "",
		"}", "",
		"-", "",
		"—", "",
		"_", "",
		"·", "",
		":", "",
		";", "",
		",", "",
		".", "",
		"!", "",
		"?", "",
	)
	return replacer.Replace(s)
}
