package model

import (
	"time"
)

type HotspotSource string
type HotspotStatus string

const (
	HotspotSourceZhihu HotspotSource = "zhihu"
	HotspotSourceWeibo HotspotSource = "weibo"

	HotspotStatusPending    HotspotStatus = "pending"
	HotspotStatusProcessing HotspotStatus = "processing"
	HotspotStatusCompleted  HotspotStatus = "completed"
	HotspotStatusSkipped    HotspotStatus = "skipped"
)

// Hotspot 热点主表，统一存储知乎热榜和微博热搜
type Hotspot struct {
	BaseModel

	// 来源标识
	Source   HotspotSource `gorm:"type:varchar(20);not null;uniqueIndex:idx_source_date_id,priority:1" json:"source"`
	SourceID string        `gorm:"type:varchar(100);uniqueIndex:idx_source_date_id,priority:2" json:"source_id"`

	// 热点内容
	Title   string `gorm:"type:varchar(500);not null" json:"title"`
	Content string `gorm:"type:text" json:"content"`
	URL     string `gorm:"type:varchar(1000)" json:"url"`

	// 排名与热度
	Rank int    `gorm:"default:0" json:"rank"`
	Heat string `gorm:"type:varchar(100)" json:"heat"`

	// 处理状态
	Status     HotspotStatus `gorm:"type:varchar(20);not null;default:'pending';index" json:"status"`
	QuestionID *uint         `gorm:"index" json:"question_id"`

	// 时间
	HotspotDate time.Time  `gorm:"type:date;not null;index;uniqueIndex:idx_source_date_id,priority:3" json:"hotspot_date"`
	CrawledAt   time.Time  `gorm:"not null;default:CURRENT_TIMESTAMP" json:"crawled_at"`
	ProcessedAt *time.Time `json:"processed_at"`

	// 关联知乎原始回答
	Answers []HotspotAnswer `gorm:"foreignKey:HotspotID" json:"answers,omitempty"`
}

// HotspotAnswer 知乎原始回答，用于「知乎原答案 vs Agent 回答」对比展示
type HotspotAnswer struct {
	BaseModel

	HotspotID uint `gorm:"not null;uniqueIndex:idx_hotspot_answer;index" json:"hotspot_id"`

	// 回答内容（保留原始 HTML，供前端渲染）
	AuthorName   string `gorm:"type:varchar(200);not null" json:"author_name"`
	AuthorURL    string `gorm:"type:varchar(1000)" json:"author_url"`
	Content      string `gorm:"type:text;not null" json:"content"`
	UpvoteCount  int    `gorm:"default:0" json:"upvote_count"`
	CommentCount int    `gorm:"default:0" json:"comment_count"`

	// 排名与来源标识
	Rank          int    `gorm:"default:0" json:"rank"`
	ZhihuAnswerID string `gorm:"type:varchar(100);uniqueIndex:idx_hotspot_answer" json:"zhihu_answer_id"`
}
