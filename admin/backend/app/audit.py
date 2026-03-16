import json
from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AdminAuditLog


def log_action(
    db: Session,
    admin_id: int,
    action: str,
    target_type: str = "system",
    target_id: str = "0",
    reason: str = "",
    payload: dict | None = None,
    request: Request | None = None,
):
    ip = ""
    if request is not None and request.client is not None:
        ip = request.client.host or ""

    row = AdminAuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        reason=reason,
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
        ip=ip,
    )
    db.add(row)
    db.commit()
