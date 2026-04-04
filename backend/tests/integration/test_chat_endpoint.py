"""Integration tests for the chat streaming endpoint."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.claude import StreamEvent


def make_mock_stream(content: str):
    """Create an async generator that yields streaming events like the real Claude service."""
    async def _gen(messages):
        yield StreamEvent("delta", content)
        from app.services.claude import extract_cq_script  # noqa: PLC0415
        script = extract_cq_script(content)
        if script:
            yield StreamEvent("code_extracted", script)
        yield StreamEvent("done", "")
    return _gen


@pytest.mark.asyncio
async def test_chat_stream_returns_sse(client, session_id, mock_claude_response):
    """POST /chat/stream should return SSE with delta events."""
    mock_gen = make_mock_stream(mock_claude_response)

    with patch("app.routers.chat.stream_chat", side_effect=mock_gen):
        response = await client.post(
            "/api/v1/chat/stream",
            json={"session_id": session_id, "message": "make me a box"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    assert "event: delta" in body
    assert "event: done" in body


@pytest.mark.asyncio
async def test_chat_stream_creates_job(client, session_id, mock_claude_response):
    """When Claude returns a code block, a job_created event should appear."""
    mock_gen = make_mock_stream(mock_claude_response)

    with patch("app.routers.chat.stream_chat", side_effect=mock_gen):
        with patch("app.routers.chat.job_queue") as mock_queue:
            mock_queue.enqueue = AsyncMock()
            response = await client.post(
                "/api/v1/chat/stream",
                json={"session_id": session_id, "message": "make me a box"},
            )

    body = response.text
    assert "event: job_created" in body

    # Extract job_id from the event
    for line in body.split("\n"):
        if line.startswith("data:") and "job_id" in line:
            data = json.loads(line[5:].strip())
            assert "job_id" in data
            break


@pytest.mark.asyncio
async def test_chat_stream_invalid_session_id(client):
    """Invalid session_id should return 422."""
    response = await client.post(
        "/api/v1/chat/stream",
        json={"session_id": "not-a-uuid", "message": "test"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_empty_message(client, session_id):
    """Empty message should return 422."""
    response = await client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "message": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    response = await client.get(f"/api/v1/chat/{uuid.uuid4()}")
    assert response.status_code == 404
