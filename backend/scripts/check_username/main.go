package main

import (
	"fmt"

	"github.com/joho/godotenv"
	"backend/internal/database"
	"backend/internal/model"
)

func main() {
	godotenv.Load()
	database.Init()

	var agents []model.User
	database.DB.Where("role = ? AND is_system = ?", model.RoleAgent, true).
		Order("id").
		Select("id, name, handle, expressiveness").
		Find(&agents)

	fmt.Println("数据库中系统Agent的实际状态:")
	fmt.Println(" ID | Handle          | Name         | Expressiveness")
	fmt.Println("----|-----------------|--------------|---------------")

	for _, a := range agents {
		handle := "(nil)"
		if a.Handle != nil {
			handle = *a.Handle
		}
		fmt.Printf("%2d  | %-15s | %-12s | %s\n", a.ID, handle, a.Name, a.Expressiveness)
	}
}
