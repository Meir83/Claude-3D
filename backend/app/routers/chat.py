"""
Chat router: handles streaming Claude responses and session management.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        assistant_content = ""
        job_id_created: str | None = None

        async for event in await stream_chat(history, provider=body.provider, model=body.model):
            if event.event == "delta":
                assistant_content += event.data
                yield event.to_sse()

            elif event.event == "code_extracted":
                script = event.data
                yield event.to_sse()

                # Validate and create job
                try:
                    validate_script(script)
                    job_id = str(uuid.uuid4())
                    script_hash = hashlib.sha256(script.encode()).hexdigest()

                    # Write script to disk before enqueueing
                    job_script_path(job_id).parent.mkdir(parents=True, exist_ok=True)
                    job_script_path(job_id).write_text(script, encoding="utf-8")

                    async with db.begin_nested():
                        job = GenerationJob(
                            id=job_id,
                            session_id=body.session_id,
                            status=JobStatus.pending,
                            script_hash=script_hash,
                            script_path=str(job_script_path(job_id)),
                        )
                        db.add(job)

                    await db.commit()
                    await job_queue.enqueue(job_id)
                    job_id_created = job_id
                    yield f"event: job_created\ndata: {json.dumps({'job_id': job_id})}\n\n"

                except SandboxViolation as exc:
                    yield f"event: sandbox_error\ndata: {json.dumps({'error': str(exc)})}\n\n"

            elif event.event == "done":
                # Persist assistant message
                if assistant_content:
                    async with db.begin():
                        asst_msg = ChatMessage(
                            session_id=body.session_id,
                            role=MessageRole.assistant,
                            content=assistant_content,
                        )
                        db.add(asst_msg)
                yield event.to_sse()

            elif event.event == "error":
                yield event.to_sse()

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
