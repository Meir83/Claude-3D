"""Integration tests for the chat streaming endpoint."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm import StreamEvent, extract_cq_script


def make_mock_stream(*contents: str):
    """
    Stand-in for app.services.llm.stream_chat. Each call returns the next
    canned response as a provider-style event stream. Records the messages
    it was called with on `.calls`.
    """
    responses = list(contents)
    calls: list[list[dict]] = []

    async def _stream_chat(messages, provider="claude", model=None):
        calls.append(list(messages))
        content = responses[min(len(calls), len(responses)) - 1]

        async def _gen():
            yield StreamEvent("delta", content)
            script = extract_cq_script(content)
            if script:
                yield StreamEvent("code_extracted", script)
            yield StreamEvent("done", "")

        return _gen()

    _stream_chat.calls = calls
    return _stream_chat


def sse_events(body: str) -> list[tuple[str, str]]:
    events = []
    for block in body.split("\n\n"):
        name, data = None, ""
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        if name:
            events.append((name, data))
    return events


@pytest.mark.asyncio
async def test_chat_stream_returns_sse(client, session_id):
    """POST /chat/stream should return SSE with delta events."""
    with patch("app.routers.chat.stream_chat", new=make_mock_stream("Hello, what size?")):
        response = await client.post(
            "/api/v1/chat/stream",
            json={"session_id": session_id, "message": "make me a box"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    names = [name for name, _ in sse_events(response.text)]
    assert "delta" in names
    assert names[-1] == "done"


@pytest.mark.asyncio
async def test_chat_stream_creates_job(client, session_id, mock_claude_response):
    """When the model returns a code block, a job_created event should appear."""
    with patch("app.routers.chat.stream_chat", new=make_mock_stream(mock_claude_response)), \
         patch("app.routers.chat.job_queue") as mock_queue, \
         patch("app.routers.chat._wait_for_job_failure", new=AsyncMock(return_value=None)):
        mock_queue.enqueue = AsyncMock()
        response = await client.post(
            "/api/v1/chat/stream",
            json={"session_id": session_id, "message": "make me a box"},
        )

    created = [json.loads(d) for name, d in sse_events(response.text) if name == "job_created"]
    assert len(created) == 1
    assert uuid.UUID(created[0]["job_id"])
    mock_queue.enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_build_is_sent_back_for_repair(client, session_id, mock_claude_response):
    """A failed build feeds the error back to the model, which gets another try."""
    stream = make_mock_stream(mock_claude_response, mock_claude_response)
    wait = AsyncMock(side_effect=["StdFail_NotDone: BRep_API: command not done", None])

    with patch("app.routers.chat.stream_chat", new=stream), \
         patch("app.routers.chat.job_queue") as mock_queue, \
         patch("app.routers.chat._wait_for_job_failure", new=wait):
        mock_queue.enqueue = AsyncMock()
        response = await client.post(
            "/api/v1/chat/stream",
            json={"session_id": session_id, "message": "make me a box"},
        )

    events = sse_events(response.text)
    names = [name for name, _ in events]
    assert names.count("job_created") == 2
    assert names.count("repair") == 1
    assert names[-1] == "done" and names.count("done") == 1

    repair = json.loads(next(d for n, d in events if n == "repair"))
    assert repair["attempt"] == 1
    assert "BRep_API" in repair["error"]

    # Second model call saw the first answer and the error as the latest user turn
    second_call = stream.calls[1]
    assert second_call[-2]["role"] == "assistant"
    assert second_call[-1]["role"] == "user"
    assert "BRep_API" in second_call[-1]["content"]


@pytest.mark.asyncio
async def test_repair_loop_stops_after_max_attempts(client, session_id, mock_claude_response):
    """The model is not asked to fix the script forever."""
    stream = make_mock_stream(mock_claude_response)
    wait = AsyncMock(return_value="still broken")

    with patch("app.routers.chat.stream_chat", new=stream), \
         patch("app.routers.chat.job_queue") as mock_queue, \
         patch("app.routers.chat._wait_for_job_failure", new=wait), \
         patch("app.routers.chat.settings.auto_repair_attempts", 2):
        mock_queue.enqueue = AsyncMock()
        response = await client.post(
            "/api/v1/chat/stream",
            json={"session_id": session_id, "message": "make me a box"},
        )

    names = [name for name, _ in sse_events(response.text)]
    assert names.count("repair") == 2
    assert len(stream.calls) == 3  # original + 2 repairs


@pytest.mark.asyncio
async def test_sandbox_violation_triggers_repair(client, session_id):
    """A script the sandbox rejects is also sent back for a fix."""
    evil = "```python\nimport cadquery as cq\nimport subprocess\nresult = cq.Workplane().box(1, 1, 1)\n```"
    stream = make_mock_stream(evil, "Sorry, fixed.")

    with patch("app.routers.chat.stream_chat", new=stream):
        response = await client.post(
            "/api/v1/chat/stream",
            json={"session_id": session_id, "message": "make me a box"},
        )

    names = [name for name, _ in sse_events(response.text)]
    assert "sandbox_error" in names
    assert "repair" in names
    assert "sandbox" in stream.calls[1][-1]["content"]


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
