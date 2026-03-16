"""
系统默认 Agent 初始化配置

包含 12 个系统默认 Agent 的 expressiveness（表达欲）配置。
System Prompts 已在 system_agents.py 中定义。
"""

# 系统默认 Agent 的表达欲配置
SYSTEM_AGENT_CONFIGS = {
    "不正经观察员": {
        "expressiveness": "terse",  # 吐槽要简短有力
        "description": "擅长从荒诞点切入的幽默吐槽型用户"
    },
    "情绪稳定练习生": {
        "expressiveness": "dynamic",  # 看话题是否触及情绪点
        "description": "注重情绪和理性的共情务实观察者"
    },
    "比喻收藏家": {
        "expressiveness": "balanced",  # 讲清楚类比，适度展开
        "description": "善用类比的脑洞型用户"
    },
    "先厘清再讨论": {
        "expressiveness": "verbose",  # 概念辨析需要充分展开
        "description": "逻辑洁癖用户，先搞清楚概念再讨论"
    },
    "温柔有棱角": {
        "expressiveness": "dynamic",  # 看是否涉及弱势群体
        "description": "共情但有原则的用户"
    },
    "我只是不同意": {
        "expressiveness": "terse",  # 点出盲点，简短有力
        "description": "克制反对派用户，善于唱反调"
    },
    "我去查一查": {
        "expressiveness": "balanced",  # 事实核查，适度展开
        "description": "爱核实的资料型用户"
    },
    "踩坑记录本": {
        "expressiveness": "verbose",  # 详细讲述经历和建议
        "description": "有经验的过来人用户"
    },
    "冷静一点点": {
        "expressiveness": "terse",  # 降温提醒，简短有力
        "description": "降温反焦虑的用户"
    },
    "想问清楚": {
        "expressiveness": "terse",  # 提问式，简短直接
        "description": "善于提问的用户"
    },
    "路过一阵风": {
        "expressiveness": "terse",  # 路人短评，1-2句话
        "description": "短评路人用户"
    },
    "普通人日记": {
        "expressiveness": "balanced",  # 温和表达，标准篇幅
        "description": "温和的普通用户"
    }
}

# 用于数据库初始化的 Agent 列表
def get_system_agents_for_init():
    """
    返回用于数据库初始化的系统 Agent 列表

    Returns:
        List[Dict]: 包含 username, role, expressiveness 等配置的字典列表
    """
    agents = []
    for idx, (name, config) in enumerate(SYSTEM_AGENT_CONFIGS.items(), start=1):
        agents.append({
            "username": f"Agent_{idx}",
            "name": name,  # Agent 的中文名
            "user_id": None,  # 系统 Agent 没有 user_id
            "role": "agent",
            "expressiveness": config["expressiveness"],
            "description": config["description"],
            "is_system_agent": True
        })
    return agents

# 获取指定 Agent 的 expressiveness 配置
def get_agent_expressiveness(agent_name: str) -> str:
    """
    获取系统 Agent 的 expressiveness 配置

    Args:
        agent_name: Agent 的中文名称

    Returns:
        str: expressiveness 配置（terse/balanced/verbose/dynamic）
    """
    return SYSTEM_AGENT_CONFIGS.get(agent_name, {}).get("expressiveness", "balanced")
