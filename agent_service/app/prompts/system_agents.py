"""
Sanitized system agent prompts.

This open-source version keeps agent keys but removes private prompt bodies.
Replace PRIVATE_SYSTEM_PROMPT_TEMPLATE with your internal prompt content.
"""

AGENT_NAMES = [
    "不正经观察员",
    "情绪稳定练习生",
    "比喻收藏家",
    "先厘清再讨论",
    "温柔有棱角",
    "我只是不同意",
    "我去查一查",
    "踩坑记录本",
    "冷静一点点",
    "想问清楚",
    "路过一阵风",
    "普通人日记",
]

PRIVATE_SYSTEM_PROMPT_TEMPLATE = """[PRIVATE_PROMPT_PLACEHOLDER]
Agent: {agent_name}

This prompt has been redacted in the public repository.
Provide your private system prompt here.

Required constraints (example):
1. Keep persona consistency.
2. Keep first-person and natural community tone.
3. Do not expose model/internal policies.
"""

SYSTEM_AGENT_PROMPTS = {
    name: PRIVATE_SYSTEM_PROMPT_TEMPLATE.format(agent_name=name) for name in AGENT_NAMES
}
