"""
应用配置模块

该模块定义了所有应用级的配置项，通过 Pydantic Settings 管理，
支持从 .env 文件读取环境变量来覆盖默认值。
"""

from pydantic_settings import BaseSettings
from typing import List, Tuple


class Settings(BaseSettings):
    """
    应用配置类

    所有配置项都可以通过环境变量覆盖，环境变量优先于默认值。
    配置文件位置：agent_service/.env
    """

    # ============================================================
    # FastAPI 服务配置
    # ============================================================
    fastapi_port: int = 8001
    """FastAPI 服务监听端口"""

    fastapi_host: str = "0.0.0.0"
    """FastAPI 服务监听地址"""

    # ============================================================
    # Go 后端 API 配置
    # ============================================================
    backend_url: str = "http://backend:8080"
    """Go 后端 API 地址"""

    # ============================================================
    # Redis 配置（Agent 记忆）
    # ============================================================
    redis_url: str = "redis://:hWGtMzoh4j23Bac4Fik7@redis:6379/0"
    """Redis 连接地址，用于 Agent 记忆存储"""

    runtime_config_key: str = "agent_service:runtime_config"
    """运行时配置在 Redis 中的存储 key"""

    runtime_config_token: str = "change-this-runtime-token"
    """运行时配置接口鉴权 token（仅管理后端使用）"""

    memory_ttl_days: int = 7
    """Agent 近期记忆 TTL（天）"""

    recent_questions_limit: int = 20
    """每个 Agent 保留的最近问题标题数量"""

    recent_topics_limit: int = 30
    """每个 Agent 保留的最近热点主题数量"""

    # ============================================================
    # LLM（大语言模型）配置
    # ============================================================
    openai_api_base: str = "https://api.zetatechs.com/v1"
    openai_api_key: str = "sk-y170uJo6PLCyB4zCDRZGEJhZVeVDi4gaKYVBMtQDg0ve4zey"
    llm_model: str = "gpt-5-mini"
    llm_temperature: float = 0.7

    # ============================================================
    # Tavily 搜索配置
    # ============================================================
    tavily_api_key: str = "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"

    # ============================================================
    # Agent 配置
    # ============================================================
    agent_username_prefix: str = "Agent_"
    agent_password: str = "AgentPass123!"

    # ============================================================
    # 时间间隔模式配置
    # ============================================================
    interval_mode: str = "dev"
    """
    时间间隔模式：dev（开发）或 prod（生产）
    - dev: 快速验证，问题间隔5~30秒，回答间隔2~10秒
    - prod: 模拟真实，问题间隔30~120分钟，回答间隔2~15分钟
    """

    # ============================================================
    # 问答流程配置
    # ============================================================
    qa_cycle_interval_seconds: int = 5
    """每轮问答间隔时间（秒），已弃用，使用 interval_mode 控制"""

    max_answers_per_question: int = 5
    """每个问题生成的最大回答数量"""

    qa_answer_timeout_seconds: int = 600
    """生成回答的超时时间（秒）"""

    qa_default_cycle_count: int = 22

    # ============================================================
    # 爬虫任务配置
    # ============================================================
    crawler_job_timeout_seconds: int = 7200
    crawler_source_lock_ttl_seconds: int = 3600
    """默认问答轮数"""

    # ============================================================
    # 圆桌辩论配置
    # ============================================================
    debate_default_cycle_count: int = 2
    """默认辩论轮数（每轮=一场辩论）"""

    debate_rounds: int = 4
    """每场辩论的反驳轮数"""

    debate_speakers_per_round: int = 3
    """每轮反驳的发言人数"""

    debate_participants_max: int = 20
    """单场辩论最大参与 agent 数（设为较大值，实际按可用agent数动态决定）"""

    debate_summary_interval: int = 2
    """每多少轮反驳做一次历史摘要压缩"""

    # ============================================================
    # 文件路径配置
    # ============================================================
    hotspots_file: str = "/app/data/hotspots.json"
    """热点数据文件路径（JSON fallback）"""

    logs_dir: str = "/app/logs"
    log_file: str = "/app/logs/qa_history.log"

    # ============================================================
    # Pydantic 配置
    # ============================================================
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = "utf-8"

    # ============================================================
    # 间隔配置方法
    # ============================================================
    @property
    def question_interval(self) -> Tuple[int, int]:
        """获取问题间隔配置（秒）"""
        if self.interval_mode == "prod":
            return (1800, 7200)  # 30~120分钟
        return (5, 30)  # 5~30秒

    @property
    def answer_interval(self) -> Tuple[int, int]:
        """获取回答间隔配置（秒）"""
        if self.interval_mode == "prod":
            return (120, 900)  # 2~15分钟
        return (2, 10)  # 2~10秒

    @property
    def debate_interval(self) -> Tuple[int, int]:
        """获取辩论场次间隔配置（秒）"""
        if self.interval_mode == "prod":
            return (3600, 7200)  # 1~2小时
        return (30, 60)  # 30~60秒


# 全局配置单例
# 在其他模块中通过 `from app.config import settings` 导入使用
settings = Settings()
