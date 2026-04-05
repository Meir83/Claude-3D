"""
Jobs router: job status polling and SSE event stream.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import GenerationJob
from app.schemas.job import JobOut, JobListOut
from app.services.job_queue import job_queue
from app.utils.rate_limit import limiter

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)) -> JobOut:
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.from_orm(job)


@router.get("/{job_id}/events")
@limiter.limit("60/minute")
async def job_events(
    job_id: str, request: Request, db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """
    SSE stream for a single job's status transitions.
    Sends the current state immediately, then waits for changes.
    Terminates when the job reaches a terminal state (done/error).
    """
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # Send initial state
        current_job = job
        yield f"event: status\ndata: {json.dumps(JobOut.from_orm(current_job).model_dump(mode='json'))}\n\n"

        while current_job.status not in ("done", "error"):
            if await request.is_disconnected():
                break

            changed = await job_queue.wait_for_update(job_id, timeout=25.0)
            if not changed:
                # Heartbeat to keep the connection alive
                yield "event: heartbeat\ndata: {}\n\n"
                continue

            # Refresh from DB
            async with db.begin():
                r = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
                current_job = r.scalar_one_or_none()
                if not current_job:
                    break

            yield f"event: status\ndata: {json.dumps(JobOut.from_orm(current_job).model_dump(mode='json'))}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("", response_model=JobListOut)
async def list_jobs(
    session_id: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> JobListOut:
    count_result = await db.execute(
        select(func.count(GenerationJob.id)).where(
            GenerationJob.session_id == session_id
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(GenerationJob)
        .where(GenerationJob.session_id == session_id)
        .order_by(GenerationJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = result.scalars().all()
    return JobListOut(
        items=[JobOut.from_orm(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )
