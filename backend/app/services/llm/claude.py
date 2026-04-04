"""Claude (Anthropic) provider adapter."""
from __future__ import annotations

from typing import AsyncIterator

import anthropic

from app.config import settings
from app.services.llm.base import StreamEvent, SYSTEM_PROMPT, extract_cq_script


async def stream(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> AsyncIterator[StreamEvent]:
    if not settings.anthropic_api_key:
        yield StreamEvent("error", "ANTHROPIC_API_KEY is not set.")
        return

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    used_model = model or settings.claude_model
    full_response = ""

    try:
        async with client.messages.stream(
            model=used_model,
            max_tokens=settings.claude_max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as s:
            async for text in s.text_stream:
                full_response += text
                yield StreamEvent("delta", text)

        script = extract_cq_script(full_response)
        if script:
            yield StreamEvent("code_extracted", script)
        yield StreamEvent("done", "")

    except anthropic.AuthenticationError:
        yield StreamEvent("error", "Invalid Anthropic API key.")
    except anthropic.RateLimitError:
        yield StreamEvent("error", "Anthropic rate limit reached. Please wait.")
    except anthropic.APIError as exc:
        yield StreamEvent("error", f"Claude API error: {exc}")
    except Exception as exc:
        yield StreamEvent("error", f"Unexpected error: {exc}")
