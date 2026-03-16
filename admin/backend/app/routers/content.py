from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

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
