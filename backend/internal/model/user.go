package model

import (
	"crypto/rand"
	"encoding/hex"

	"gorm.io/gorm"
)

type UserRole string

const (
	RoleUser  UserRole = "user"
	RoleAdmin UserRole = "admin"
	RoleAgent UserRole = "agent"
)

type User struct {
	BaseModel

	// ==========================================
	// 1. 公共基础信息 (Common Fields)
	// ==========================================
	// 显示名称（所有人都有的，如："张三" 或 "不正经观察员"）
	Name string `gorm:"size:100;not null" json:"name"`

	// 头像 URL 或 base64 data URL
	Avatar string `gorm:"type:text" json:"avatar"`

	// 核心身份标识: "user", "agent" 或 "admin"
	Role UserRole `gorm:"type:varchar(20);not null;default:'user';index" json:"role"`

	// ==========================================
	// 2. 真人专属字段 (Human Only - 登录凭证)
	// ==========================================
	// 登录账号（唯一索引，Agent 此字段为 NULL）
	Handle *string `gorm:"uniqueIndex;size:50" json:"handle,omitempty"`

	// 密码哈希（Agent 此字段为 NULL）
	Password *string `json:"-"`

	// ==========================================
	// 3. Agent 专属字段 (Agent Only)
	// ==========================================
	// API Key: 用于 Python 端调用 Go 接口时的鉴权 (代替密码)
	APIKey string `gorm:"size:64;index" json:"api_key,omitempty"`

	// 归属权:
	// - 如果是用户创建的 Agent -> 存真人的 UserID
	// - 如果是 12 个系统官方 Agent -> 存 0
	OwnerID uint `gorm:"index;default:0" json:"owner_id"`

	// Owner 关联（Agent 专属，指向创建者）
	Owner *User `gorm:"foreignKey:OwnerID" json:"owner,omitempty"`

	// 是否为系统官方 Agent (方便前端加个"官方"认证标)
	IsSystem bool `gorm:"default:false" json:"is_system"`

	// --- 灵魂设定 (The Soul) ---

	// System Prompt: 经过 Python 优化后，真正喂给 LLM 的系统提示词
	// 比如: "# Role: 影评人\n# Style: 毒舌..."
	SystemPrompt string `gorm:"type:text" json:"-"`

	// Raw Config: 用户在前端填写的原始配置 (JSON 字符串)
	// 用于前端回显，方便用户修改。
	// 例如: {"name":"毒舌", "tags":["傲娇"], "intro":"..."}
	RawConfig string `gorm:"type:text" json:"-"`

	// Expressiveness: Agent 表达欲模式 (Agent Only)
	// 控制 Agent 的表达欲望和回复篇幅
	// 可选值: "terse"(惜字如金) | "balanced"(标准) | "verbose"(话痨) | "dynamic"(动态)
	Expressiveness string `gorm:"size:20;default:'balanced';comment:'Agent expressiveness mode: terse/balanced/verbose/dynamic'" json:"-"`
}

// BeforeCreate 在插入数据库之前自动执行
func (u *User) BeforeCreate(tx *gorm.DB) (err error) {
	if u.Role == RoleAgent {
		// Agent 的处理逻辑
		// 1. Agent 不需要 handle，保持为 nil
		u.Handle = nil
		u.Password = nil

		// 2. 自动生成 API Key
		if u.APIKey == "" {
			u.APIKey = GenerateAgentKey()
		}

		// 3. Agent 必须有 name
		if u.Name == "" {
			// 如果没提供 name，使用默认值
			u.Name = "未命名Agent"
		}
	} else {
		// 真人用户的处理逻辑
		// 如果没有设置 Name，使用 Handle 作为默认值
		if u.Name == "" && u.Handle != nil {
			u.Name = *u.Handle
		}
	}

	return
}

// GenerateAgentKey 生成一个安全的随机 API Key
// 格式: sk-agent-<32字符的16进制随机串>
func GenerateAgentKey() string {
	// 1. 定义想要多少字节的随机数 (16字节 = 32个16进制字符)
	bytes := make([]byte, 16)

	// 2. 使用 crypto/rand 读取真正的随机数 (比 math/rand 安全)
	if _, err := rand.Read(bytes); err != nil {
		// 极低概率会失败，如果失败降级处理或 panic
		return ""
	}

	// 3. 拼接前缀和编码后的字符串
	return "sk-agent-" + hex.EncodeToString(bytes)
}
