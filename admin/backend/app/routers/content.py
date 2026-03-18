from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.audit import log_action
from app.database import get_db
from app.delete_utils import (
    hard_delete_answer,
    hard_delete_comment_thread,
    hard_delete_question,
)
from app.deps import get_current_admin
from app.models import AdminUser, Answer, Comment, Question


router = APIRouter(prefix="/admin/content", tags=["admin-content"])
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc


class PurgeByDateRequest(BaseModel):
    date: str = Field(..., description="北京时间日期，格式 YYYY-MM-DD")
    delete_qa: bool = True
    delete_debate: bool = True
    reset_hotspots: bool = True


def _beijing_day_bounds_to_utc(day: date) -> tuple[datetime, datetime]:
    start_beijing = datetime.combine(day, time.min, tzinfo=BEIJING_TZ)
    end_beijing = start_beijing + timedelta(days=1)
    return start_beijing.astimezone(UTC), end_beijing.astimezone(UTC)


def _paginate(query, page: int, page_size: int):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return total, rows


@router.get("/questions")
def list_questions(
    q: str | None = Query(default=None),
    q_type: str | None = Query(default=None),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    query = db.query(Question).filter(Question.deleted_at.is_(None))
    if q:
        query = query.filter(Question.title.ilike(f"%{q}%"))
    if q_type in ("qa", "debate"):
        query = query.filter(Question.type == q_type)

    total, rows = _paginate(query.order_by(Question.id.desc()), page, page_size)
    return {
        "total": total,
        "list": [
            {
                "id": r.id,
                "title": r.title,
                "content": r.content,
                "type": r.type,
                "user_id": r.user_id,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.patch("/questions/{question_id}")
def update_question(
    question_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = (
        db.query(Question)
        .filter(Question.id == question_id, Question.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="问题不存在")
    if "title" in payload:
        row.title = payload["title"]
    if "content" in payload:
        row.content = payload["content"]
    db.commit()
    log_action(
        db,
        current_admin.id,
        "admin.update_question",
        "question",
        str(question_id),
        payload={"keys": list(payload.keys())},
        request=request,
    )
    return {"message": "更新成功"}


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = (
        db.query(Question)
        .filter(Question.id == question_id, Question.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="问题不存在")

    try:
        hard_delete_question(db, question_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    log_action(
        db,
        current_admin.id,
        "admin.delete_question",
        "question",
        str(question_id),
        request=request,
    )
    return {"message": "删除成功（硬删除）"}


@router.get("/answers")
def list_answers(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    query = (
        db.query(Answer).filter(Answer.deleted_at.is_(None)).order_by(Answer.id.desc())
    )
    total, rows = _paginate(query, page, page_size)
    return {
        "total": total,
        "list": [
            {
                "id": r.id,
                "question_id": r.question_id,
                "user_id": r.user_id,
                "content": r.content,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.patch("/answers/{answer_id}")
def update_answer(
    answer_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = (
        db.query(Answer)
        .filter(Answer.id == answer_id, Answer.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="回答不存在")
    if "content" in payload:
        row.content = payload["content"]
    db.commit()
    log_action(
        db,
        current_admin.id,
        "admin.update_answer",
        "answer",
        str(answer_id),
        payload={"keys": list(payload.keys())},
        request=request,
    )
    return {"message": "更新成功"}


@router.delete("/answers/{answer_id}")
def delete_answer(
    answer_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = (
        db.query(Answer)
        .filter(Answer.id == answer_id, Answer.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="回答不存在")

    try:
        hard_delete_answer(db, answer_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    log_action(
        db,
        current_admin.id,
        "admin.delete_answer",
        "answer",
        str(answer_id),
        request=request,
    )
    return {"message": "删除成功（硬删除）"}


@router.get("/comments")
def list_comments(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    query = (
        db.query(Comment)
        .filter(Comment.deleted_at.is_(None))
        .order_by(Comment.id.desc())
    )
    total, rows = _paginate(query, page, page_size)
    return {
        "total": total,
        "list": [
            {
                "id": r.id,
                "answer_id": r.answer_id,
                "user_id": r.user_id,
                "content": r.content,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.patch("/comments/{comment_id}")
def update_comment(
    comment_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = (
        db.query(Comment)
        .filter(Comment.id == comment_id, Comment.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="评论不存在")

    if "content" in payload:
        row.content = payload["content"]

    db.commit()
    log_action(
        db,
        current_admin.id,
        "admin.update_comment",
        "comment",
        str(comment_id),
        payload={"keys": list(payload.keys())},
        request=request,
    )
    return {"message": "更新成功"}


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = (
        db.query(Comment)
        .filter(Comment.id == comment_id, Comment.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="评论不存在")

    try:
        hard_delete_comment_thread(db, comment_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    log_action(
        db,
        current_admin.id,
        "admin.delete_comment",
        "comment",
        str(comment_id),
        request=request,
    )
    return {"message": "删除成功（硬删除）"}

@router.post("/purge-by-date")
def purge_content_by_date(
    payload: PurgeByDateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    try:
        target_day = date.fromisoformat(payload.date)
    except Exception:
        raise HTTPException(status_code=400, detail="date format must be YYYY-MM-DD")

    if (
        not payload.delete_qa
        and not payload.delete_debate
        and not payload.reset_hotspots
    ):
        raise HTTPException(
            status_code=400,
            detail="nothing to do: enable at least one operation",
        )

    start_utc, end_utc = _beijing_day_bounds_to_utc(target_day)

    q_query = db.query(Question.id).filter(
        Question.deleted_at.is_(None),
        Question.created_at >= start_utc,
        Question.created_at < end_utc,
    )
    a_query = (
        db.query(Answer.id, Answer.question_id)
        .join(Question, Answer.question_id == Question.id)
        .filter(
            Answer.deleted_at.is_(None),
            Answer.created_at >= start_utc,
            Answer.created_at < end_utc,
        )
    )

    if payload.delete_qa and not payload.delete_debate:
        q_query = q_query.filter((Question.type == "qa") | (Question.type == ""))
        a_query = a_query.filter((Question.type == "qa") | (Question.type == ""))
    elif payload.delete_debate and not payload.delete_qa:
        q_query = q_query.filter(Question.type == "debate")
        a_query = a_query.filter(Question.type == "debate")
    elif payload.delete_qa and payload.delete_debate:
        q_query = q_query.filter(
            (Question.type == "qa")
            | (Question.type == "")
            | (Question.type == "debate")
        )
        a_query = a_query.filter(
            (Question.type == "qa")
            | (Question.type == "")
            | (Question.type == "debate")
        )
    else:
        q_query = q_query.filter(False)
        a_query = a_query.filter(False)

    question_ids = [row[0] for row in q_query.all()]
    question_id_set = set(question_ids)

    answers_deleted_via_questions = (
        db.query(Answer.id).filter(Answer.question_id.in_(question_ids)).count()
        if question_ids
        else 0
    )

    answer_rows = a_query.all()
    standalone_answer_ids = [
        row[0] for row in answer_rows if row[1] not in question_id_set
    ]

    hotspots_reset = 0
    try:
        for qid in question_ids:
            hard_delete_question(db, qid)

        for aid in standalone_answer_ids:
            hard_delete_answer(db, aid)

        if payload.reset_hotspots:
            result = db.execute(
                text(
                    """
                    UPDATE hotspots
                    SET status = 'pending',
                        question_id = NULL,
                        processed_at = NULL,
                        updated_at = NOW()
                    WHERE hotspot_date = :d
                      AND (
                        status IN ('processing', 'completed', 'skipped')
                        OR question_id IS NOT NULL
                        OR processed_at IS NOT NULL
                      )
                    """
                ),
                {"d": payload.date},
            )
            hotspots_reset = int(result.rowcount or 0)

        db.commit()
    except Exception:
        db.rollback()
        raise

    deleted_answers_total = int(
        answers_deleted_via_questions + len(standalone_answer_ids)
    )

    log_action(
        db,
        current_admin.id,
        "admin.purge_content_by_date",
        "content",
        payload.date,
        payload={
            "date": payload.date,
            "timezone": "Asia/Shanghai",
            "delete_qa": payload.delete_qa,
            "delete_debate": payload.delete_debate,
            "reset_hotspots": payload.reset_hotspots,
            "deleted_questions": len(question_ids),
            "deleted_answers": deleted_answers_total,
            "hotspots_reset": hotspots_reset,
        },
        request=request,
    )

    return {
        "message": "ok",
        "data": {
            "date": payload.date,
            "timezone": "Asia/Shanghai",
            "deleted_questions": len(question_ids),
            "deleted_answers": deleted_answers_total,
            "hotspots_reset": hotspots_reset,
            "window_utc": {
                "start": start_utc.isoformat(),
                "end": end_utc.isoformat(),
            },
        },
    }
