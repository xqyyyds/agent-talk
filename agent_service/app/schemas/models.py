"""
数据模型定义

使用 Pydantic 定义所有 API 请求/响应和内部数据模型。
包含 Agent、问答流程、LangGraph 状态等相关模型。
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Literal
from datetime import datetime


# ============================================================
# Agent 相关模型
# ============================================================
from pydantic import BaseModel, Field
from typing import List


class AgentMetaBlueprint(BaseModel):
    """
    Agent 灵魂蓝图 (优化器输出)

    用于将用户模糊的输入转化为结构化的 System Prompt 组件。
    """

    # --- 1. 记忆植入 (Memory) ---
    expanded_persona: str = Field(
        ...,
        description="基于用户 Bio 扩写的第一人称背景故事。必须包含具体的职业经历、行业痛点或成就，字数控制在 150 字以内。",
    )

    # --- 2. 逻辑闭环 (Logic) ---
    cognitive_bias_reasoning: str = Field(
        ...,
        description="为用户的核心立场提供深层逻辑支撑。解释持有该偏见的技术原因、历史教训或理论依据，使其具备说服力。",
    )

    # --- 3. 语气守则 (Tone) ---
    speaking_style_rules: List[str] = Field(
        ...,
        description="3-5 条关于语气的执行指令。包含句式长短、修辞手法（如反讽/比喻）、以及禁止使用的词汇（如客套话）。",
        min_items=3,
    )

    # --- 4. 互动纲领 (Goal) ---
    interaction_goal: str = Field(
        ...,
        description="本次交互的终极策略目标。明确 Agent 是为了赢得辩论、传授知识、还是提供情绪价值。",
    )

    # --- 5. 开场战术 (Hook) ---
    opening_strategy: str = Field(
        ...,
        description="具体的开场行为指令。指示 Agent 如何在不打招呼的情况下直接切入话题（例如引用数据、直接反驳或讲述轶事）。",
    )

    # --- 6. 表达欲控制 (Expressiveness) ---
    expressiveness_rule: str = Field(
        ..., description="基于用户选择的 expressiveness 模式，生成的具体表达约束指令。"
    )


class AgentInfo(BaseModel):
    """
    Agent 信息模型

    表示一个 AI Agent 的基本信息和认证状态。
    """

    model_config = ConfigDict(populate_by_name=True)

    username: str
    """Agent 用户名"""

    user_id: Optional[int] = None
    """用户 ID（从后端获取）"""

    role: str = "agent"
    """用户角色，固定为 'agent'"""

    token: Optional[str] = None
    """JWT 认证令牌（API Key）"""

    token_expires_at: Optional[datetime] = None
    """令牌过期时间"""

    persona: str = ""
    """Agent 人设（角色类型），如：技术专家、行业分析师等"""

    system_prompt: str = ""
    """Agent 的完整 System Prompt（来自数据库，由优化器生成）"""

    activity_level: Literal["high", "medium", "low"] = "medium"
    """
    活跃度级别，控制提问权重和回答概率
    - high: 高活跃，提问权重3，回答概率80%
    - medium: 中等，提问权重2，回答概率50%
    - low: 低活跃，提问权重1，回答概率15%
    """

    is_system: bool = False
    """是否为系统Agent（NPC），系统Agent必须回答每个问题"""

    expressiveness: Literal["terse", "balanced", "verbose", "dynamic"] = "balanced"
    """
    控制 Agent 的表达欲望和回复篇幅模式
    - terse: 惜字如金，高冷简洁 (50字以内)
    - balanced: 标准篇幅，逻辑清晰 (100-200字)
    - verbose: 话痨详尽，深度输出 (300字以上)
    - dynamic: 基于兴趣的动态表达 (根据话题智能调整，最像真人)
    """

    stats: Dict = Field(default_factory=dict)
    """Agent 统计信息，包含 questions_created 和 answers_created"""

    model_source: Literal["system", "custom"] = "system"
    """Agent 绑定的模型来源"""

    model_id: str = ""
    """系统模型目录 ID（仅 system 模式使用）"""

    custom_model_config: Optional[str] = Field(default=None, alias="model_config")
    """自定义模型密文配置（仅 custom 模式使用）"""

    model_info: Optional[Dict] = None
    """后端解析后的模型信息（用于展示与调试）"""


class AgentStatus(BaseModel):
    """
    Agent 状态模型

    用于展示 Agent 的当前状态和统计信息。
    """

    username: str
    """Agent 用户名"""

    role: str
    """用户角色"""

    is_active: bool
    """Agent 是否活跃（已初始化且 token 有效）"""

    token_valid: bool
    """Token 是否有效"""

    questions_created: int = 0
    """已创建的问题数量"""

    answers_created: int = 0
    """已创建的回答数量"""

    last_activity: Optional[datetime] = None
    """最后活动时间"""


# ============================================================
# 问答相关模型（LLM 输入输出）
# ============================================================
class HotspotItem(BaseModel):
    """
    热点项模型

    表示一个待讨论的热点话题。
    """

    category: str
    """热点类别，如：科技、社会、财经、生活、政治、高校"""

    topic: str
    """热点主题/标题"""


class QuestionInput(BaseModel):
    """
    提问 Agent 输入模型

    传递给 LLM 生成问题的输入数据。
    """

    category: str
    """热点类别"""

    topic: str
    """热点主题"""

    search_results: List[dict] = Field(default_factory=list)
    """搜索结果列表，用于生成有依据的问题"""


class QuestionOutput(BaseModel):
    """
    提问 Agent 输出模型

    LLM 生成的问题输出，使用结构化输出保证格式。
    """

    title: str = Field(
        description="问题标题，一句话概括，不超过25字，像真人提问，不要出现'title:'这样的标记"
    )
    """问题标题，简洁有力"""

    content: str = Field(
        description="问题的详细描述或背景，用自然口语讲述，像真人在说话，带点情绪或困惑，绝对不要出现'content:'或JSON格式标记"
    )
    """问题内容，详细阐述"""

    reasoning: str = Field(description="生成此问题的思路和依据（内部用，不展示给用户）")
    """生成理由，解释为什么提出这个问题"""

    references: List[str] = Field(
        default_factory=list, description="引用的搜索结果来源"
    )
    """参考来源 URL 列表"""


class AnswerInput(BaseModel):
    """
    回答 Agent 输入模型

    传递给 LLM 生成回答的输入数据。
    """

    question: dict
    """问题信息，包含 id、title、content"""

    persona: str
    """回答者人设（角色类型）"""

    search_results: List[dict] = Field(default_factory=list)
    """搜索结果列表，用于生成有依据的回答"""


class AnswerOutput(BaseModel):
    """
    回答 Agent 输出模型

    LLM 生成的回答输出，使用结构化输出保证格式。
    """

    content: str = Field(
        description="回答内容，真人风格，分段清晰，口语化，可以有表情符号，禁止Markdown格式，建议200-800字"
    )
    """
    回答正文

    要求：
    - 多段落，避免大段文字堆砌
    - 口语化表达，使用"额""呃""吧"等语气词
    - 可以有表情符号增加生动性
    - 严禁使用 Markdown 格式（**粗体**、### 标题、- 列表等）
    """

    viewpoint: str = Field(description="核心观点摘要，15-100字")
    """
    核心观点

    一句话概括回答的主要观点和立场。
    """

    evidence: List[str] = Field(default_factory=list, description="支撑观点的事实/数据")
    """
    证据列表

    支持观点的具体事实、数据或案例。
    """

    references: List[str] = Field(default_factory=list, description="引用来源")
    """
    参考来源 URL 列表

    回答中引用的搜索结果来源地址。
    """


# ============================================================
# API 请求/响应模型
# ============================================================
class QAStartRequest(BaseModel):
    """
    启动问答请求模型

    用于 POST /qa/start 接口的请求体。
    """

    cycle_count: Optional[int] = Field(
        None, description="问答轮数（不填则使用配置文件默认值）", ge=1, example=80
    )
    """
    计划执行的问答轮数

    实际执行轮数 = min(cycle_count, 热点总数)

    默认值从配置文件读取，可通过 .env 中的 QA_DEFAULT_CYCLE_COUNT 配置。
    如果不指定，使用配置文件中的默认值。
    """

    categories: Optional[List[str]] = Field(
        default=None,
        description="指定热点类别（如：['科技', '社会']），不填则全部",
        example=None,
    )
    """
    热点类别过滤

    如果指定，只处理指定类别的热点。
    如果为 None 或空，则自动处理所有类别的热点。
    """

    source: Optional[str] = Field(
        default=None,
        description="热点数据源筛选（zhihu / weibo），不填则全部",
        example=None,
    )
    """热点来源筛选，可选 zhihu / weibo，不填则处理所有来源"""

    interval_seconds: int = Field(
        default=30,
        description="每轮间隔秒数（已弃用，请使用 INTERVAL_MODE 环境变量）",
        ge=1,
    )
    """
    每轮间隔时间（已弃用）

    该参数已弃用，请使用 .env 文件中的 QA_CYCLE_INTERVAL_SECONDS 配置。
    保留此参数仅为向后兼容。
    """


class QAStatusResponse(BaseModel):
    """
    问答状态响应模型

    用于 GET /qa/status 接口的响应体。
    """

    status: str = Field(description="running|stopped|idle|error")
    """
    问答会话状态

    - running: 正在运行中
    - stopped: 已停止
    - idle: 空闲
    - error: 发生错误
    """

    current_cycle: int = Field(description="当前轮次")
    """当前执行到第几轮（从 1 开始）"""

    total_cycles: int = Field(description="总轮数")
    """计划执行的总轮数"""

    current_hotspot: Optional[HotspotItem] = None
    """当前正在处理的热点"""

    agents_status: List[AgentStatus] = Field(default_factory=list)
    """所有 Agent 的状态列表"""

    logs: List[str] = Field(default_factory=list)
    """
    最近的日志消息列表

    按时间倒序排列，最新的在前。
    """


class QAHistoryItem(BaseModel):
    """
    问答历史项模型

    表示一轮已完成的问答记录。
    """

    id: int
    """历史记录 ID"""

    category: str
    """热点类别"""

    topic: str
    """热点主题"""

    question_title: str
    """生成的问题标题"""

    question_id: int
    """问题在后端数据库中的 ID"""

    answers_count: int
    """生成的回答数量"""

    created_at: datetime
    """创建时间"""


class BackendAPIResponse(BaseModel):
    """
    Go 后端 API 统一响应模型

    所有后端 API 返回的数据都遵循此格式。
    """

    code: int
    """状态码，200 表示成功"""

    message: str
    """响应消息"""

    data: Optional[dict] = None
    """响应数据，具体内容因接口而异"""


# ============================================================
# LangGraph 状态模型
# ============================================================
class QAState(BaseModel):
    """
    问答流程状态模型

    LangGraph 状态图的核心状态对象，在各个节点间传递和更新。
    使用 operator.add 合并状态，确保累加器字段正确累积。
    """

    current_hotspot: Optional[HotspotItem] = None
    """当前处理的热点"""

    question: Optional[dict] = None
    """当前生成的问题信息"""

    answers: List[dict] = Field(default_factory=list)
    """
    已生成的回答列表

    注意：使用 operator.add 合并，不是直接覆盖。
    """

    search_results: List[dict] = Field(default_factory=list)
    """当前轮次的搜索结果"""

    cycle: int = 0
    """当前轮次编号"""

    total_cycles: int = 1
    """总轮次数"""

    logs: List[str] = Field(default_factory=list)
    """
    日志消息列表

    使用 operator.add 合并，累积所有节点的日志。
    """


# ============================================================
# Debate API 模型
# ============================================================
class DebateStartRequest(BaseModel):
    """启动辩论请求"""

    cycle_count: Optional[int] = Field(
        None, description="辩论场次数（不填则使用默认值）", ge=1, example=2
    )
    resume: bool = Field(False, description="是否恢复上次未完成的辩论进度")


class DebateStatusResponse(BaseModel):
    """辩论状态响应"""

    status: str
    current_cycle: int
    total_cycles: int
    history_count: int
    logs: List[str] = Field(default_factory=list)
