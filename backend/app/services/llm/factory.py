"""
Provider factory: route to the right LLM adapter based on provider name.
"""
from __future__ import annotations

from typing import AsyncIterator

from app.services.llm import claude, gemini, ollama
from app.services.llm.base import StreamEvent

_ADAPTERS = {
    "claude": claude.stream,
    "gemini": gemini.stream,
    "ollama": ollama.stream,
}


async def stream_chat(
    messages: list[dict[str, str]],
    provider: str = "claude",
    model: str | None = None,
) -> AsyncIterator[StreamEvent]:
    """
    Dispatch to the correct provider adapter.
    Falls back to yielding an error event for unknown providers.
    """
    adapter = _ADAPTERS.get(provider)
    if adapter is None:
        async def _unknown():
            yield StreamEvent("error", f"Unknown provider '{provider}'. Choose: {list(_ADAPTERS)}")
        return _unknown()

    return adapter(messages, model=model)
