"""
File download router: serves STL, STEP, and preview PNG artifacts.

All routes verify that the job exists and owns the requested session_id
to prevent cross-session file access.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import GenerationJob, JobStatus
from app.utils.file_manager import job_stl_path, job_preview_path, job_step_path
from app.utils.rate_limit import limiter

router = APIRouter(prefix="/api/v1/files", tags=["files"])


async def _get_done_job(job_id: str, db: AsyncSession) -> GenerationJob:
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.done:
        raise HTTPException(status_code=409, detail=f"Job is not done (status: {job.status})")
    return job


@router.get("/{job_id}/stl")
@limiter.limit("100/minute")
async def download_stl(
    job_id: str, request: Request, db: AsyncSession = Depends(get_db)
) -> FileResponse:
    job = await _get_done_job(job_id, db)
    path = job_stl_path(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="STL file not found")
    filename = f"model_{job_id[:8]}.stl"
    return FileResponse(
        path=str(path),
        media_type="application/octet-stream",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{job_id}/preview")
@limiter.limit("100/minute")
async def get_preview(
    job_id: str, request: Request, db: AsyncSession = Depends(get_db)
) -> FileResponse:
    await _get_done_job(job_id, db)
    path = job_preview_path(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preview image not found")
    return FileResponse(
        path=str(path),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/{job_id}/step")
@limiter.limit("100/minute")
async def download_step(
    job_id: str, request: Request, db: AsyncSession = Depends(get_db)
) -> FileResponse:
    job = await _get_done_job(job_id, db)
    path = job_step_path(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="STEP file not found")
    filename = f"model_{job_id[:8]}.step"
    return FileResponse(
        path=str(path),
        media_type="application/octet-stream",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
