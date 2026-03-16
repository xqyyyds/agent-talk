package main

import (
	"fmt"
	"log"

	"github.com/joho/godotenv"

	"backend/internal/database"
	"backend/internal/model"
)

// 系统 Agent 的 expressiveness 配置映射
// 基于 agent_service/app/config/system_agent_init.py
var systemAgentExpressiveness = map[string]string{
	"不正经观察员":  "terse",
	"情绪稳定练习生": "dynamic",
	"比喻收藏家":   "balanced",
	"先厘清再讨论":  "verbose",
	"温柔有棱角":   "dynamic",
	"我只是不同意":  "terse",
	"我去查一查":   "balanced",
	"踩坑记录本":   "verbose",
	"冷静一点点":   "terse",
	"想问清楚":    "terse",
	"路过一阵风":   "terse",
	"普通人日记":   "balanced",
}

func main() {
	if err := godotenv.Load(); err != nil {
		log.Println("cannot find .env file")
	}

	database.Init()

	fmt.Println("🚀 开始迁移系统 Agent 的 expressiveness 字段...")
	fmt.Println("==================================================")

	var agents []model.User
	if err := database.DB.Where("role = ? AND is_system = ?", model.RoleAgent, true).Find(&agents).Error; err != nil {
		log.Fatal("❌ 查询系统 Agent 失败:", err)
	}

	fmt.Printf("📋 找到 %d 个系统 Agent\n", len(agents))
	if len(agents) == 0 {
		log.Fatal("❌ 没有找到系统 Agent，请先创建系统 Agent")
	}

	fmt.Println("\n📊 当前状态:")
	for _, agent := range agents {
		currentValue := agent.Expressiveness
		if currentValue == "" {
			currentValue = "(未设置)"
		}
		fmt.Printf("  ID=%d, Name=%s, CurrentExpressiveness=%s\n", agent.ID, agent.Name, currentValue)
	}

	fmt.Println("\n==================================================")
	fmt.Println("准备开始迁移...")
	fmt.Println("==================================================")

	successCount := 0
	notFoundCount := 0
	errorCount := 0

	for _, agent := range agents {
		expressiveness, exists := systemAgentExpressiveness[agent.Name]

		if !exists {
			fmt.Printf("⚠️  未找到配置: %s (ID=%d)，跳过\n", agent.Name, agent.ID)
			notFoundCount++
			continue
		}

		if err := database.DB.Model(&agent).Update("expressiveness", expressiveness).Error; err != nil {
			fmt.Printf("❌ 更新失败: %s (ID=%d) - %v\n", agent.Name, agent.ID, err)
			errorCount++
		} else {
			fmt.Printf("✅ 成功: %s (ID=%d) → %s\n", agent.Name, agent.ID, expressiveness)
			successCount++
		}
	}

	fmt.Println("\n==================================================")
	fmt.Println("📊 迁移完成统计:")
	fmt.Printf("  ✅ 成功更新: %d\n", successCount)
	fmt.Printf("  ⚠️  未找到配置: %d\n", notFoundCount)
	fmt.Printf("  ❌ 更新失败: %d\n", errorCount)
	fmt.Println("==================================================")

	if errorCount > 0 {
		log.Fatal("\n❌ 迁移过程中出现错误，请检查日志")
	}

	if successCount == 12 {
		fmt.Println("\n🎉 迁移成功完成！所有12个系统 Agent 已正确配置 expressiveness")
	} else {
		fmt.Printf("\n⚠️  迁移部分完成：%d/12 个 Agent 已更新\n", successCount)
	}
}
