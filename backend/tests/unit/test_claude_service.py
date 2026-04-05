"""Tests for the Claude streaming service."""
import pytest
from app.services.claude import extract_cq_script, stream_chat, StreamEvent


RESPONSE_WITH_CODE = """\
Here is a simple box:

```python
import cadquery as cq
result = cq.Workplane("XY").box(40, 30, 20, centered=(True, True, False))
```

This will create a 40×30×20mm box.
"""

RESPONSE_NO_CODE = "I understand you want a box. Could you provide more details?"

MULTI_CODE_RESPONSE = """\
First attempt:
```python
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
```

Updated version:
```python
import cadquery as cq
result = cq.Workplane("XY").box(40, 30, 20)
```
"""


def test_extract_script_finds_code():
    script = extract_cq_script(RESPONSE_WITH_CODE)
    assert script is not None
    assert "cadquery" in script
    assert "box" in script


def test_extract_script_no_code():
    assert extract_cq_script(RESPONSE_NO_CODE) is None


def test_extract_script_returns_last_block():
    """When multiple code blocks exist, return the last one."""
    script = extract_cq_script(MULTI_CODE_RESPONSE)
    assert script is not None
    assert "box(40, 30, 20)" in script


def test_stream_event_sse_format():
    event = StreamEvent("delta", "hello world")
    sse = event.to_sse()
    assert sse == "event: delta\ndata: hello world\n\n"


def test_stream_event_empty_data():
    event = StreamEvent("done", "")
    sse = event.to_sse()
    assert "event: done" in sse


@pytest.mark.asyncio
async def test_stream_chat_auth_error():
    """Test that an auth error yields an error event (not an exception)."""
    import os
    original = os.environ.get("ANTHROPIC_API_KEY", "")

    # Patch settings to use invalid key
    from app.config import settings
    original_key = settings.anthropic_api_key
    settings.anthropic_api_key = "sk-invalid-key-for-testing"

    try:
        events = []
        async for event in stream_chat([{"role": "user", "content": "test"}]):
            events.append(event)
            if event.event in ("error", "done"):
                break

        assert any(e.event == "error" for e in events)
    finally:
        settings.anthropic_api_key = original_key
