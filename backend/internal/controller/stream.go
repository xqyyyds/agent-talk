package controller

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"sync/atomic"
	"time"

	"backend/internal/database"

	"github.com/gin-gonic/gin"
)

var allowedStreamChannels = map[string]struct{}{
	"hotspots":  {},
	"questions": {},
	"debates":   {},
	"agents":    {},
	"online":    {},
}

var lastOnlinePublishUnix int64

type streamEvent struct {
	Event string      `json:"event"`
	Data  interface{} `json:"data"`
	At    string      `json:"at"`
}

type publishStreamEventRequest struct {
	Channel string      `json:"channel" binding:"required"`
	Event   string      `json:"event" binding:"required"`
	Data    interface{} `json:"data"`
}

func streamTopic(channel string) string {
	return "stream:" + channel
}

func normalizeChannel(channel string) string {
	return strings.TrimSpace(strings.ToLower(channel))
}

func isAllowedChannel(channel string) bool {
	_, ok := allowedStreamChannels[channel]
	return ok
}

func publishStreamEvent(channel, event string, data interface{}) {
	channel = normalizeChannel(channel)
	if !isAllowedChannel(channel) {
		return
	}
	payload, err := json.Marshal(streamEvent{
		Event: event,
		Data:  data,
		At:    time.Now().UTC().Format(time.RFC3339),
	})
	if err != nil {
		return
	}
	_ = database.RedisClient.Publish(context.Background(), streamTopic(channel), string(payload)).Err()
}

// publishOnlineMetricEvent emits at most once every 5 seconds to avoid flooding.
func publishOnlineMetricEvent(onlineWindowSeconds int) {
	now := time.Now().Unix()
	prev := atomic.LoadInt64(&lastOnlinePublishUnix)
	if now-prev < 5 {
		return
	}
	if !atomic.CompareAndSwapInt64(&lastOnlinePublishUnix, prev, now) {
		return
	}

	publishStreamEvent("online", "online_heartbeat", gin.H{
		"online_window_seconds": onlineWindowSeconds,
		"ts":                    now,
	})
}

// StreamEvents streams Redis pub/sub events to frontend via SSE.
func StreamEvents(c *gin.Context) {
	channel := normalizeChannel(c.Param("channel"))
	if !isAllowedChannel(channel) {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "invalid channel",
		})
		return
	}

	c.Writer.Header().Set("Content-Type", "text/event-stream")
	c.Writer.Header().Set("Cache-Control", "no-cache")
	c.Writer.Header().Set("Connection", "keep-alive")
	c.Writer.Header().Set("X-Accel-Buffering", "no")

	ctx := c.Request.Context()
	pubsub := database.RedisClient.Subscribe(ctx, streamTopic(channel))
	defer pubsub.Close()

	// Ping on connect so client can mark channel alive quickly.
	c.SSEvent("ping", gin.H{
		"channel": channel,
		"at":      time.Now().UTC().Format(time.RFC3339),
	})
	c.Writer.Flush()

	messageChan := pubsub.Channel()
	keepAliveTicker := time.NewTicker(20 * time.Second)
	defer keepAliveTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case msg := <-messageChan:
			if msg == nil {
				continue
			}
			c.SSEvent("message", msg.Payload)
			c.Writer.Flush()
		case <-keepAliveTicker.C:
			c.SSEvent("ping", gin.H{
				"channel": channel,
				"at":      time.Now().UTC().Format(time.RFC3339),
			})
			c.Writer.Flush()
		}
	}
}

// InternalPublishStreamEvent allows trusted internal services to publish stream events.
func InternalPublishStreamEvent(c *gin.Context) {
	var req publishStreamEventRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	channel := normalizeChannel(req.Channel)
	if !isAllowedChannel(channel) {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "invalid channel"})
		return
	}

	publishStreamEvent(channel, strings.TrimSpace(req.Event), req.Data)
	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "published",
	})
}
