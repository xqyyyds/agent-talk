package controller

import (
	"backend/internal/database"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
)

const (
	presenceSortedSetKey   = "presence:users:last_seen"
	presenceOnlineWindow   = 300
	presenceRetentionLimit = 86400
)

// UserHeartbeat records current user's activity timestamp for "online users" metric.
func UserHeartbeat(c *gin.Context) {
	userID, ok := getOptionalUserID(c)
	if !ok || userID == 0 {
		c.JSON(http.StatusUnauthorized, Response{
			Code:    401,
			Message: "未授权",
		})
		return
	}

	now := time.Now().Unix()
	member := strconv.FormatUint(uint64(userID), 10)

	if err := database.RedisClient.ZAdd(c.Request.Context(), presenceSortedSetKey, redis.Z{
		Score:  float64(now),
		Member: member,
	}).Err(); err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "heartbeat failed",
		})
		return
	}

	// Periodic cleanup for stale members.
	cutoff := now - presenceRetentionLimit
	_ = database.RedisClient.ZRemRangeByScore(
		c.Request.Context(),
		presenceSortedSetKey,
		"-inf",
		fmt.Sprintf("%d", cutoff),
	).Err()

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "ok",
		Data: gin.H{
			"online_window_seconds": presenceOnlineWindow,
		},
	})

	publishOnlineMetricEvent(presenceOnlineWindow)
}
