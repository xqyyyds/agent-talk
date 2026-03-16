package model

// UserLoginEvent 记录用户登录事件，用于后台统计最近登录量
// 仅记录真人用户（user/admin）的登录，不记录 agent。
type UserLoginEvent struct {
	BaseModel
	UserID uint   `gorm:"index;not null" json:"user_id"`
	Handle string `gorm:"size:100" json:"handle"`
	IP     string `gorm:"size:64" json:"ip"`
}
