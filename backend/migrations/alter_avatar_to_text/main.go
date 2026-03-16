package main

import (
	"fmt"
	"log"

	"backend/internal/database"
)

func main() {
	database.Init()

	sql := `ALTER TABLE users ALTER COLUMN avatar TYPE text`
	if err := database.DB.Exec(sql).Error; err != nil {
		log.Fatalf("迁移失败: %v", err)
	}

	fmt.Println("✅ 成功将 users.avatar 字段类型从 varchar(255) 修改为 text")
}
