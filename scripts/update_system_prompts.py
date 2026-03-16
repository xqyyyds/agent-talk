#!/usr/bin/env python3
"""
更新系统Agent的System Prompt到数据库

从 agent_service/app/prompts/system_agents.py 读取预定义的prompts，
并通过API更新到数据库中的12个系统Agent。
"""

import sys
import os
import requests
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent_service'))

# 现在可以导入prompts模块
try:
    from app.prompts.system_agents import SYSTEM_AGENT_PROMPTS
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保从项目根目录运行此脚本，或手动调整导入路径")
    sys.exit(1)

# 后端API配置
BACKEND_URL = "http://localhost:8080"
UPDATE_AGENT_ENDPOINT = f"{BACKEND_URL}/api/agents"

# Admin JWT Token（需要替换为实际的token）
# 可以通过以下方式获取：
# curl -X POST http://localhost:8080/api/login \
#   -H "Content-Type: application/json" \
#   -d '{"handle":"admin","password":"your_password"}'
ADMIN_TOKEN = os.getenv("ADMIN_JWT_TOKEN", "")

# Agent名称到ID的映射（需要先从数据库获取）
def get_agent_mapping(token):
    """获取系统Agent的ID映射"""
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(f"{BACKEND_URL}/api/agents", headers=headers)

    if response.status_code != 200:
        print(f"❌ 获取Agent列表失败: {response.status_code}")
        return None

    data = response.json()["data"]
    agents = data["agents"] if isinstance(data, dict) and "agents" in data else data

    mapping = {}
    for agent in agents:
        if agent["is_system"]:
            mapping[agent["name"]] = agent["id"]

    return mapping


def update_system_prompt(agent_id, system_prompt, token):
    """更新单个Agent的System Prompt"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "system_prompt": system_prompt
    }

    response = requests.put(
        f"{UPDATE_AGENT_ENDPOINT}/{agent_id}",
        headers=headers,
        json=payload
    )

    return response.status_code == 200


def main():
    print("🚀 开始更新系统Agent的System Prompts...")
    print("=" * 70)

    # 检查环境变量
    if not ADMIN_TOKEN:
        print("❌ 缺少管理员 JWT Token！")
        print("请设置环境变量:")
        print("  export ADMIN_JWT_TOKEN='your_token_here'")
        print("")
        print("获取Token的方式:")
        print("  curl -X POST http://localhost:8080/api/login \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"handle\":\"admin\",\"password\":\"your_password\"}'")
        sys.exit(1)

    # 获取Agent ID映射
    print("\n📋 步骤1: 获取Agent ID映射...")
    agent_mapping = get_agent_mapping(ADMIN_TOKEN)

    if not agent_mapping:
        print("❌ 无法获取Agent映射")
        sys.exit(1)

    print(f"✅ 找到 {len(agent_mapping)} 个系统Agent")

    # 更新每个Agent的System Prompt
    print("\n📝 步骤2: 更新System Prompts...")
    print("-" * 70)

    success_count = 0
    skip_count = 0
    error_count = 0

    for agent_name, system_prompt in SYSTEM_AGENT_PROMPTS.items():
        agent_id = agent_mapping.get(agent_name)

        if not agent_id:
            print(f"⚠️  跳过: {agent_name} (未在数据库中找到)")
            skip_count += 1
            continue

        # 更新System Prompt
        if update_system_prompt(agent_id, system_prompt, ADMIN_TOKEN):
            print(f"✅ 成功: {agent_name} (ID={agent_id})")
            print(f"     System Prompt长度: {len(system_prompt)} 字符")
            success_count += 1
        else:
            print(f"❌ 失败: {agent_name} (ID={agent_id})")
            error_count += 1

        print()  # 空行分隔

    # 输出统计
    print("=" * 70)
    print("📊 更新完成统计:")
    print(f"  ✅ 成功更新: {success_count}")
    print(f"  ⏭️  跳过: {skip_count}")
    print(f"  ❌ 更新失败: {error_count}")
    print("=" * 70)

    if success_count == 12:
        print("\n🎉 所有12个系统Agent的System Prompt更新成功！")
        print("现在可以运行 go run verify_system_prompts.go 验证")
    elif success_count > 0:
        print(f"\n⚠️  部分更新成功: {success_count}/12")
    else:
        print("\n❌ 所有更新都失败了，请检查:")
        print("  1. 后端服务是否运行 (http://localhost:8080)")
        print("  2. JWT Token是否正确")
        print("  3. Agent映射是否正确")


if __name__ == "__main__":
    main()
