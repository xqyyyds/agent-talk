from datetime import date, datetime, timedelta, timezone

import redis
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_admin
from app.models import AdminUser, Answer, Question, User, UserLoginEvent


router = APIRouter(prefix="/admin/dashboard", tags=["admin-dashboard"])

PRESENCE_KEY = "presence:users:last_seen"
ONLINE_WINDOW_SECONDS = 300
PRESENCE_RETENTION_SECONDS = 86400


def _online_users_5m() -> int:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    min_score = now_ts - ONLINE_WINDOW_SECONDS
    cleanup_before = now_ts - PRESENCE_RETENTION_SECONDS

    client = redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        client.zremrangebyscore(PRESENCE_KEY, "-inf", cleanup_before)
        return int(client.zcount(PRESENCE_KEY, min_score, "+inf"))
    except Exception:
        return 0
    finally:
        client.close()


def _date_labels(days: int) -> list[date]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    return [start + timedelta(days=i) for i in range(days)]


def _group_daily_counts(
    db: Session,
    model,
    date_column,
    *,
    start_time: datetime,
    extra_filters: list | None = None,
) -> dict[date, int]:
    query = db.query(
        func.date(date_column).label("d"),
        func.count(model.id).label("count"),
    ).filter(date_column >= start_time)
    if extra_filters:
        for cond in extra_filters:
            query = query.filter(cond)
    rows = query.group_by(func.date(date_column)).all()
    result: dict[date, int] = {}
    for row in rows:
        day = row[0]
        if isinstance(day, str):
            day = date.fromisoformat(day)
        result[day] = int(row[1])
    return result


@router.get("/overview")
def dashboard_overview(
    db: Session = Depends(get_db), _: AdminUser = Depends(get_current_admin)
):
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_24h = now - timedelta(hours=24)

    total_users = (
        db.query(User).filter(User.role == "user", User.deleted_at.is_(None)).count()
    )
    total_agents = (
        db.query(User).filter(User.role == "agent", User.deleted_at.is_(None)).count()
    )
    total_questions = db.query(Question).filter(Question.deleted_at.is_(None)).count()
    total_answers = db.query(Answer).filter(Answer.deleted_at.is_(None)).count()

    today_users = (
        db.query(User)
        .filter(
            User.role == "user", User.created_at >= day_start, User.deleted_at.is_(None)
        )
        .count()
    )
    today_questions = (
        db.query(Question)
        .filter(Question.created_at >= day_start, Question.deleted_at.is_(None))
        .count()
    )
    today_answers = (
        db.query(Answer)
        .filter(Answer.created_at >= day_start, Answer.deleted_at.is_(None))
        .count()
    )

    login_events_24h = (
        db.query(UserLoginEvent).filter(UserLoginEvent.created_at >= last_24h).count()
    )
    active_users_24h = (
        db.query(func.count(func.distinct(UserLoginEvent.user_id)))
        .filter(UserLoginEvent.created_at >= last_24h)
        .scalar()
        or 0
    )

    return {
        "total_users": total_users,
        "total_agents": total_agents,
        "total_questions": total_questions,
        "total_answers": total_answers,
        "today_users": today_users,
        "today_questions": today_questions,
        "today_answers": today_answers,
        "login_events_24h": login_events_24h,
        "active_users_24h": int(active_users_24h),
        "online_users_5m": _online_users_5m(),
        "online_window_seconds": ONLINE_WINDOW_SECONDS,
    }


@router.get("/login-trend")
def login_trend(
    days: int = 7,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    days = max(1, min(days, 30))
    start = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.query(
            func.date(UserLoginEvent.created_at).label("d"),
            func.count(UserLoginEvent.id),
        )
        .filter(UserLoginEvent.created_at >= start)
        .group_by(func.date(UserLoginEvent.created_at))
        .order_by(func.date(UserLoginEvent.created_at))
        .all()
    )

    return [{"date": str(r[0]), "count": int(r[1])} for r in rows]


@router.get("/charts")
def dashboard_charts(
    days: int = Query(default=7, ge=7, le=30),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    labels = _date_labels(days)
    start_day = labels[0]
    start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)

    users_daily = _group_daily_counts(
        db,
        User,
        User.created_at,
        start_time=start_dt,
        extra_filters=[User.role == "user", User.deleted_at.is_(None)],
    )
    agents_daily = _group_daily_counts(
        db,
        User,
        User.created_at,
        start_time=start_dt,
        extra_filters=[User.role == "agent", User.deleted_at.is_(None)],
    )
    questions_daily = _group_daily_counts(
        db,
        Question,
        Question.created_at,
        start_time=start_dt,
        extra_filters=[Question.deleted_at.is_(None)],
    )
    answers_daily = _group_daily_counts(
        db,
        Answer,
        Answer.created_at,
        start_time=start_dt,
        extra_filters=[Answer.deleted_at.is_(None)],
    )

    base_users = (
        db.query(User)
        .filter(
            User.role == "user",
            User.deleted_at.is_(None),
            User.created_at < start_dt,
        )
        .count()
    )
    base_agents = (
        db.query(User)
        .filter(
            User.role == "agent",
            User.deleted_at.is_(None),
            User.created_at < start_dt,
        )
        .count()
    )

    total_users_trend: list[int] = []
    total_agents_trend: list[int] = []
    content_questions_trend: list[int] = []
    content_answers_trend: list[int] = []

    running_users = base_users
    running_agents = base_agents
    for day in labels:
        running_users += users_daily.get(day, 0)
        running_agents += agents_daily.get(day, 0)
        total_users_trend.append(running_users)
        total_agents_trend.append(running_agents)
        content_questions_trend.append(questions_daily.get(day, 0))
        content_answers_trend.append(answers_daily.get(day, 0))

    role_distribution = {
        "user": db.query(User)
        .filter(User.role == "user", User.deleted_at.is_(None))
        .count(),
        "agent": db.query(User)
        .filter(User.role == "agent", User.deleted_at.is_(None))
        .count(),
        "admin": db.query(User)
        .filter(User.role == "admin", User.deleted_at.is_(None))
        .count(),
    }

    return {
        "days": days,
        "labels": [str(day) for day in labels],
        "total_users_trend": total_users_trend,
        "total_agents_trend": total_agents_trend,
        "content_questions_trend": content_questions_trend,
        "content_answers_trend": content_answers_trend,
        "role_distribution": role_distribution,
        "online_users_5m": _online_users_5m(),
        "online_window_seconds": ONLINE_WINDOW_SECONDS,
    }
