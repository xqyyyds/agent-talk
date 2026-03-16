package main

import (
	"fmt"
	"log"
	"strings"

	"backend/internal/database"
	"backend/internal/model"
	"github.com/joho/godotenv"
)

const enhancementMarker = "真人化表达增强（统一追加）"

const enhancementBlock = `

# 真人化表达增强（统一追加）
- 先说立场，再说理由，最后给一个可执行建议。
- 禁止使用“首先/其次/最后/综上”等模板词。
- 禁止空洞宏大叙事，优先给出生活化细节或可感知场景。
- 不要输出教科书式定义，不要一上来讲抽象概念。
- 回答里至少出现一次“我”的主观视角或亲历口吻。
- 避免重复上条回答；如果观点接近，换角度补充边界条件。
`

func main() {
	_ = godotenv.Load()
	database.Init()

	var agents []model.User
	if err := database.DB.
		Where("role = ? AND is_system = ? AND owner_id = ?", model.RoleAgent, true, 0).
		Order("id").
		Find(&agents).Error; err != nil {
		log.Fatal(err)
	}

	if len(agents) == 0 {
		fmt.Println("No system agents found (role=agent,is_system=true,owner_id=0)")
		return
	}

	updated := 0
	for _, agent := range agents {
		prompt := strings.TrimSpace(agent.SystemPrompt)
		if prompt == "" {
			continue
		}
		if strings.Contains(prompt, enhancementMarker) {
			continue
		}

		newPrompt := prompt + enhancementBlock
		if err := database.DB.Model(&model.User{}).
			Where("id = ?", agent.ID).
			Update("system_prompt", newPrompt).Error; err != nil {
			log.Printf("update failed for agent id=%d name=%s: %v", agent.ID, agent.Name, err)
			continue
		}
		updated++
		fmt.Printf("updated system agent: id=%d name=%s\n", agent.ID, agent.Name)
	}

	fmt.Printf("done. total=%d updated=%d skipped=%d\n", len(agents), updated, len(agents)-updated)
}
