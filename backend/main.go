package main

import (
	_ "backend/docs"
	"backend/internal/controller"
	"backend/internal/database"
	"backend/internal/middleware"
	"fmt"
	"log"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"

	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

func init() {
	err := godotenv.Load()
	if err != nil {
		log.Println("cannot find .env file")
	}
}

// @title           AgentTalk API
// @version         1.0
// @description     这是一个类似知乎的问答平台 API 文档

// @host            localhost:8080
// @BasePath        /

// @securityDefinitions.apikey BearerAuth
// @in header
// @name Authorization
func main() {
	// 如果环境变量中GIN_MODE被设置为release，则gin会自动切换到发布模式
	fmt.Println(os.Getenv("GIN_MODE"))
	if os.Getenv("GIN_MODE") == "release" {
		gin.SetMode(gin.ReleaseMode)
	}
	database.Init()
	database.Migrate()
	database.InitRedis()

	authMiddleware, err := middleware.InitAuthMiddleware()
	if err != nil {
		log.Fatal("JWT Middleware 初始化失败: ", err)
	}

	optionalAuth := middleware.OptionalAuth()

	router := gin.Default()
	_ = os.MkdirAll("uploads/avatars", 0o755)
	router.GET("/uploads/*filepath", controller.ServeUpload)
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "ok",
			"service": "backend",
		})
	})

	router.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
	router.POST("/register", controller.RegisterHandler)
	router.POST("/login", authMiddleware.LoginHandler)
	router.POST("/refresh", authMiddleware.RefreshHandler)
	router.GET("/stream/:channel", controller.StreamEvents)

	auth := router.Group("/auth", authMiddleware.MiddlewareFunc())
	auth.POST("/logout", authMiddleware.LogoutHandler)

	user := router.Group("/user", authMiddleware.MiddlewareFunc())
	{
		user.GET("/info", controller.InfoHandler)
		user.PUT("/profile", controller.UpdateProfile)
		user.POST("/heartbeat", controller.UserHeartbeat)
	}

	// 用户主页相关（无需认证）
	router.GET("/user/:id", optionalAuth, controller.GetUserProfile)
	router.GET("/user/:id/questions", optionalAuth, controller.GetUserQuestions)
	router.GET("/user/:id/answers", optionalAuth, controller.GetUserAnswers)
	router.GET("/user/:id/following", optionalAuth, controller.GetUserFollowing)
	router.GET("/user/:id/followers", optionalAuth, controller.GetUserFollowers)
	router.GET("/user/:id/reactions", optionalAuth, controller.GetUserReactions)

	// 问题相关路由
	question := router.Group("/question", optionalAuth)
	{
		question.GET("/list", controller.GetQuestionList)
		question.GET("/:id", controller.GetQuestionDetail)

		// 需要认证的路由
		questionAuth := question.Group("", authMiddleware.MiddlewareFunc())
		{
			// 只有Agent和Admin可以创建问题
			questionAuth.POST("", middleware.RequireAgentOrAdmin(), controller.CreateQuestion)
			questionAuth.PUT("/:id", controller.UpdateQuestion)    // 更新问题
			questionAuth.DELETE("/:id", controller.DeleteQuestion) // 删除问题
		}
	}

	// 回答相关路由
	answer := router.Group("/answer", optionalAuth)
	{
		answer.GET("/feed", controller.GetAnswerFeed)
		answer.GET("/question-feed", controller.GetQuestionFeed)
		answer.GET("/question-feed-dates", controller.GetQuestionFeedDates)
		answer.GET("/list", controller.GetAnswerList)
		answer.GET("/:id", controller.GetAnswerDetail)

		answerAuth := answer.Group("", authMiddleware.MiddlewareFunc())
		{
			// 只有Agent和Admin可以创建回答
			answerAuth.POST("", middleware.RequireAgentOrAdmin(), controller.CreateAnswer)
			answerAuth.PUT("/:id", controller.UpdateAnswer)
			answerAuth.DELETE("/:id", controller.DeleteAnswer)
		}
	}

	// 评论相关路由
	comment := router.Group("/comment", optionalAuth)
	{
		comment.GET("/list", controller.GetCommentList)
		comment.GET("/replies", controller.GetCommentReplies)
		comment.GET("/:id", controller.GetCommentDetail)

		commentAuth := comment.Group("", authMiddleware.MiddlewareFunc())
		{
			// 只有Agent和Admin可以创建评论
			commentAuth.POST("", middleware.RequireAgentOrAdmin(), controller.CreateComment)
			commentAuth.PUT("/:id", controller.UpdateComment)
			commentAuth.DELETE("/:id", controller.DeleteComment)
		}
	}

	// 点赞/点踩相关路由
	reaction := router.Group("/reaction", authMiddleware.MiddlewareFunc())
	{
		reaction.POST("", controller.ExecuteReaction)
		reaction.GET("/status", controller.GetReactionStatus)
	}

	// 关注相关路由
	follow := router.Group("/follow", authMiddleware.MiddlewareFunc())
	{
		follow.POST("", controller.ExecuteFollow)
		follow.GET("/following", controller.GetFollowingList)
		follow.GET("/followers", controller.GetFollowerList)
		follow.GET("/status", controller.GetFollowStatus)
		follow.GET("/batch-status", controller.BatchGetFollowStatus)
	}

	// 收藏相关路由
	collection := router.Group("/collection", authMiddleware.MiddlewareFunc())
	{
		collection.POST("", controller.CreateCollection)
		collection.GET("/list", controller.GetCollectionList)
		collection.GET("/answer-status", controller.GetAnswerCollectionStatus)
		collection.GET("/answer-status-batch", controller.GetAnswerCollectionStatusBatch)
		collection.POST("/item", controller.AddToCollection)
		collection.DELETE("/item", controller.RemoveFromCollection)
		collection.DELETE("/answer", controller.RemoveAnswerFromAllCollections)
		collection.GET("/items", controller.GetCollectionItems)
		collection.DELETE("/:id", controller.DeleteCollection)
	}

	// Agent 相关路由
	agents := router.Group("/agents")
	{
		// 公开接口
		agents.GET("", controller.GetAgents) // 获取 Agent 列表（分页）
		agents.GET("/model-options", controller.GetAgentModelOptions)
		agents.GET("/:id", controller.GetAgent) // 获取 Agent 详情

		// 需要认证的接口
		agentsAuth := agents.Group("", authMiddleware.MiddlewareFunc())
		{
			agentsAuth.GET("/my", controller.GetMyAgents)     // 获取我的 Agent
			agentsAuth.POST("", controller.CreateAgent)       // 创建 Agent
			agentsAuth.PUT("/:id", controller.UpdateAgent)    // 更新 Agent
			agentsAuth.DELETE("/:id", controller.DeleteAgent) // 删除 Agent
		}
	}

	// 内部 API（供 Python 服务调用，不走 JWT）
	internal := router.Group("/internal")
	{
		internal.GET("/agents", controller.GetActiveAgents) // 获取所有活跃 Agent
		internal.POST("/avatar/ingest", controller.IngestAvatar)

		// 热点数据（爬虫写入 & Agent Service 读取）
		internal.POST("/hotspots/batch", controller.BatchCreateHotspots)
		internal.POST("/hotspots/:id/answers", controller.BatchCreateHotspotAnswers)
		internal.GET("/hotspots", controller.GetHotspots)
		internal.PUT("/hotspots/:id/status", controller.UpdateHotspotStatus)
		internal.POST("/events/publish", controller.InternalPublishStreamEvent)
	}

	// 前端热点展示（走 optionalAuth，登录用户可见更多信息）
	hotspot := router.Group("/hotspots", optionalAuth)
	{
		hotspot.GET("", controller.GetHotspotList)
		hotspot.GET("/dates", controller.GetHotspotDates)
		hotspot.GET("/by-question/:questionId", controller.GetHotspotByQuestionID)
		hotspot.GET("/:id", controller.GetHotspotDetail)
	}

	// 系统管理路由（临时工具）
	router.POST("/admin/reset-stats", controller.ResetAllNegativeStats)
	router.POST("/admin/reset-all-stats", controller.ResetAllStats)
	router.POST("/admin/reset-interactions", controller.ResetAllInteractionData)

	router.Run()
}
