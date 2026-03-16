"""
LangGraph 状态定义

定义问答流程的状态结构（严格遵循 LangGraph 1.0 规范）
"""

from typing import List, Dict, Optional, TypedDict, Annotated
from app.schemas.models import QuestionOutput
import operator


class QAState(TypedDict):
    """
    问答流程状态

    使用 TypedDict + Annotated[List, operator.add] 遵循 LangGraph 1.0 规范。
    """

    # 输入
    hotspot: Dict  # 热点信息 {"topic": ..., "category": ..., ...}
    cycle: int
    total_cycles: int

    # 热点数据库信息（新增：DB-based 流程）
    hotspot_db_id: Optional[int]  # hotspots 表的主键 ID
    hotspot_source: Optional[str]  # "zhihu" | "weibo"

    # 中间状态
    search_results: List[Dict]
    question_output: Optional[QuestionOutput]
    question_id: Optional[int]
    questioner_username: Optional[str]
    questioner_persona: Optional[str]
    answers: Annotated[List[Dict], operator.add]

    # 执行状态（使用 operator.add 累加）
    logs: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
