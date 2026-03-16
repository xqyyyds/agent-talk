package dto

import (
	"backend/internal/database"
	"time"

	"backend/internal/model"
	"backend/internal/service"
)

// UserResponse 用户响应结构
type UserResponse struct {
	ID     uint    `json:"id"`
	Name   string  `json:"name"`             // 显示名称（所有人都有）
	Handle *string `json:"handle,omitempty"` // 登录账号（仅真人，Agent 为 null）
	Role   string  `json:"role"`
	Avatar string  `json:"avatar"`

	// Agent 专属字段（可选）
	APIKey    *string `json:"api_key,omitempty"`
	IsSystem  *bool   `json:"is_system,omitempty"`
	OwnerID   *uint   `json:"owner_id,omitempty"`
	OwnerName *string `json:"owner_name,omitempty"`

	IsFollowing *bool `json:"is_following,omitempty"`
}

// UserProfileResponse 用户资料响应（带统计数据）
type UserProfileResponse struct {
	ID     uint    `json:"id"`
	Name   string  `json:"name"`             // 显示名称（所有人都有）
	Handle *string `json:"handle,omitempty"` // 登录账号（仅真人，Agent 为 null）
	Role   string  `json:"role"`
	Avatar string  `json:"avatar"`

	// Agent 专属字段（可选）
	APIKey    *string `json:"api_key,omitempty"`
	IsSystem  *bool   `json:"is_system,omitempty"`
	OwnerID   *uint   `json:"owner_id,omitempty"`
	OwnerName *string `json:"owner_name,omitempty"`

	Stats       UserStats `json:"stats"`
	IsFollowing *bool     `json:"is_following,omitempty"`
}

// UserStats 用户统计数据
type UserStats struct {
	QuestionCount  int64 `json:"question_count"`
	AnswerCount    int64 `json:"answer_count"`
	FollowerCount  int64 `json:"follower_count"`
	FollowingCount int64 `json:"following_count"`

	// Agent 专属统计：收到的赞/踩
	ReceivedLikeCount    int64 `json:"received_like_count"`
	ReceivedDislikeCount int64 `json:"received_dislike_count"`

	// 真人专属统计：给出的赞/踩、关注的问题数
	GivenLikeCount        int64 `json:"given_like_count"`
	GivenDislikeCount     int64 `json:"given_dislike_count"`
	FollowedQuestionCount int64 `json:"followed_question_count"`
}

// QuestionResponse 问题响应结构
type QuestionResponse struct {
	ID             uint          `json:"id"`
	Title          string        `json:"title"`
	Content        string        `json:"content"`
	Type           string        `json:"type"`
	UserID         uint          `json:"user_id"`
	User           *UserResponse `json:"user,omitempty"`
	Tags           []TagResponse `json:"tags,omitempty"`
	CreatedAt      time.Time     `json:"created_at"`
	UpdatedAt      time.Time     `json:"updated_at"`
	Stats          *ObjectStats  `json:"stats,omitempty"`
	ReactionStatus *int          `json:"reaction_status,omitempty"`
	IsFollowing    *bool         `json:"is_following,omitempty"`
}

// AnswerResponse 回答响应结构
type AnswerResponse struct {
	ID             uint          `json:"id"`
	Content        string        `json:"content"`
	QuestionID     uint          `json:"question_id"`
	UserID         uint          `json:"user_id"`
	User           *UserResponse `json:"user,omitempty"`
	CreatedAt      time.Time     `json:"created_at"`
	UpdatedAt      time.Time     `json:"updated_at"`
	Stats          *ObjectStats  `json:"stats,omitempty"`
	ReactionStatus *int          `json:"reaction_status,omitempty"`
}

// AnswerWithQuestionResponse 回答响应结构（包含问题信息，用于Feed流）
type AnswerWithQuestionResponse struct {
	ID             uint              `json:"id"`
	Content        string            `json:"content"`
	QuestionID     uint              `json:"question_id"`
	Question       *QuestionResponse `json:"question,omitempty"`
	UserID         uint              `json:"user_id"`
	User           *UserResponse     `json:"user,omitempty"`
	CreatedAt      time.Time         `json:"created_at"`
	UpdatedAt      time.Time         `json:"updated_at"`
	Stats          *ObjectStats      `json:"stats,omitempty"`
	ReactionStatus *int              `json:"reaction_status,omitempty"`
}

// CommentResponse 评论响应结构
type CommentResponse struct {
	ID             uint          `json:"id"`
	Content        string        `json:"content"`
	AnswerID       uint          `json:"answer_id"`
	UserID         uint          `json:"user_id"`
	User           *UserResponse `json:"user,omitempty"`
	RootID         uint          `json:"root_id"`
	ParentID       uint          `json:"parent_id"`
	ParentUser     *UserResponse `json:"parent_user,omitempty"`
	CreatedAt      time.Time     `json:"created_at"`
	UpdatedAt      time.Time     `json:"updated_at"`
	Stats          *ObjectStats  `json:"stats,omitempty"`
	ReactionStatus *int          `json:"reaction_status,omitempty"`
}

// TagResponse 标签响应结构
type TagResponse struct {
	ID          uint   `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	Icon        string `json:"icon,omitempty"`
}

// ObjectStats 对象统计数据
type ObjectStats struct {
	LikeCount    int64 `json:"like_count"`
	DislikeCount int64 `json:"dislike_count"`
	CommentCount int64 `json:"comment_count"`
}

// CollectionResponse 收藏夹响应结构
type CollectionResponse struct {
	ID        uint      `json:"id"`
	UserID    uint      `json:"user_id"`
	Name      string    `json:"name"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// FollowResponse 关注关系响应结构
type FollowResponse struct {
	ID         uint      `json:"id"`
	UserID     uint      `json:"user_id"`
	TargetType uint8     `json:"target_type"`
	TargetID   uint      `json:"target_id"`
	CreatedAt  time.Time `json:"created_at"`
}

// PaginatedResponse 分页响应结构
type PaginatedResponse struct {
	List       interface{} `json:"list"`
	NextCursor uint        `json:"next_cursor"`
	HasMore    bool        `json:"has_more"`
}

// 转换函数：Model -> DTO

// ToUserResponse 转换 User 模型为响应结构
func ToUserResponse(user *model.User) *UserResponse {
	if user == nil {
		return nil
	}

	resp := &UserResponse{
		ID:     user.ID,
		Name:   user.Name,   // 显示名称（所有人都有）
		Handle: user.Handle, // 登录账号（仅真人，Agent 为 nil）
		Role:   string(user.Role),
		Avatar: user.Avatar,
	}

	// Agent 专属字段：仅当角色为 Agent 时返回
	if user.Role == model.RoleAgent {
		if user.APIKey != "" {
			resp.APIKey = &user.APIKey
		}
		resp.IsSystem = &user.IsSystem
		resp.OwnerID = &user.OwnerID

		if user.IsSystem {
			ownerName := "system"
			resp.OwnerName = &ownerName
		} else if user.OwnerID > 0 {
			if user.Owner != nil && user.Owner.Name != "" {
				ownerName := user.Owner.Name
				resp.OwnerName = &ownerName
			} else {
				var owner model.User
				if err := database.DB.Select("name").First(&owner, user.OwnerID).Error; err == nil {
					ownerName := owner.Name
					resp.OwnerName = &ownerName
				}
			}
		}
	}

	return resp
}

// ToUserProfileResponse 转换 User 模型为资料响应结构
func ToUserProfileResponse(user *model.User, stats UserStats) *UserProfileResponse {
	if user == nil {
		return nil
	}

	resp := &UserProfileResponse{
		ID:     user.ID,
		Name:   user.Name,   // 显示名称（所有人都有）
		Handle: user.Handle, // 登录账号（仅真人，Agent 为 nil）
		Role:   string(user.Role),
		Avatar: user.Avatar,
		Stats:  stats,
	}

	// Agent 专属字段：仅当角色为 Agent 时返回
	if user.Role == model.RoleAgent {
		if user.APIKey != "" {
			resp.APIKey = &user.APIKey
		}
		resp.IsSystem = &user.IsSystem
		resp.OwnerID = &user.OwnerID

		if user.IsSystem {
			ownerName := "system"
			resp.OwnerName = &ownerName
		} else if user.OwnerID > 0 {
			if user.Owner != nil && user.Owner.Name != "" {
				ownerName := user.Owner.Name
				resp.OwnerName = &ownerName
			} else {
				var owner model.User
				if err := database.DB.Select("name").First(&owner, user.OwnerID).Error; err == nil {
					ownerName := owner.Name
					resp.OwnerName = &ownerName
				}
			}
		}
	}

	return resp
}

// ToQuestionResponse 转换 Question 模型为响应结构
func ToQuestionResponse(question *model.Question, stats *service.ObjectStats) *QuestionResponse {
	if question == nil {
		return nil
	}

	resp := &QuestionResponse{
		ID:        question.ID,
		Title:     question.Title,
		Content:   question.Content,
		Type:      question.Type,
		UserID:    question.UserID,
		CreatedAt: question.CreatedAt,
		UpdatedAt: question.UpdatedAt,
	}

	if question.User.ID != 0 {
		resp.User = ToUserResponse(&question.User)
	}

	if len(question.Tags) > 0 {
		resp.Tags = make([]TagResponse, len(question.Tags))
		for i, tag := range question.Tags {
			resp.Tags[i] = *ToTagResponse(&tag)
		}
	}

	if stats != nil {
		resp.Stats = &ObjectStats{
			LikeCount:    stats.LikeCount,
			DislikeCount: stats.DislikeCount,
			CommentCount: stats.CommentCount,
		}
	}

	return resp
}

// ToAnswerResponse 转换 Answer 模型为响应结构
func ToAnswerResponse(answer *model.Answer, stats *service.ObjectStats) *AnswerResponse {
	if answer == nil {
		return nil
	}

	resp := &AnswerResponse{
		ID:         answer.ID,
		Content:    answer.Content,
		QuestionID: answer.QuestionID,
		UserID:     answer.UserID,
		CreatedAt:  answer.CreatedAt,
		UpdatedAt:  answer.UpdatedAt,
	}

	if answer.User.ID != 0 {
		resp.User = ToUserResponse(&answer.User)
	}

	if stats != nil {
		resp.Stats = &ObjectStats{
			LikeCount:    stats.LikeCount,
			DislikeCount: stats.DislikeCount,
			CommentCount: stats.CommentCount,
		}
	}

	return resp
}

// ToAnswerWithQuestionResponse 转换 Answer 模型为带问题信息的响应结构
func ToAnswerWithQuestionResponse(answer *model.Answer, answerStats *service.ObjectStats, questionStats *service.ObjectStats) *AnswerWithQuestionResponse {
	if answer == nil {
		return nil
	}

	resp := &AnswerWithQuestionResponse{
		ID:         answer.ID,
		Content:    answer.Content,
		QuestionID: answer.QuestionID,
		UserID:     answer.UserID,
		CreatedAt:  answer.CreatedAt,
		UpdatedAt:  answer.UpdatedAt,
	}

	if answer.User.ID != 0 {
		resp.User = ToUserResponse(&answer.User)
	}

	if answer.Question.ID != 0 {
		resp.Question = ToQuestionResponse(&answer.Question, questionStats)
	}

	if answerStats != nil {
		resp.Stats = &ObjectStats{
			LikeCount:    answerStats.LikeCount,
			DislikeCount: answerStats.DislikeCount,
			CommentCount: answerStats.CommentCount,
		}
	}

	return resp
}

// ToCommentResponse 转换 Comment 模型为响应结构
func ToCommentResponse(comment *model.Comment, stats *service.ObjectStats) *CommentResponse {
	if comment == nil {
		return nil
	}

	resp := &CommentResponse{
		ID:        comment.ID,
		Content:   comment.Content,
		AnswerID:  comment.AnswerID,
		UserID:    comment.UserID,
		RootID:    comment.RootID,
		ParentID:  comment.ParentID,
		CreatedAt: comment.CreatedAt,
		UpdatedAt: comment.UpdatedAt,
	}

	if comment.User.ID != 0 {
		resp.User = ToUserResponse(&comment.User)
	}

	if stats != nil {
		resp.Stats = &ObjectStats{
			LikeCount:    stats.LikeCount,
			DislikeCount: stats.DislikeCount,
			CommentCount: stats.CommentCount,
		}
	}

	return resp
}

// ToCommentResponseWithParent 转换 Comment 模型为响应结构（包含父评论用户信息）
func ToCommentResponseWithParent(comment *model.Comment, parentUser *model.User, stats *service.ObjectStats) *CommentResponse {
	resp := ToCommentResponse(comment, stats)
	if resp != nil && parentUser != nil && parentUser.ID != 0 {
		resp.ParentUser = ToUserResponse(parentUser)
	}
	return resp
}

// ToTagResponse 转换 Tag 模型为响应结构
func ToTagResponse(tag *model.Tag) *TagResponse {
	if tag == nil {
		return nil
	}
	return &TagResponse{
		ID:          tag.ID,
		Name:        tag.Name,
		Description: tag.Description,
		Icon:        tag.Icon,
	}
}

// ToCollectionResponse 转换 Collection 模型为响应结构
func ToCollectionResponse(collection *model.Collection) *CollectionResponse {
	if collection == nil {
		return nil
	}
	return &CollectionResponse{
		ID:        collection.ID,
		UserID:    collection.UserID,
		Name:      collection.Name,
		CreatedAt: collection.CreatedAt,
		UpdatedAt: collection.UpdatedAt,
	}
}

// ToFollowResponse 转换 Follow 模型为响应结构
func ToFollowResponse(follow *model.Follow) *FollowResponse {
	if follow == nil {
		return nil
	}
	return &FollowResponse{
		ID:         follow.ID,
		UserID:     follow.UserID,
		TargetType: follow.TargetType,
		TargetID:   follow.TargetID,
		CreatedAt:  follow.CreatedAt,
	}
}
