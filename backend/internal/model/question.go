package model

import (
	"time"
)

type TargetType uint8

const (
	TargetTypeQuestion = 1
	TargetTypeAnswer   = 2
	TargetTypeComment  = 3
	TargetTypeUser     = 4
)

func (t TargetType) String() string {
	switch t {
	case TargetTypeQuestion:
		return "q"
	case TargetTypeAnswer:
		return "a"
	case TargetTypeComment:
		return "c"
	case TargetTypeUser:
		return "u"
	default:
		return "unknown"
	}
}

type Tag struct {
	BaseModel
	Name        string `gorm:"type:varchar(50);uniqueIndex;not null" json:"name"`
	Description string `gorm:"type:text" json:"description"`
	Icon        string `gorm:"type:text" json:"icon"`

	Questions []Question `gorm:"many2many:question_tags;" json:"-"`
}

type Question struct {
	BaseModel

	Title   string `gorm:"type:varchar(255);not null;index" json:"title"`
	Content string `gorm:"type:text" json:"content"`
	Type    string `gorm:"type:varchar(20);not null;default:'qa';index" json:"type"`

	UserID uint `gorm:"index;not null" json:"user_id"`
	User   User `json:"user"`

	Tags []Tag `gorm:"many2many:question_tags;" json:"tags,omitempty"`
}

type Answer struct {
	BaseModel
	Content string `gorm:"type:text;not null" json:"content"`

	QuestionID uint     `gorm:"index;not null" json:"question_id"`
	Question   Question `json:"-"`

	UserID uint `gorm:"index;not null" json:"user_id"`
	User   User `json:"user"`
}

type Comment struct {
	BaseModel

	UserID uint `gorm:"index;not null" json:"user_id"`
	User   User `json:"user"`

	AnswerID uint `gorm:"index;not null" json:"answer_id"`

	Content string `gorm:"type:text;not null" json:"content"`

	RootID   uint `gorm:"index;default:0" json:"root_id"`
	ParentID uint `gorm:"index;default:0" json:"parent_id"`
}

type Like struct {
	BaseModel
	UserID uint `gorm:"uniqueIndex:idx_user_target;not null" json:"user_id"`

	TargetType uint8 `gorm:"uniqueIndex:idx_user_target;not null" json:"target_type"` // "question", "answer", "comment"
	TargetID   uint  `gorm:"uniqueIndex:idx_user_target;not null" json:"target_id"`

	Value int `gorm:"not null;default:1" json:"value"` // 1 表示点赞，-1 表示点踩
}

type Follow struct {
	ID        uint `gorm:"primarykey"`
	CreatedAt time.Time
	UpdatedAt time.Time

	UserID     uint  `gorm:"uniqueIndex:idx_follow" json:"user_id"`
	TargetType uint8 `gorm:"uniqueIndex:idx_follow;not null" json:"target_type"` // "question", "user"
	TargetID   uint  `gorm:"uniqueIndex:idx_follow" json:"target_id"`
}

// 收藏夹
type Collection struct {
	BaseModel
	UserID uint   `gorm:"index;not null" json:"user_id"`
	Name   string `gorm:"type:varchar(50);not null" json:"name"`
}

type CollectionItem struct {
	BaseModel
	CollectionID uint       `gorm:"index;not null" json:"collection_id"`
	Collection   Collection `json:"-"`

	AnswerID uint `gorm:"index;not null" json:"answer_id"`
}
