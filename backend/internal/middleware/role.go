package middleware

import (
	"net/http"
	"strings"

	"backend/internal/model"

	"github.com/gin-gonic/gin"
)

// RequireRole 创建一个中间件，检查用户是否有指定的角色
// 示例: RequireRole(model.RoleAgent, model.RoleAdmin)
func RequireRole(roles ...model.UserRole) gin.HandlerFunc {
	return func(c *gin.Context) {
		// 从context获取role（JWT中间件已设置）
		userRole, exists := c.Get("role")
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{
				"code":    http.StatusUnauthorized,
				"message": "未授权",
			})
			c.Abort()
			return
		}

		// 检查用户的角色是否在允许列表中
		roleStr := userRole.(string)
		allowed := false
		for _, r := range roles {
			if string(r) == roleStr {
				allowed = true
				break
			}
		}

		if !allowed {
			// 获取角色的显示名称
			roleNames := make([]string, len(roles))
			for i, r := range roles {
				roleNames[i] = getRoleDisplayName(r)
			}

			c.JSON(http.StatusForbidden, gin.H{
				"code":    http.StatusForbidden,
				"message": "只有" + strings.Join(roleNames, "或") + "可以执行此操作",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// RequireAgentOrAdmin 返回只允许Agent和Admin的中间件
func RequireAgentOrAdmin() gin.HandlerFunc {
	return RequireRole(model.RoleAgent, model.RoleAdmin)
}

// RequireAdmin 返回只允许Admin的中间件
func RequireAdmin() gin.HandlerFunc {
	return RequireRole(model.RoleAdmin)
}

// getRoleDisplayName 返回角色的可读名称
func getRoleDisplayName(role model.UserRole) string {
	switch role {
	case model.RoleAgent:
		return "Agent"
	case model.RoleAdmin:
		return "管理员"
	case model.RoleUser:
		return "普通用户"
	default:
		return string(role)
	}
}

// GetRoleFromContext 从context安全地提取角色
func GetRoleFromContext(c *gin.Context) (model.UserRole, bool) {
	role, exists := c.Get("role")
	if !exists {
		return "", false
	}
	return model.UserRole(role.(string)), true
}
