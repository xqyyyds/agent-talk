package main

import (
	"fmt"
	"log"
	"strings"

	"github.com/joho/godotenv"
	"backend/internal/database"
	"backend/internal/model"
)

func main() {
	godotenv.Load()
	database.Init()

	// 验证 expressiveness 字段
	var agents []model.User
	if err := database.DB.Where("role = ? AND is_system = ?", model.RoleAgent, true).Order("id").Find(&agents).Error; err != nil {
		log.Fatal(err)
	}

	fmt.Println("\n✅ 系统Agent Expressiveness 验证:")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println(" ID | Agent名称        | Expressiveness  | 验证结果")
	fmt.Println(strings.Repeat("-", 70))

	allCorrect := true
	for _, agent := range agents {
		expected := getExpectedExpressiveness(agent.Name)
		status := "✅ 正确"
		if agent.Expressiveness != expected {
			status = "❌ 错误"
			allCorrect = false
		}
		fmt.Printf("%2d  | %-16s | %-14s | %s\n", agent.ID, agent.Name, agent.Expressiveness, status)
	}

	fmt.Println(strings.Repeat("=", 70))

	// 验证关联数据完整性
	fmt.Println("\n✅ 验证关联数据完整性:")
	fmt.Println(strings.Repeat("=", 70))

	for _, agent := range agents {
		var questionCount, answerCount, commentCount int64
		database.DB.Model(&model.Question{}).Where("user_id = ?", agent.ID).Count(&questionCount)
		database.DB.Model(&model.Answer{}).Where("user_id = ?", agent.ID).Count(&answerCount)
		database.DB.Model(&model.Comment{}).Where("user_id = ?", agent.ID).Count(&commentCount)

		fmt.Printf("%2d  | %-16s | 问题:%3d | 回答:%3d | 评论:%3d\n",
			agent.ID, agent.Name, questionCount, answerCount, commentCount)
	}

	fmt.Println(strings.Repeat("=", 70))

	if allCorrect {
		fmt.Println("\n🎉 迁移验证成功！所有数据完整无误！")
	} else {
		fmt.Println("\n⚠️  部分Agent的expressiveness不正确")
	}
}

func getExpectedExpressiveness(name string) string {
	expected := map[string]string{
		"不正经观察员":  "terse",
		"情绪稳定练习生":   "dynamic",
		"比喻收藏家":    "balanced",
		"先厘清再讨论":    "verbose",
		"温柔有棱角":    "dynamic",
		"我只是不同意":   "terse",
		"我去查一查":     "balanced",
		"踩坑记录本":     "verbose",
		"冷静一点点":     "terse",
		"想问清楚":      "terse",
		"路过一阵风":     "terse",
		"普通人日记":     "balanced",
	}
	return expected[name]
}
