package database

import (
	"context"
	"os"

	"github.com/redis/go-redis/v9"
)

var RedisClient *redis.Client
var ctx = context.Background()

func InitRedis() {
	redisURL := os.Getenv("REDIS_URL")
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		panic("Failed to parse Redis URL: " + err.Error())
	}
	RedisClient = redis.NewClient(opt)
	err = RedisClient.Ping(ctx).Err()
	if err != nil {
		panic("Failed to connect to Redis: " + err.Error())
	}
}
