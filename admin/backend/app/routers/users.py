from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.delete_utils import hard_delete_user
from app.deps import get_current_admin
from app.models import AdminUser, User
from app.security import hash_password
from app.services.avatar_normalizer import normalize_avatar_value


router = APIRouter(prefix="/admin/users", tags=["admin-users-data"])


@router.get("")
def list_users(
    role: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    query = db.query(User).filter(User.deleted_at.is_(None))
    if role:
        query = query.filter(User.role == role)
    if q:
        query = query.filter(
            (User.name.ilike(f"%{q}%")) | (User.handle.ilike(f"%{q}%"))
        )

    total = query.count()
    rows = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    for row in rows:
        normalized_avatar = normalize_avatar_value(row.avatar)
        if normalized_avatar != (row.avatar or ""):
            row.avatar = normalized_avatar
    db.commit()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": [
            {
                "id": r.id,
                "name": r.name,
                "handle": r.handle,
                "role": r.role,
                "avatar": normalize_avatar_value(r.avatar),
                "owner_id": r.owner_id,
                "is_system": r.is_system,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.post("")
def create_user(
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    handle = payload.get("handle")
    password = payload.get("password")

    if not handle or not password:
        raise HTTPException(status_code=400, detail="注册用户必须提供 handle/password")

    existed = db.query(User).filter(User.handle == handle).first()
    if existed:
        raise HTTPException(status_code=409, detail="handle 已存在")

    row = User(
        name=payload.get("name", handle),
        avatar=normalize_avatar_value(payload.get("avatar", "")),
        role="user",
        handle=handle,
        password=hash_password(password),
        owner_id=0,
        is_system=False,
        system_prompt="",
        raw_config="{}",
        expressiveness="balanced",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(
        db,
        current_admin.id,
        "admin.create_user",
        "user",
        str(row.id),
        payload={"role": "user"},
        request=request,
    )
    return {"message": "创建成功", "id": row.id}


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    if "name" in payload:
        row.name = payload["name"]
    if "avatar" in payload:
        row.avatar = normalize_avatar_value(payload["avatar"])
    if "handle" in payload:
        existed = (
            db.query(User)
            .filter(User.handle == payload["handle"], User.id != user_id)
            .first()
        )
        if existed:
            raise HTTPException(status_code=409, detail="handle 已存在")
        row.handle = payload["handle"]
    if "password" in payload and payload["password"]:
        row.password = hash_password(payload["password"])
    if "system_prompt" in payload:
        row.system_prompt = payload["system_prompt"]
    if "raw_config" in payload:
        row.raw_config = payload["raw_config"]
    if "expressiveness" in payload:
        row.expressiveness = payload["expressiveness"]
    if "is_system" in payload:
        row.is_system = bool(payload["is_system"])

    db.commit()
    log_action(
        db,
        current_admin.id,
        "admin.update_user",
        "user",
        str(row.id),
        payload={"keys": list(payload.keys())},
        request=request,
    )
    return {"message": "更新成功"}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    row = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    try:
        hard_delete_user(db, user_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    log_action(
        db, current_admin.id, "admin.delete_user", "user", str(user_id), request=request
    )
    return {"message": "删除成功（硬删除）"}
