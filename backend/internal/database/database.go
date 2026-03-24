package database

import (
	"log"
	"os"
	"time"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"backend/internal/model"
)

var DB *gorm.DB

func Migrate() {
	// 手动迁移：将 avatar 列从 varchar(500) 改为 text，兼容历史头像数据
	DB.Exec("ALTER TABLE users ALTER COLUMN avatar TYPE text")
	DB.Exec("DROP INDEX IF EXISTS idx_source_id")
	DB.Exec("DROP INDEX IF EXISTS idx_hotspots_source_id")

	// 先迁移无外键依赖的表，避免 User 自引用外键阻断整个迁移
	DB.AutoMigrate(
		&model.Hotspot{}, &model.HotspotAnswer{},
	)
	// 禁用外键约束后迁移 User 及其关联表
	DB.DisableForeignKeyConstraintWhenMigrating = true
	DB.AutoMigrate(
		&model.User{}, &model.Tag{}, &model.Question{}, &model.Answer{}, &model.Comment{}, &model.Like{},
		&model.Follow{}, &model.Collection{}, &model.CollectionItem{}, &model.UserLoginEvent{},
	)
	DB.DisableForeignKeyConstraintWhenMigrating = false
}

func Init() {
	dsn := os.Getenv("DB_DSN")
	if dsn == "" {
		log.Fatal("错误: 未设置 DB_DSN 环境变量")
	}

	var err error

	// 根据环境变量设置 GORM 日志级别
	logLevel := logger.Warn // 默认为 Warn
	gormLogLevel := os.Getenv("GORM_LOG_LEVEL")
	switch gormLogLevel {
	case "silent":
		logLevel = logger.Silent
	case "error":
		logLevel = logger.Error
	case "warn":
		logLevel = logger.Warn
	case "info":
		logLevel = logger.Info
	}

	config := &gorm.Config{
		Logger: logger.Default.LogMode(logLevel),
	}

	DB, err = gorm.Open(postgres.Open(dsn), config)
	if err != nil {
		log.Fatal("PostgreSQL 连接失败: ", err)
	}

	sqlDB, _ := DB.DB()
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)
	sqlDB.SetConnMaxLifetime(time.Hour)

	log.Println("PostgreSQL 连接成功！")
}
