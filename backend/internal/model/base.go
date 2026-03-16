package model

import (
	"time"

	"gorm.io/gorm"
)

// BaseModel 替代 gorm.Model，添加小写 JSON 标签
// gorm.Model 默认不带 json tag，导致序列化为大写 "ID"、"CreatedAt" 等
type BaseModel struct {
	ID        uint           `gorm:"primarykey" json:"id"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"deleted_at"`
}
