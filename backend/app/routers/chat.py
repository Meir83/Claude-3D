"""
Chat router: handles streaming Claude responses and session management.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.job import GenerationJob, JobStatus
from app.models.message import ChatMessage, MessageRole
from app.models.session import ChatSession
from app.schemas.chat import ChatRequest, SessionOut
from app.services.llm import stream_chat
from app.services.job_queue import job_queue
from app.utils.file_manager import job_script_path
from app.utils.rate_limit import limiter
from app.utils.sandbox import validate_script, SandboxViolation

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


async def _get_or_create_session(session_id: str, db: AsyncSession) -> ChatSession:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        session = ChatSession(id=session_id)
        db.add(session)
        await db.flush()
    return session


async def _load_history(session_id: str, db: AsyncSession) -> list[dict[str, str]]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [{"role": m.role.value, "content": m.content} for m in messages]


async def _create_job(script: str, session_id: str, db: AsyncSession) -> str:
    """Validate a script, persist it as a pending job and enqueue it."""
    validate_script(script, max_bytes=settings.max_script_size_bytes)
    job_id = str(uuid.uuid4())
    script_path = job_script_path(job_id)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")

    db.add(GenerationJob(
        id=job_id,
        session_id=session_id,
        status=JobStatus.pending,
        script_hash=hashlib.sha256(script.encode()).hexdigest(),
        script_path=str(script_path),
    ))
    await db.commit()
    await job_queue.enqueue(job_id)
    return job_id


async def _wait_for_job_failure(job_id: str, db: AsyncSession) -> str | None:
    """
    Block until the job finishes. Returns its error message if it failed,
    or None if it succeeded (or did not finish in time).
    """
    deadline = time.monotonic() + settings.script_timeout_seconds + 90
    while time.monotonic() < deadline:
        result = await db.execute(
            select(GenerationJob.status, GenerationJob.error_message)
            .where(GenerationJob.id == job_id)
        )
        row = result.one_or_none()
        await db.commit()  # end the read transaction so the next poll sees fresh data
        if row is None:
            return None
        status, error = row
        if status == JobStatus.done:
            return None
        if status == JobStatus.error:
            return error or "Execution failed with no error output"
        await job_queue.wait_for_update(job_id, timeout=2.0)
    return None


def _repair_prompt(error: str, attempt: int, max_attempts: int) -> str:
    return (
        f"[Automatic build check {attempt}/{max_attempts}] The CadQuery script you just "
        "wrote failed to build. Error output:\n\n"
        f"```\n{error[-1500:]}\n```\n\n"
        "Find the root cause and reply with the complete corrected script in a single "
        "```python block. Keep all parameters and the final `result` variable. If a fillet, "
        "shell or loft failed, simplify that operation rather than guessing new values."
    )


@router.post("/stream")
@limiter.limit("10/minute")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream a Claude response. Returns SSE events:
      - delta: text chunk
      - code_extracted: CadQuery script was found (data = script text)
      - job_created: job ID created for the script (data = JSON {job_id})
      - sandbox_error: script rejected by static validation
      - repair: build failed, model is being asked to fix it (data = JSON {attempt, max_attempts, error})
      - done: stream finished
      - error: error message
    """
    session = await _get_or_create_session(body.session_id, db)

    # Persist user message
    user_msg = ChatMessage(
        session_id=body.session_id,
        role=MessageRole.user,
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    # Auto-title the session from the first message
    if not session.title:
        session.title = body.message[:80]

    history = await _load_history(body.session_id, db)
    await db.commit()

    async def event_generator():
        conversation = list(history)
        max_repairs = settings.auto_repair_attempts
        attempt = 0

        while True:
            assistant_content = ""
            job_id_created: str | None = None
            failure: str | None = None

            async for event in await stream_chat(conversation, provider=body.provider, model=body.model):
                if event.event == "delta":
                    assistant_content += event.data
                    yield event.to_sse()

                elif event.event == "code_extracted":
                    script = event.data
                    yield event.to_sse()

                    try:
                        job_id_created = await _create_job(script, body.session_id, db)
                        yield f"event: job_created\ndata: {json.dumps({'job_id': job_id_created})}\n\n"
                    except SandboxViolation as exc:
                        failure = f"Script rejected by sandbox: {exc}"
                        yield f"event: sandbox_error\ndata: {json.dumps({'error': str(exc)})}\n\n"

                elif event.event == "done":
                    if assistant_content:
                        db.add(ChatMessage(
                            session_id=body.session_id,
                            role=MessageRole.assistant,
                            content=assistant_content,
                        ))
                        await db.commit()

                elif event.event == "error":
                    yield event.to_sse()
                    yield "event: done\ndata: \n\n"
                    return

            conversation.append({"role": "assistant", "content": assistant_content})

            # Close the loop: wait for the build and feed errors back to the model
            # so it can fix its own script without the user copy-pasting tracebacks.
            if attempt >= max_repairs:
                break
            if job_id_created and failure is None:
                failure = await _wait_for_job_failure(job_id_created, db)
            if failure is None:
                break

            attempt += 1
            repair_prompt = _repair_prompt(failure, attempt, max_repairs)
            db.add(ChatMessage(
                session_id=body.session_id,
                role=MessageRole.user,
                content=repair_prompt,
            ))
            await db.commit()
            conversation.append({"role": "user", "content": repair_prompt})
            payload = {"attempt": attempt, "max_attempts": max_repairs, "error": failure[-500:]}
            yield f"event: repair\ndata: {json.dumps(payload)}\n\n"

        yield "event: done\ndata: \n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionOut:
    """Return session with full message history."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut.model_validate(session)
