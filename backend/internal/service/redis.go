package service

import (
	"backend/internal/database"
	"backend/internal/model"
	"context"
	"embed"
	"fmt"
	"strconv"

	"github.com/redis/go-redis/v9"
)

//go:embed lua/*.lua
var luaFS embed.FS

var scriptUpdateState *redis.Script

const (
	ActionCancel  = 0
	ActionLike    = 1
	ActionDislike = 2
)

func init() {
	src, err := luaFS.ReadFile("lua/update_state.lua")
	if err != nil {
		panic("failed to load lua/update_state.lua: " + err.Error())
	}
	scriptUpdateState = redis.NewScript(string(src))
}

// 点赞（用户）
func keyUserLike(uid uint, t model.TargetType) string {
	return fmt.Sprintf("ulike:%s:%d", t.String(), uid)
}

// 点赞（对象）
func keyObjLike(objID uint, t model.TargetType) string {
	return fmt.Sprintf("plike:%s:%d", t.String(), objID)
}

// 点踩（用户）
func keyUserDislike(uid uint, t model.TargetType) string {
	return fmt.Sprintf("udislike:%s:%d", t.String(), uid)
}

// 点踩（对象）
func keyObjDislike(objID uint, t model.TargetType) string {
	return fmt.Sprintf("pdislike:%s:%d", t.String(), objID)
}

// 生成 Stats Key
func keyStats(objID uint, t model.TargetType) string {
	return fmt.Sprintf("stats:%s:%d", t.String(), objID)
}

// ExecuteAction 执行动作：点赞 / 点踩 / 取消
// action: 1=Like, 2=Dislike, 0=Cancel
func ExecuteAction(ctx context.Context, uid uint, objType model.TargetType, objID uint, action int) error {
	keys := []string{
		keyUserLike(uid, objType),     // KEYS[1]
		keyObjLike(objID, objType),    // KEYS[2]
		keyUserDislike(uid, objType),  // KEYS[3]
		keyObjDislike(objID, objType), // KEYS[4]
		keyStats(objID, objType),      // KEYS[5] -> 新增 stats Key
	}

	argv := []any{
		objID,  // ARGV[1]
		uid,    // ARGV[2]
		action, // ARGV[3]
	}

	if err := scriptUpdateState.Run(ctx, database.RedisClient, keys, argv...).Err(); err != nil {
		return fmt.Errorf("redis lua error: %w", err)
	}

	// 同步更新数据库 Like 表
	// 数据库中的 value: 1=点赞, -1=点踩
	var dbValue int
	if action == ActionLike {
		dbValue = 1
	} else if action == ActionDislike {
		dbValue = -1
	}

	// 检查是否已存在记录
	var existingLike model.Like
	err := database.DB.Where("user_id = ? AND target_type = ? AND target_id = ?", uid, objType, objID).First(&existingLike).Error

	if action == ActionCancel {
		// 取消：删除记录
		if err == nil {
			database.DB.Delete(&existingLike)
		}
	} else {
		// 点赞或点踩
		if err == nil {
			// 记录存在，更新 value
			existingLike.Value = dbValue
			database.DB.Save(&existingLike)
		} else {
			// 记录不存在，创建新记录
			newLike := model.Like{
				UserID:     uid,
				TargetType: uint8(objType),
				TargetID:   objID,
				Value:      dbValue,
			}
			database.DB.Create(&newLike)
		}
	}

	return nil
}

// GetUserStatus 获取单个用户的状态
// 返回: 1(赞), 2(踩), 0(无)
func GetUserStatus(ctx context.Context, uid uint, objType model.TargetType, objID uint) (int, error) {
	pipe := database.RedisClient.Pipeline()

	// 检查赞
	isLikeCmd := pipe.Do(ctx, "R.GETBIT", keyUserLike(uid, objType), objID)
	// 检查踩
	isDislikeCmd := pipe.Do(ctx, "R.GETBIT", keyUserDislike(uid, objType), objID)

	if _, err := pipe.Exec(ctx); err != nil {
		return 0, err
	}

	if val, _ := isLikeCmd.Int(); val == 1 {
		return ActionLike, nil
	}
	if val, _ := isDislikeCmd.Int(); val == 1 {
		return ActionDislike, nil
	}
	return ActionCancel, nil
}

// BatchGetUserStatus 批量获取状态 (Feed流核心)
// 返回 map[objID]status (1=赞, 2=踩, 0=无)
func BatchGetUserStatus(ctx context.Context, uid uint, objType model.TargetType, objIDs []uint) (map[uint]int, error) {
	if len(objIDs) == 0 {
		return map[uint]int{}, nil
	}

	uLikeKey := keyUserLike(uid, objType)
	uDislikeKey := keyUserDislike(uid, objType)

	pipe := database.RedisClient.Pipeline()

	// 我们需要保存 cmd 的引用来解析结果
	// 结构: cmds[i] = [likeCmd, dislikeCmd]
	type pair struct {
		likeCmd    *redis.Cmd
		dislikeCmd *redis.Cmd
	}
	cmds := make([]pair, len(objIDs))

	for i, oid := range objIDs {
		cmds[i] = pair{
			likeCmd:    pipe.Do(ctx, "R.GETBIT", uLikeKey, oid),
			dislikeCmd: pipe.Do(ctx, "R.GETBIT", uDislikeKey, oid),
		}
	}

	_, err := pipe.Exec(ctx)
	if err != nil && err != redis.Nil {
		return nil, err
	}

	result := make(map[uint]int, len(objIDs))
	for i, oid := range objIDs {
		lVal, _ := cmds[i].likeCmd.Int()
		dVal, _ := cmds[i].dislikeCmd.Int()

		if lVal == 1 {
			result[oid] = ActionLike
		} else if dVal == 1 {
			result[oid] = ActionDislike
		} else {
			result[oid] = ActionCancel
		}
	}

	return result, nil
}

// 评论
func IncrCommentCount(ctx context.Context, objType model.TargetType, objID uint, delta int64) error {
	key := fmt.Sprintf("stats:%s:%d", objType.String(), objID)
	// HINCRBY stats:q:888 c 1
	return database.RedisClient.HIncrBy(ctx, key, "c", delta).Err()
}

type ObjectStats struct {
	LikeCount    int64 `json:"like_count"`
	DislikeCount int64 `json:"dislike_count"`
	CommentCount int64 `json:"comment_count"`
}

func parseInt64(s string) int64 {
	if s == "" {
		return 0
	}
	v, _ := strconv.ParseInt(s, 10, 64)
	// 确保计数器不为负数（容错机制）
	if v < 0 {
		return 0
	}
	return v
}

func BatchGetStats(ctx context.Context, objType model.TargetType, objIDs []uint) (map[uint]ObjectStats, error) {
	if len(objIDs) == 0 {
		return nil, nil
	}

	pipe := database.RedisClient.Pipeline()
	cmds := make([]*redis.MapStringStringCmd, len(objIDs))

	for i, oid := range objIDs {
		// 直接查 Hash，里面全都有：l, d, c
		statKey := keyStats(oid, objType)
		cmds[i] = pipe.HGetAll(ctx, statKey)
	}

	_, err := pipe.Exec(ctx)
	if err != nil && err != redis.Nil {
		return nil, err
	}

	result := make(map[uint]ObjectStats, len(objIDs))

	for i, oid := range objIDs {
		statsMap, _ := cmds[i].Result()

		result[oid] = ObjectStats{
			// 直接从 Hash 读，不再从 Bitmap 算
			LikeCount:    parseInt64(statsMap["l"]),
			DislikeCount: parseInt64(statsMap["d"]),
			CommentCount: parseInt64(statsMap["c"]),
		}
	}

	return result, nil
}

// ResetStats 重置指定对象的统计数据（用于修复负数等异常数据）
func ResetStats(ctx context.Context, objType model.TargetType, objID uint) error {
	statKey := keyStats(objID, objType)
	// 获取当前统计数据
	statsMap, err := database.RedisClient.HGetAll(ctx, statKey).Result()
	if err != nil && err != redis.Nil {
		return err
	}

	// 检查并重置负数
	needsUpdate := false
	for field, valStr := range statsMap {
		if val, err := strconv.ParseInt(valStr, 10, 64); err == nil && val < 0 {
			database.RedisClient.HSet(ctx, statKey, field, 0)
			needsUpdate = true
		}
	}

	// 如果没有任何字段，初始化为0
	if len(statsMap) == 0 {
		database.RedisClient.HSet(ctx, statKey, "l", 0)
		database.RedisClient.HSet(ctx, statKey, "d", 0)
		database.RedisClient.HSet(ctx, statKey, "c", 0)
	}

	if needsUpdate {
		fmt.Printf("Reset stats for %s:%d\n", objType.String(), objID)
	}

	return nil
}
