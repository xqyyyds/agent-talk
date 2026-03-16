from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.deps import get_current_admin
from app.models import AdminUser
from app.schemas import (
    ChangePasswordRequest,
    ChangeUsernameRequest,
    LoginRequest,
    TokenResponse,
)
from app.security import create_access_token, verify_password, hash_password


router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=TokenResponse)
def admin_login(
    payload: LoginRequest, db: Session = Depends(get_db), request: Request = None
):
    admin = db.query(AdminUser).filter(AdminUser.username == payload.username).first()
    if not admin or admin.status != "active":
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    token = create_access_token(str(admin.id))
    log_action(
        db,
        admin.id,
        "admin.login",
        payload={"username": admin.username},
        request=request,
    )
    return TokenResponse(access_token=token)


@router.get("/me")
def get_me(current_admin: AdminUser = Depends(get_current_admin)):
    return {
        "id": current_admin.id,
        "username": current_admin.username,
        "status": current_admin.status,
        "created_at": current_admin.created_at,
    }


@router.patch("/me/username")
def change_my_username(
    payload: ChangeUsernameRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    existed = (
        db.query(AdminUser).filter(AdminUser.username == payload.new_username).first()
    )
    if existed and existed.id != current_admin.id:
        raise HTTPException(status_code=409, detail="用户名已存在")

    old_name = current_admin.username
    current_admin.username = payload.new_username
    db.commit()

    log_action(
        db,
        current_admin.id,
        "admin.change_username",
        target_type="admin_user",
        target_id=str(current_admin.id),
        payload={"from": old_name, "to": payload.new_username},
        request=request,
    )

    return {"message": "用户名修改成功"}


@router.patch("/me/password")
def change_my_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    request: Request = None,
):
    if not verify_password(payload.old_password, current_admin.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    current_admin.password_hash = hash_password(payload.new_password)
    db.commit()

    log_action(
        db,
        current_admin.id,
        "admin.change_password",
        target_type="admin_user",
        target_id=str(current_admin.id),
        request=request,
    )

    return {"message": "密码修改成功"}
