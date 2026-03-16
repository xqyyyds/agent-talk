package middleware

import (
	"fmt"
	"os"
	"time"

	"backend/internal/database"
	"backend/internal/model"

	"golang.org/x/crypto/bcrypt"

	jwt "github.com/appleboy/gin-jwt/v2"
	"github.com/gin-gonic/gin"
)

const IdentityKey = "user_id"

type LoginRequest struct {
	Handle   string `form:"handle" json:"handle" binding:"required"`
	Password string `form:"password" json:"password" binding:"required"`
}

func InitAuthMiddleware() (*jwt.GinJWTMiddleware, error) {
	authMiddleware, err := jwt.New(&jwt.GinJWTMiddleware{
		Realm:       "my_zone",
		Key:         []byte(os.Getenv("JWT_SECRET_KEY")),
		Timeout:     time.Hour * 24,
		MaxRefresh:  time.Hour * 24 * 7,
		IdentityKey: IdentityKey,

		PayloadFunc: func(data any) jwt.MapClaims {
			if v, ok := data.(*model.User); ok {
				return jwt.MapClaims{
					IdentityKey: v.ID,
					"role":      v.Role,
				}
			}
			return jwt.MapClaims{}
		},

		IdentityHandler: func(c *gin.Context) any {
			claims := jwt.ExtractClaims(c)
			c.Set(IdentityKey, uint(claims[IdentityKey].(float64)))
			c.Set("role", claims["role"].(string))
			return claims[IdentityKey]
		},

		Authenticator: func(c *gin.Context) (any, error) {
			var loginVals LoginRequest
			if err := c.ShouldBind(&loginVals); err != nil {
				return "", jwt.ErrMissingLoginValues
			}

			var user model.User
			result := database.DB.Where("handle = ?", loginVals.Handle).First(&user)
			if result.Error != nil {
				return nil, jwt.ErrFailedAuthentication
			}

			// Agent 不能通过 handle/password 登录
			if user.Role == model.RoleAgent || user.Password == nil {
				return nil, jwt.ErrFailedAuthentication
			}

			err := bcrypt.CompareHashAndPassword([]byte(*user.Password), []byte(loginVals.Password))
			if err != nil {
				return nil, jwt.ErrFailedAuthentication
			}

			loginEvent := model.UserLoginEvent{
				UserID: user.ID,
				Handle: loginVals.Handle,
				IP:     c.ClientIP(),
			}
			if createErr := database.DB.Create(&loginEvent).Error; createErr != nil {
				fmt.Printf("[AUTH WARN] failed to create login event for user %d: %v\n", user.ID, createErr)
			}

			return &user, nil
		},

		// 自定义未授权响应
		Unauthorized: func(c *gin.Context, code int, message string) {
			// 打印调试信息
			authHeader := c.GetHeader("Authorization")
			fmt.Printf("[AUTH DEBUG] 401 Error - URL: %s, Message: %s, Auth Header: '%s'\n", c.Request.URL.Path, message, authHeader)
			c.JSON(code, gin.H{
				"code":    code,
				"message": message,
			})
		},

		TokenLookup:   "header: Authorization, query: token, cookie: jwt",
		TokenHeadName: "Bearer",
		TimeFunc:      time.Now,
	})

	if err != nil {
		return nil, err
	}

	return authMiddleware, nil
}
