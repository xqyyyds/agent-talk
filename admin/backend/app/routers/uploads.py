import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import settings
from app.deps import get_current_admin
from app.models import AdminUser


router = APIRouter(prefix="/admin/uploads", tags=["admin-uploads"])


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    _: AdminUser = Depends(get_current_admin),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="头像文件不能为空")

    filename = file.filename or "avatar"
    content_type = file.content_type or "application/octet-stream"

    try:
        response = httpx.post(
            f"{settings.backend_base_url}/internal/avatar/upload",
            files={"file": (filename, content, content_type)},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="头像上传失败") from exc

    data = payload.get("data") or {}
    avatar = str(data.get("avatar") or "").strip()
    if not avatar:
        raise HTTPException(status_code=502, detail="头像上传失败")

    return {"code": 200, "data": {"avatar": avatar}}
