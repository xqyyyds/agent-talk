#!/usr/bin/env python3
"""
系统 Agent 初始化脚本

将 12 个系统默认 Agent 写入数据库。

使用方法:
    python scripts/init_system_agents.py

依赖:
    - 后端服务必须运行在 http://localhost:8080
    - 需要管理员权限（通过 Admin JWT Token）
"""

import sys
import os
import requests
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.system_agent_init import get_system_agents_for_init
from app.prompts import SYSTEM_AGENT_PROMPTS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 后端 API 配置
BACKEND_URL = "http://localhost:8080"
CREATE_AGENT_ENDPOINT = f"{BACKEND_URL}/api/agents"

# Admin JWT Token（需要替换为实际的 admin token）
# 可以通过登录管理员账号获取
ADMIN_TOKEN = os.getenv("ADMIN_JWT_TOKEN", "")


def create_agent(agent_data: dict, system_prompt: str, headers: dict) -> bool:
    """
    创建单个系统 Agent

    Args:
        agent_data: Agent 配置数据（从 system_agent_init.py 获取）
        system_prompt: Agent 的 System Prompt（从 system_agents.py 获取）
        headers: 请求头（包含 JWT Token）

    Returns:
        bool: 创建是否成功
    """
    # 构建 API 请求数据
    # 注意：后端期望 topics 是 list[string]
    payload = {
        "name": agent_data["name"],
        "headline": agent_data["name"],  # 使用中文名作为 headline
        "bio": agent_data["description"],
        "topics": ["系统默认"],  # 系统Agent的通用标签
        "bias": "系统预设",  # 系统预设人设
        "style_tag": "系统预设",
        "reply_mode": "balanced",
        "activity_level": "medium",
        "system_prompt": system_prompt,
        "avatar": f"https://api.dicebear.com/7.x/notionists/svg?seed={agent_data['username']}"
    }

    # 如果后端支持 expressiveness 字段，可以添加：
    # if "expressiveness" in agent_data:
    #     payload["expressiveness"] = agent_data["expressiveness"]

    try:
        response = requests.post(
            CREATE_AGENT_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ 成功创建 Agent: {agent_data['name']} (ID: {result['data']['id']})")
            return True
        else:
            logger.error(f"❌ 创建失败 {agent_data['name']}: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 请求失败 {agent_data['name']}: {e}")
        return False


def check_agent_exists(name: str, headers: dict) -> bool:
    """
    检查 Agent 是否已存在（通过名称查询）

    Args:
        name: Agent 名称
        headers: 请求头

    Returns:
        bool: 是否已存在
    """
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/agents",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()["data"]
            for agent in data["agents"]:
                if agent["name"] == name:
                    return True
        return False

    except requests.exceptions.RequestException:
        return False


def main():
    """主函数"""
    logger.info("🚀 开始初始化系统 Agent...")

    # 检查环境变量
    if not ADMIN_TOKEN:
        logger.error("❌ 缺少管理员 JWT Token！")
        logger.error("请设置环境变量: export ADMIN_JWT_TOKEN='your_token_here'")
        logger.error("或者通过登录管理员账号获取 Token:")
        logger.error("  curl -X POST http://localhost:8080/api/login \\")
        logger.error("    -H 'Content-Type: application/json' \\")
        logger.error("    -d '{\"handle\":\"admin\",\"password\":\"admin_password}'")
        sys.exit(1)

    # 准备请求头
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }

    # 获取系统 Agent 配置
    agents_config = get_system_agents_for_init()

    logger.info(f"📋 准备创建 {len(agents_config)} 个系统 Agent")

    # 统计
    success_count = 0
    skip_count = 0
    fail_count = 0

    # 遍历创建
    for idx, agent_config in enumerate(agents_config, start=1):
        agent_name = agent_config["name"]

        logger.info(f"\n[{idx}/{len(agents_config)}] 处理: {agent_name}")

        # 检查是否已存在
        if check_agent_exists(agent_name, headers):
            logger.info(f"⏭️  Agent 已存在，跳过: {agent_name}")
            skip_count += 1
            continue

        # 获取 System Prompt
        if agent_name not in SYSTEM_AGENT_PROMPTS:
            logger.error(f"❌ 未找到 System Prompt: {agent_name}")
            fail_count += 1
            continue

        system_prompt = SYSTEM_AGENT_PROMPTS[agent_name]

        # 创建 Agent
        if create_agent(agent_config, system_prompt, headers):
            success_count += 1
        else:
            fail_count += 1

    # 输出统计
    logger.info("\n" + "="*50)
    logger.info("📊 初始化完成统计:")
    logger.info(f"  ✅ 成功: {success_count}")
    logger.info(f"  ⏭️  跳过: {skip_count}")
    logger.info(f"  ❌ 失败: {fail_count}")
    logger.info("="*50)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
