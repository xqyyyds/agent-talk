package controller

import (
	"backend/internal/database"
	"backend/internal/middleware"
	"backend/internal/model"
	"context"

	"github.com/gin-gonic/gin"
)

func getOptionalUserID(c *gin.Context) (uint, bool) {
	userID, exists := c.Get(middleware.IdentityKey)
	if !exists {
		return 0, false
	}

	switch v := userID.(type) {
	case float64:
		if v <= 0 {
			return 0, false
		}
		return uint(v), true
	case uint:
		if v == 0 {
			return 0, false
		}
		return v, true
	case int:
		if v <= 0 {
			return 0, false
		}
		return uint(v), true
	case int64:
		if v <= 0 {
			return 0, false
		}
		return uint(v), true
	case float32:
		if v <= 0 {
			return 0, false
		}
		return uint(v), true
	default:
		return 0, false
	}
}

func getFollowStatus(ctx context.Context, userID uint, targetType uint8, targetID uint) (bool, error) {
	if userID == 0 || targetID == 0 {
		return false, nil
	}
	var count int64
	if err := database.DB.WithContext(ctx).Model(&model.Follow{}).Where(
		"user_id = ? AND target_type = ? AND target_id = ?",
		userID, targetType, targetID,
	).Count(&count).Error; err != nil {
		return false, err
	}
	return count > 0, nil
}

func getFollowStatusMap(ctx context.Context, userID uint, targetType uint8, targetIDs []uint) (map[uint]bool, error) {
	if userID == 0 || len(targetIDs) == 0 {
		return map[uint]bool{}, nil
	}

	var follows []model.Follow
	if err := database.DB.WithContext(ctx).Where(
		"user_id = ? AND target_type = ? AND target_id IN ?",
		userID, targetType, targetIDs,
	).Find(&follows).Error; err != nil {
		return nil, err
	}

	result := make(map[uint]bool, len(targetIDs))
	for _, f := range follows {
		result[f.TargetID] = true
	}
	return result, nil
}
