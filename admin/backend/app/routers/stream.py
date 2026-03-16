import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.deps import get_current_admin
from app.models import AdminUser


router = APIRouter(prefix="/admin", tags=["admin-stream"])

ALLOWED_CHANNELS = {"hotspots", "questions", "debates", "agents", "online"}


@router.get("/stream/{channel}")
async def stream_channel(
    channel: str,
    _: AdminUser = Depends(get_current_admin),
):
    channel = channel.strip().lower()
    if channel not in ALLOWED_CHANNELS:
        raise HTTPException(status_code=400, detail="invalid stream channel")

    async def _event_generator():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET",
                f"{settings.backend_base_url}/stream/{channel}",
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=body.decode("utf-8", errors="replace") or "stream upstream error",
                    )

                async for line in response.aiter_lines():
                    if line is None:
                        continue
                    yield f"{line}\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
