from fastapi import APIRouter, HTTPException, Query

from app.core.crawler_jobs import (
    CrawlerConflictError,
    CrawlerJobError,
    CrawlerJobNotFoundError,
    SUPPORTED_SOURCES,
    crawler_job_manager,
)


router = APIRouter(prefix="/admin/crawler", tags=["admin-crawler"])


def _handle_job_error(exc: Exception) -> None:
    if isinstance(exc, CrawlerConflictError):
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "source": exc.source,
                "running_job_id": exc.job_id,
            },
        ) from exc
    if isinstance(exc, CrawlerJobNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, CrawlerJobError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{source}/jobs")
async def create_crawler_job(source: str):
    normalized_source = source.strip().lower()
    if normalized_source not in SUPPORTED_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported source: {source}; expected one of {sorted(SUPPORTED_SOURCES)}",
        )

    try:
        job = await crawler_job_manager.create_job(normalized_source)
        return {
            "code": 200,
            "message": "crawler job created",
            "data": {"job": job},
        }
    except Exception as exc:
        _handle_job_error(exc)


@router.get("/jobs")
async def list_crawler_jobs(
    source: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        jobs = await crawler_job_manager.list_jobs(source=source, limit=limit)
        return {
            "code": 200,
            "message": "ok",
            "data": {"jobs": jobs},
        }
    except Exception as exc:
        _handle_job_error(exc)


@router.get("/jobs/{job_id}")
async def get_crawler_job(job_id: str):
    try:
        job = await crawler_job_manager.get_job(job_id)
        return {
            "code": 200,
            "message": "ok",
            "data": {"job": job},
        }
    except Exception as exc:
        _handle_job_error(exc)


@router.get("/jobs/{job_id}/logs")
async def get_crawler_job_logs(
    job_id: str,
    tail: int = Query(default=200, ge=1, le=2000),
):
    try:
        logs = await crawler_job_manager.get_logs(job_id=job_id, tail=tail)
        return {
            "code": 200,
            "message": "ok",
            "data": {"logs": logs},
        }
    except Exception as exc:
        _handle_job_error(exc)


@router.post("/zhihu/run")
async def run_zhihu_crawler():
    return await create_crawler_job("zhihu")


@router.post("/weibo/run")
async def run_weibo_crawler():
    return await create_crawler_job("weibo")
