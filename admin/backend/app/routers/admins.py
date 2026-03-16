from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.deps import get_current_admin
from app.models import AdminUser
from app.schemas import AdminUserCreate, AdminUserUpdate
from app.security import hash_password


router = APIRouter(prefix="/admin/admin-users", tags=["admin-users"])


@router.get("")
def list_admin_users(
    db: Session = Depends(get_db), _: AdminUser = Depends(get_current_admin)
):
    rows = db.query(AdminUser).order_by(AdminUser.id.desc()).all()
    return [
        {
            "id": r.id,
            "username": r.username,
            "status": r.status,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


@router.post("")
def create_admin_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    existed = db.query(AdminUser).filter(AdminUser.username == payload.username).first()
    if existed:
        raise HTTPException(status_code=409, detail="用户名已存在")

    row = AdminUser(
        username=payload.username,
        password_hash=hash_password(payload.password),
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(
        db,
        current_admin.id,
        "admin.create_admin_user",
        target_type="admin_user",
        target_id=str(row.id),
        payload={"username": row.username},
        request=request,
    )

    return {"message": "管理员创建成功", "id": row.id}


@router.patch("/{admin_id}")
def update_admin_user(
    admin_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    target = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if payload.username:
        existed = (
            db.query(AdminUser)
            .filter(AdminUser.username == payload.username, AdminUser.id != admin_id)
            .first()
        )
        if existed:
            raise HTTPException(status_code=409, detail="用户名已存在")
        target.username = payload.username

    if payload.status in ("active", "disabled"):
        if admin_id == current_admin.id and payload.status != "active":
            raise HTTPException(status_code=400, detail="不能禁用自己")
        target.status = payload.status

    db.commit()
    log_action(
        db,
        current_admin.id,
        "admin.update_admin_user",
        target_type="admin_user",
        target_id=str(target.id),
        payload={"username": target.username, "status": target.status},
        request=request,
    )
    return {"message": "更新成功"}


@router.delete("/{admin_id}")
def delete_admin_user(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    if admin_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    total_active = db.query(AdminUser).filter(AdminUser.status == "active").count()
    target = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="管理员不存在")
    if target.status == "active" and total_active <= 1:
        raise HTTPException(status_code=400, detail="至少保留一个可用管理员")

    db.delete(target)
    db.commit()

    log_action(
        db,
        current_admin.id,
        "admin.delete_admin_user",
        target_type="admin_user",
        target_id=str(admin_id),
        request=request,
    )
    return {"message": "删除成功"}
