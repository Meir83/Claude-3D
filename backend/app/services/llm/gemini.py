"""Google Gemini provider adapter.

Uses the official `google-generativeai` SDK with streaming.
Gemini's API doesn't support a separate system role in the same way,
so we prepend the system prompt as the first user turn + model ack.
"""
from __future__ import annotations

from typing import AsyncIterator

from app.config import settings
from app.services.llm.base import StreamEvent, SYSTEM_PROMPT, extract_cq_script


def _build_gemini_messages(messages: list[dict[str, str]]) -> list[dict]:
    """
    Convert OpenAI-style messages to Gemini's format.

    Gemini roles: "user" and "model" (not "assistant").
    We inject the system prompt as the first user/model exchange.
    """
    gemini_msgs: list[dict] = [
        {"role": "user",  "parts": [SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Understood. I will follow these guidelines to generate parametric 3D models using CadQuery."]},
    ]
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        gemini_msgs.append({"role": role, "parts": [m["content"]]})
    return gemini_msgs


async def stream(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> AsyncIterator[StreamEvent]:
    if not settings.gemini_api_key:
        yield StreamEvent("error", "GEMINI_API_KEY is not set.")
        return

    try:
        import google.generativeai as genai  # type: ignore[import-untyped]
        import asyncio
    except ImportError:
        yield StreamEvent("error", "google-generativeai package not installed. Run: pip install google-generativeai")
        return

    genai.configure(api_key=settings.gemini_api_key)
    used_model = model or settings.gemini_model

    full_response = ""

    try:
        gmodel = genai.GenerativeModel(used_model)
        gemini_messages = _build_gemini_messages(messages)

        # genai streaming is synchronous; run in executor to avoid blocking
        loop = asyncio.get_event_loop()

        def _run_stream():
            return gmodel.generate_content(
                gemini_messages,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=8192,
                    temperature=0.7,
                ),
            )

        response_stream = await loop.run_in_executor(None, _run_stream)

        def _iter_chunks():
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

        # Stream chunks
        for text in _iter_chunks():
            full_response += text
            yield StreamEvent("delta", text)

        script = extract_cq_script(full_response)
        if script:
            yield StreamEvent("code_extracted", script)
        yield StreamEvent("done", "")

    except Exception as exc:
        # Catch google.api_core.exceptions too
        msg = str(exc)
        if "API_KEY_INVALID" in msg or "API key not valid" in msg:
            yield StreamEvent("error", "Invalid Gemini API key.")
        elif "quota" in msg.lower() or "rate" in msg.lower():
            yield StreamEvent("error", "Gemini rate limit reached.")
        else:
            yield StreamEvent("error", f"Gemini error: {msg}")
