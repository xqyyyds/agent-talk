"""
提示词模块初始化

集中导出所有提示词配置，方便其他模块导入使用。

架构说明：
- agent_optimizer.py: Agent 配置优化器（用户输入 → System Prompt）
- system_agents.py: 12 个系统默认 Agent 的完整 System Prompt（预定义常量）
- question.py: 提问任务的 User Prompt 模板
- answer.py: 回答/评论任务的 User Prompt 模板

使用模式：
- System Prompt: 完整的 Agent 人设（用户创建由优化器生成，系统 Agent 为预定义常量）
- User Prompt: 任务级指令（运行时动态生成）

注意：同一套 System Prompts 既用于提问也用于回答
任务的区别通过 User Prompt（question.py / answer.py）来实现
"""

# ============================================================
# Agent 优化器
# ============================================================
from .agent_optimizer import AGENT_OPTIMIZER_META_PROMPT, AGENT_FALLBACK_PROMPT

# ============================================================
# 系统 Agent System Prompts（预定义常量）
# ============================================================
from .system_agents import SYSTEM_AGENT_PROMPTS

# ============================================================
# 提问任务 User Prompt 和表达欲配置
# ============================================================
from .question import (
    QUESTION_USER_PROMPT,
    QUESTION_MEMORY_SECTION,
    EXPRESSIVENESS_INSTRUCTIONS as QUESTION_EXPRESSIVENESS_INSTRUCTIONS,
)

# ============================================================
# 回答任务 User Prompt 和表达欲配置
# ============================================================
from .answer import (
    ANSWER_USER_PROMPT,
    COMMENT_USER_PROMPT,
    EXISTING_ANSWERS_SECTION,
    EXPRESSIVENESS_INSTRUCTIONS as ANSWER_EXPRESSIVENESS_INSTRUCTIONS,
)

# ============================================================
# 编排器 ReAct Agent 提示词
# ============================================================
from .orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    HOTSPOT_TASK_TEMPLATE,
    ZHIHU_QUESTION_INSTRUCTION,
    OTHER_QUESTION_INSTRUCTION,
)

__all__ = [
    # Agent 优化器
    "AGENT_OPTIMIZER_META_PROMPT",
    "AGENT_FALLBACK_PROMPT",
    # 系统 Agent System Prompts（注意：同一套既用于提问也用于回答）
    "SYSTEM_AGENT_PROMPTS",
    # 任务 User Prompts
    "QUESTION_USER_PROMPT",
    "QUESTION_MEMORY_SECTION",
    "ANSWER_USER_PROMPT",
    "COMMENT_USER_PROMPT",
    "EXISTING_ANSWERS_SECTION",
    # 表达欲指令映射
    "QUESTION_EXPRESSIVENESS_INSTRUCTIONS",
    "ANSWER_EXPRESSIVENESS_INSTRUCTIONS",
    # 编排器 ReAct Agent 提示词
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "HOTSPOT_TASK_TEMPLATE",
    "ZHIHU_QUESTION_INSTRUCTION",
    "OTHER_QUESTION_INSTRUCTION",
]
