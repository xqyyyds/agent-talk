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

	// 查询所有系统Agent
	var agents []model.User
	if err := database.DB.Where("role = ? AND is_system = ?", model.RoleAgent, true).Order("id").Find(&agents).Error; err != nil {
		log.Fatal(err)
	}

	fmt.Println("\n✅ 系统 Agent System Prompt 验证:")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(" ID | Agent名称        | System Prompt长度 | 包含关键片段验证")
	fmt.Println(strings.Repeat("-", 80))

	for _, agent := range agents {
		sp := agent.SystemPrompt

		// 检查关键片段
		hasRole := strings.Contains(sp, "# 角色定义")
		hasMental := strings.Contains(sp, "# 核心思维模型")
		hasInteraction := strings.Contains(sp, "# 互动策略")
		hasStyle := strings.Contains(sp, "# 语言风格准则")
		hasKnowledge := strings.Contains(sp, "# 知识边界")
		hasMeta := strings.Contains(sp, "# 系统级最高指令")
		hasIdentityLock := strings.Contains(sp, "身份锁死")

		checks := []bool{hasRole, hasMental, hasInteraction, hasStyle, hasKnowledge, hasMeta, hasIdentityLock}
		allPresent := true
		for _, c := range checks {
			if !c {
				allPresent = false
				break
			}
		}

		status := "✅ 完整"
		if !allPresent {
			status = "❌ 不完整"
		}

		// 检查是否有Markdown格式要求（应该已被删除）
		hasMarkdownFormat := strings.Contains(sp, "使用标准的 Markdown 格式")
		if hasMarkdownFormat {
			status = "⚠️  包含Markdown要求（应删除）"
		}

		fmt.Printf("%2d  | %-16s | %5d 字符       | %s\n",
			agent.ID, agent.Name, len(sp), status)

		// 如果不完整，显示缺少的部分
		if !allPresent {
			missing := []string{}
			if !hasRole { missing = append(missing, "角色定义") }
			if !hasMental { missing = append(missing, "思维模型") }
			if !hasInteraction { missing = append(missing, "互动策略") }
			if !hasStyle { missing = append(missing, "语言风格") }
			if !hasKnowledge { missing = append(missing, "知识边界") }
			if !hasMeta { missing = append(missing, "系统指令") }
			if !hasIdentityLock { missing = append(missing, "身份锁死") }
			fmt.Printf("     缺少: %s\n", strings.Join(missing, ", "))
		}

		// 显示System Prompt的前100字符作为预览
		preview := sp
		if len(preview) > 100 {
			preview = preview[:100] + "..."
		}
		fmt.Printf("     预览: %s\n\n", preview)
	}

	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\n📝 验证说明:")
	fmt.Println("- 完整的 System Prompt 应包含7个主要部分")
	fmt.Println("- 不应包含 '使用标准的 Markdown 格式' 要求")
	fmt.Println("- System Prompt 由 agent_service/app/prompts/system_agents.py 定义")
	fmt.Println("  应与数据库存储的内容完全一致")
}
