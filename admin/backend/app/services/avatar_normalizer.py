import httpx

from app.config import settings


def normalize_avatar_value(avatar: str) -> str:
    raw = str(avatar or "").strip()
    if not raw:
        return ""
    if not raw.startswith("data:"):
        return _canonicalize_avatar(raw)

    try:
        response = httpx.post(
            f"{settings.backend_base_url}/internal/avatar/ingest",
            json={"avatar": raw},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        normalized = str(data.get("avatar") or "").strip()
        return _canonicalize_avatar(normalized)
    except Exception:
        return ""


def _canonicalize_avatar(avatar: str) -> str:
    if avatar.startswith("/api/uploads/"):
        return avatar
    if avatar.startswith("/uploads/"):
        return f"/api{avatar}"
    if avatar.startswith("uploads/"):
        return f"/api/{avatar}"
    return avatar
