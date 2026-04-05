"""
Background worker: consumes the job queue, runs CadQuery execution + preview rendering.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.job import GenerationJob, JobStatus
from app.services.executor import execute_script
from app.services.job_queue import job_queue
from app.services.renderer import render_preview

logger = logging.getLogger(__name__)


async def _process_job(job_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.warning("Job %s not found in DB", job_id)
            return

        # Mark running
        job.status = JobStatus.running
        job.started_at = datetime.utcnow()
        await db.commit()
        job_queue.notify(job_id)

        # Read script from disk
        from app.utils.file_manager import job_script_path  # noqa: PLC0415
        script_path = job_script_path(job_id)

        # The script was written by the router before enqueuing.
        # We run only the original script — the executor wraps it.
        try:
            script_content = script_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            job.status = JobStatus.error
            job.error_message = "Script file missing"
            job.finished_at = datetime.utcnow()
            await db.commit()
            job_queue.notify(job_id)
            return

        # Execute
        exec_result = await execute_script(script_content, job_id)

        if not exec_result.success:
            job.status = JobStatus.error
            job.error_message = (
                exec_result.stderr[:2000] if exec_result.stderr else "Execution failed"
            )
            job.execution_time_ms = exec_result.execution_time_ms
            job.finished_at = datetime.utcnow()
            await db.commit()
            job_queue.notify(job_id)
            return

        # Update artifact paths
        from app.utils.file_manager import (  # noqa: PLC0415
            job_stl_path,
            job_preview_path,
            job_step_path,
        )

        job.stl_path = str(job_stl_path(job_id)) if exec_result.stl_exists else None
        job.step_path = str(job_step_path(job_id)) if exec_result.step_exists else None
        job.execution_time_ms = exec_result.execution_time_ms

        # Render preview
        preview_ok = await render_preview(job_id)
        if preview_ok:
            job.preview_path = str(job_preview_path(job_id))

        job.status = JobStatus.done
        job.finished_at = datetime.utcnow()
        await db.commit()
        job_queue.notify(job_id)
        logger.info("Job %s done in %dms", job_id, exec_result.execution_time_ms)


async def worker_loop(worker_id: int) -> None:
    """Runs forever, processing jobs from the queue."""
    logger.info("CAD worker %d started", worker_id)
    while True:
        job_id = await job_queue.dequeue()
        try:
            await _process_job(job_id)
        except Exception as exc:
            logger.exception("Worker %d: unhandled error on job %s: %s", worker_id, job_id, exc)
        finally:
            job_queue.task_done()


async def start_workers() -> None:
    """Start worker_concurrency background worker tasks."""
    for i in range(settings.worker_concurrency):
        asyncio.create_task(worker_loop(i))
