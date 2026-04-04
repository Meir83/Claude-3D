"""
Claude API streaming service.

Streams the assistant response, extracts embedded CadQuery code blocks,
and yields typed SSE-compatible events.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import AsyncIterator

import anthropic

from app.config import settings

# Load SKILL.md once at import time
_SKILL_MD_PATH = Path(__file__).resolve().parents[3] / "SKILL.md"
_DESIGN_REVIEW_PATH = Path(__file__).resolve().parents[3] / "design-review.md"


def _load_system_prompt() -> str:
    parts: list[str] = []
    if _SKILL_MD_PATH.exists():
        parts.append(_SKILL_MD_PATH.read_text())
    if _DESIGN_REVIEW_PATH.exists():
        parts.append("\n\n---\n\n")
        parts.append(_DESIGN_REVIEW_PATH.read_text())
    return "".join(parts)


SYSTEM_PROMPT = _load_system_prompt()

# Regex: fenced python code block (```python ... ```)
_CODE_BLOCK_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def extract_cq_script(text: str) -> str | None:
    """Return the last ```python``` block in text, if any."""
    matches = _CODE_BLOCK_RE.findall(text)
    return matches[-1].strip() if matches else None


class StreamEvent:
    """Typed SSE event."""

    __slots__ = ("event", "data")

    def __init__(self, event: str, data: str) -> None:
        self.event = event
        self.data = data

    def to_sse(self) -> str:
        return f"event: {self.event}\ndata: {self.data}\n\n"


async def stream_chat(
    messages: list[dict[str, str]],
) -> AsyncIterator[StreamEvent]:
    """
    Stream a Claude response for the given message history.

    Yields:
        StreamEvent(event="delta", data=<text chunk>)
        StreamEvent(event="code_extracted", data=<python script>)  — once, at end
        StreamEvent(event="done", data="")
        StreamEvent(event="error", data=<message>)  — on failure
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    full_response = ""

    try:
        async with client.messages.stream(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                full_response += text
                yield StreamEvent("delta", text)

        # After stream completes, extract any CadQuery script
        script = extract_cq_script(full_response)
        if script:
            yield StreamEvent("code_extracted", script)

        yield StreamEvent("done", "")

    except anthropic.AuthenticationError:
        yield StreamEvent("error", "Invalid Anthropic API key. Check your ANTHROPIC_API_KEY.")
    except anthropic.RateLimitError:
        yield StreamEvent("error", "Rate limit reached. Please wait a moment.")
    except anthropic.APIError as exc:
        yield StreamEvent("error", f"Claude API error: {exc}")
    except Exception as exc:
        yield StreamEvent("error", f"Unexpected error: {exc}")
