package controller

import (
	"encoding/json"
	"net/http"
	"os"
	"strconv"
	"time"

	"backend/internal/database"
	"backend/internal/middleware"
	"backend/internal/model"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v4"
)

// ============================================
// 请求/响应模型
// ============================================

// RawConfig 用户原始配置结构
type RawConfig struct {
	Headline       string   `json:"headline"`
	Bio            string   `json:"bio"`
	Topics         []string `json:"topics"`
	Bias           string   `json:"bias"`
	StyleTag       string   `json:"style_tag"`
	ReplyMode      string   `json:"reply_mode"`
	ActivityLevel  string   `json:"activity_level"`
	Expressiveness string   `json:"expressiveness"`
}

type CreateAgentRequest struct {
	Name           string   `json:"name" binding:"required,min=2,max=50"`
	Headline       string   `json:"headline" binding:"max=100"`
	Bio            string   `json:"bio" binding:"max=1000"`
	Topics         []string `json:"topics" binding:"required,min=1,dive,max=50"`
	Bias           string   `json:"bias" binding:"max=200"`
	StyleTag       string   `json:"style_tag" binding:"max=50"`
	ReplyMode      string   `json:"reply_mode" binding:"max=50"`
	ActivityLevel  string   `json:"activity_level" binding:"required,oneof=high medium low"`
	Avatar         string   `json:"avatar"`
	SystemPrompt   string   `json:"system_prompt" binding:"omitempty,max=5000"`
	Expressiveness string   `json:"expressiveness" binding:"omitempty,oneof=terse balanced verbose dynamic"`
}

type UpdateAgentRequest struct {
	Name           *string   `json:"name" binding:"omitempty,min=2,max=50"`
	Headline       *string   `json:"headline" binding:"omitempty,max=100"`
	Bio            *string   `json:"bio" binding:"omitempty,max=1000"`
	Topics         *[]string `json:"topics" binding:"omitempty,min=1,dive,max=50"`
	Bias           *string   `json:"bias" binding:"omitempty,max=200"`
	StyleTag       *string   `json:"style_tag" binding:"omitempty,max=50"`
	ReplyMode      *string   `json:"reply_mode" binding:"omitempty,max=50"`
	ActivityLevel  *string   `json:"activity_level" binding:"omitempty,oneof=high medium low"`
	Avatar         *string   `json:"avatar"`
	SystemPrompt   *string   `json:"system_prompt" binding:"omitempty,max=5000"`
	Expressiveness *string   `json:"expressiveness" binding:"omitempty,oneof=terse balanced verbose dynamic"`
}

type AgentResponse struct {
	ID        uint       `json:"id"`
	Name      string     `json:"name"`
	Avatar    string     `json:"avatar"`
	IsSystem  bool       `json:"is_system"`
	OwnerID   uint       `json:"owner_id"`
	RawConfig RawConfig  `json:"raw_config"`
	Stats     AgentStats `json:"stats"`
	APIKey    string     `json:"api_key,omitempty"` // 只在创建时返回
}

type AgentStats struct {
	QuestionsCount int `json:"questions_count"`
	AnswersCount   int `json:"answers_count"`
	FollowersCount int `json:"followers_count"`
}

type AgentListResponse struct {
	Agents   []AgentResponse `json:"agents"`
	Total    int64           `json:"total"`
	Page     int             `json:"page"`
	PageSize int             `json:"page_size"`
}

// ============================================
// Agent CRUD 接口
// ============================================

// CreateAgent 创建新的 Agent
// @Summary 创建 Agent
// @Description 创建一个新的 Agent，当前用户成为其 owner
// @Tags Agent
// @Accept json
// @Produce json
// @Param request body CreateAgentRequest true "创建请求"
// @Success 200 {object} Response{data=AgentResponse}
// @Failure 400 {object} Response
// @Failure 401 {object} Response
// @Router /api/agents [post]
func CreateAgent(c *gin.Context) {
	// 获取当前用户 ID（从 JWT 中间件）
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"code": 401, "message": "未登录"})
		return
	}

	var req CreateAgentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": err.Error()})
		return
	}

	// 构建 raw_config
	rawConfig := RawConfig{
		Headline:       req.Headline,
		Bio:            req.Bio,
		Topics:         req.Topics,
		Bias:           req.Bias,
		StyleTag:       req.StyleTag,
		ReplyMode:      req.ReplyMode,
		ActivityLevel:  req.ActivityLevel,
		Expressiveness: req.Expressiveness,
	}
	rawConfigJSON, err := json.Marshal(rawConfig)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": "配置序列化失败"})
		return
	}

	// 创建 Agent（作为 User 记录）
	// JWT 中间件存储的 userID 是 float64，需要转换为 uint
	ownerID := uint(userID.(float64))
	agent := model.User{
		Name:           req.Name,
		Avatar:         req.Avatar,
		Role:           model.RoleAgent,
		OwnerID:        ownerID,
		IsSystem:       false,
		RawConfig:      string(rawConfigJSON),
		SystemPrompt:   req.SystemPrompt,
		Expressiveness: req.Expressiveness,
	}

	// BeforeCreate 钩子会自动生成 API Key
	if err := database.DB.Create(&agent).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "创建失败"})
		return
	}

	// 重新查询以获取关联数据
	database.DB.Preload("Owner").First(&agent, agent.ID)

	// 构建响应（包含 API Key，只显示一次）
	response := buildAgentResponse(agent, true)

	c.JSON(http.StatusOK, gin.H{"code": 200, "data": response})

	publishStreamEvent("agents", "agent_created", gin.H{
		"agent_id":   agent.ID,
		"name":       agent.Name,
		"is_system":  agent.IsSystem,
		"owner_id":   agent.OwnerID,
		"created_at": agent.CreatedAt,
	})
}

// GetAgents 获取 Agent 列表（分页）
// @Summary 获取 Agent 列表
// @Description 获取所有 Agent 列表，支持分页
// @Tags Agent
// @Produce json
// @Param page query int false "页码" default(1)
// @Param page_size query int false "每页数量" default(20)
// @Success 200 {object} Response{data=AgentListResponse}
// @Router /api/agents [get]
func GetAgents(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))

	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 20
	}

	var agents []model.User
	var total int64

	// 查询总数
	database.DB.Model(&model.User{}).Where("role = ?", model.RoleAgent).Count(&total)

	// 查询列表
	offset := (page - 1) * pageSize
	database.DB.Where("role = ?", model.RoleAgent).
		Preload("Owner").
		Offset(offset).
		Limit(pageSize).
		Order("is_system DESC, created_at DESC").
		Find(&agents)

	// 构建响应
	response := AgentListResponse{
		Agents:   make([]AgentResponse, 0, len(agents)),
		Total:    total,
		Page:     page,
		PageSize: pageSize,
	}

	for _, agent := range agents {
		response.Agents = append(response.Agents, buildAgentResponse(agent, false))
	}

	c.JSON(http.StatusOK, gin.H{"code": 200, "data": response})
}

// GetMyAgents 获取当前用户创建的 Agent
// @Summary 获取我的 Agent
// @Description 获取当前用户创建的所有 Agent
// @Tags Agent
// @Produce json
// @Success 200 {object} Response{data=[]AgentResponse}
// @Failure 401 {object} Response
// @Router /api/agents/my [get]
func GetMyAgents(c *gin.Context) {
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"code": 401, "message": "未登录"})
		return
	}

	var agents []model.User
	database.DB.Where("role = ? AND owner_id = ?", model.RoleAgent, userID).
		Preload("Owner").
		Order("created_at DESC").
		Find(&agents)

	response := make([]AgentResponse, 0, len(agents))
	for _, agent := range agents {
		response = append(response, buildAgentResponse(agent, false))
	}

	c.JSON(http.StatusOK, gin.H{"code": 200, "data": response})
}

// GetAgent 获取 Agent 详情
// @Summary 获取 Agent 详情
// @Description 根据 ID 获取 Agent 详情
// @Tags Agent
// @Produce json
// @Param id path int true "Agent ID"
// @Success 200 {object} Response{data=AgentResponse}
// @Failure 404 {object} Response
// @Router /api/agents/{id} [get]
func GetAgent(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": "无效的 ID"})
		return
	}

	var agent model.User
	if err := database.DB.Where("role = ? AND id = ?", model.RoleAgent, id).
		Preload("Owner").
		First(&agent).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": 404, "message": "Agent 不存在"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"code": 200, "data": buildAgentResponse(agent, false)})
}

// UpdateAgent 更新 Agent
// @Summary 更新 Agent
// @Description 更新 Agent 配置（仅所有者或 Admin）
// @Tags Agent
// @Accept json
// @Produce json
// @Param id path int true "Agent ID"
// @Param request body UpdateAgentRequest true "更新请求"
// @Success 200 {object} Response{data=AgentResponse}
// @Failure 403 {object} Response
// @Failure 404 {object} Response
// @Router /api/agents/{id} [put]
func UpdateAgent(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": "无效的 ID"})
		return
	}

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"code": 401, "message": "未登录"})
		return
	}

	userRole, _ := c.Get("role")
	// JWT 中间件存储的 userID 是 float64，需要转换为 uint
	currentUserID := uint(userID.(float64))

	var agent model.User
	if err := database.DB.Where("role = ? AND id = ?", model.RoleAgent, id).First(&agent).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": 404, "message": "Agent 不存在"})
		return
	}

	// 权限检查：只有 owner 或 admin 可以修改
	if agent.OwnerID != currentUserID && userRole != model.RoleAdmin {
		c.JSON(http.StatusForbidden, gin.H{"code": 403, "message": "无权限修改此 Agent"})
		return
	}

	// 系统 Agent 只能由 Admin 修改
	if agent.IsSystem && userRole != model.RoleAdmin {
		c.JSON(http.StatusForbidden, gin.H{"code": 403, "message": "系统 Agent 只能由管理员修改"})
		return
	}

	var req UpdateAgentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": err.Error()})
		return
	}

	// 解析现有的 raw_config
	var rawConfig RawConfig
	if agent.RawConfig != "" {
		if err := json.Unmarshal([]byte(agent.RawConfig), &rawConfig); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "配置解析失败"})
			return
		}
	}

	// 更新 raw_config 字段
	if req.Headline != nil {
		rawConfig.Headline = *req.Headline
	}
	if req.Bio != nil {
		rawConfig.Bio = *req.Bio
	}
	if req.Topics != nil {
		rawConfig.Topics = *req.Topics
	}
	if req.Bias != nil {
		rawConfig.Bias = *req.Bias
	}
	if req.StyleTag != nil {
		rawConfig.StyleTag = *req.StyleTag
	}
	if req.ReplyMode != nil {
		rawConfig.ReplyMode = *req.ReplyMode
	}
	if req.ActivityLevel != nil {
		rawConfig.ActivityLevel = *req.ActivityLevel
	}

	// 重新序列化 raw_config
	newRawConfigJSON, err := json.Marshal(rawConfig)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "配置序列化失败"})
		return
	}

	// 构建 updates map
	updates := make(map[string]interface{})
	if req.Name != nil {
		updates["name"] = *req.Name
	}
	if req.Avatar != nil {
		updates["avatar"] = *req.Avatar
	}
	if req.SystemPrompt != nil {
		updates["system_prompt"] = *req.SystemPrompt
	}
	if req.Expressiveness != nil {
		updates["expressiveness"] = *req.Expressiveness
	}
	updates["raw_config"] = string(newRawConfigJSON)

	if err := database.DB.Model(&agent).Updates(updates).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "更新失败"})
		return
	}

	// 重新获取更新后的数据
	database.DB.Preload("Owner").First(&agent, id)
	c.JSON(http.StatusOK, gin.H{"code": 200, "data": buildAgentResponse(agent, false)})

	publishStreamEvent("agents", "agent_updated", gin.H{
		"agent_id":   agent.ID,
		"name":       agent.Name,
		"is_system":  agent.IsSystem,
		"owner_id":   agent.OwnerID,
		"updated_at": agent.UpdatedAt,
	})
}

// DeleteAgent 删除 Agent
// @Summary 删除 Agent
// @Description 删除 Agent（仅所有者或 Admin）
// @Tags Agent
// @Produce json
// @Param id path int true "Agent ID"
// @Success 200 {object} Response
// @Failure 403 {object} Response
// @Failure 404 {object} Response
// @Router /api/agents/{id} [delete]
func DeleteAgent(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": "无效的 ID"})
		return
	}

	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"code": 401, "message": "未登录"})
		return
	}

	userRole, _ := c.Get("role")
	// JWT 中间件存储的 userID 是 float64，需要转换为 uint
	currentUserID := uint(userID.(float64))

	var agent model.User
	if err := database.DB.Where("role = ? AND id = ?", model.RoleAgent, id).First(&agent).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": 404, "message": "Agent 不存在"})
		return
	}

	// 权限检查
	if agent.OwnerID != currentUserID && userRole != model.RoleAdmin {
		c.JSON(http.StatusForbidden, gin.H{"code": 403, "message": "无权限删除此 Agent"})
		return
	}

	// 系统 Agent 只能由 Admin 删除
	if agent.IsSystem && userRole != model.RoleAdmin {
		c.JSON(http.StatusForbidden, gin.H{"code": 403, "message": "系统 Agent 只能由管理员删除"})
		return
	}

	if err := database.DB.Delete(&agent).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "删除失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"code": 200, "message": "删除成功"})

	publishStreamEvent("agents", "agent_deleted", gin.H{
		"agent_id":  agent.ID,
		"name":      agent.Name,
		"is_system": agent.IsSystem,
		"owner_id":  agent.OwnerID,
	})
}

// ============================================
// 内部 API：供 Python 服务调用
// ============================================

type InternalAgentResponse struct {
	ID             uint   `json:"id"`
	Name           string `json:"name"`
	Avatar         string `json:"avatar"`
	APIKey         string `json:"api_key"`
	JWTToken       string `json:"jwt_token"`
	SystemPrompt   string `json:"system_prompt"`
	RawConfig      string `json:"raw_config"`
	IsSystem       bool   `json:"is_system"`
	OwnerID        uint   `json:"owner_id"`
	Expressiveness string `json:"expressiveness"`
}

// GetActiveAgents 获取所有活跃的 Agent（供内部调用）
// @Summary 获取活跃 Agent 列表（内部）
// @Description 获取所有 Agent 配置，供 Python 服务使用
// @Tags Internal
// @Produce json
// @Router /internal/agents [get]
func GetActiveAgents(c *gin.Context) {
	var agents []model.User

	database.DB.Where("role = ?", model.RoleAgent).
		Select("id, name, avatar, api_key, system_prompt, raw_config, is_system, owner_id, expressiveness").
		Find(&agents)

	result := make([]InternalAgentResponse, 0, len(agents))
	for _, agent := range agents {
		jwtToken, _ := generateAgentJWT(agent.ID)
		result = append(result, InternalAgentResponse{
			ID:             agent.ID,
			Name:           agent.Name,
			Avatar:         agent.Avatar,
			APIKey:         agent.APIKey,
			JWTToken:       jwtToken,
			SystemPrompt:   agent.SystemPrompt,
			RawConfig:      agent.RawConfig,
			IsSystem:       agent.IsSystem,
			OwnerID:        agent.OwnerID,
			Expressiveness: agent.Expressiveness,
		})
	}

	c.JSON(http.StatusOK, gin.H{"code": 200, "data": result})
}

func generateAgentJWT(userID uint) (string, error) {
	claims := jwt.MapClaims{
		middleware.IdentityKey: userID,
		"role":                 model.RoleAgent,
		"exp":                  time.Now().Add(24 * time.Hour).Unix(),
		"orig_iat":             time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	secret := []byte(os.Getenv("JWT_SECRET_KEY"))
	return token.SignedString(secret)
}

// ============================================
// 辅助函数
// ============================================

// buildAgentResponse 构建 Agent 响应
func buildAgentResponse(agent model.User, includeAPIKey bool) AgentResponse {
	// 解析 raw_config
	var rawConfig RawConfig
	if agent.RawConfig != "" {
		// 忽略解析错误，使用空配置
		_ = json.Unmarshal([]byte(agent.RawConfig), &rawConfig)
	}

	// 获取统计数据
	stats := getAgentStats(agent.ID)

	response := AgentResponse{
		ID:        agent.ID,
		Name:      agent.Name,
		Avatar:    agent.Avatar,
		IsSystem:  agent.IsSystem,
		OwnerID:   agent.OwnerID,
		RawConfig: rawConfig,
		Stats:     stats,
	}

	// 只在创建时返回 API Key
	if includeAPIKey {
		response.APIKey = agent.APIKey
	}

	return response
}

// getAgentStats 获取 Agent 统计数据
func getAgentStats(agentID uint) AgentStats {
	var questionsCount, answersCount, followersCount int64

	// 统计问题数
	database.DB.Model(&model.Question{}).Where("user_id = ?", agentID).Count(&questionsCount)

	// 统计回答数
	database.DB.Model(&model.Answer{}).Where("user_id = ?", agentID).Count(&answersCount)

	// 统计粉丝数
	database.DB.Model(&model.Follow{}).Where("target_id = ? AND target_type = ?", agentID, model.TargetTypeUser).Count(&followersCount)

	return AgentStats{
		QuestionsCount: int(questionsCount),
		AnswersCount:   int(answersCount),
		FollowersCount: int(followersCount),
	}
}
