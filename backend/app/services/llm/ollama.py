"""Ollama provider adapter — local, free, no API key required.

Uses Ollama's OpenAI-compatible streaming API via httpx.
Ollama must be running locally: https://ollama.ai

Quick start:
    ollama pull codellama   # or llama3.1, qwen2.5-coder, etc.
    ollama serve            # starts on http://localhost:11434
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from app.config import settings
from app.services.llm.base import StreamEvent, SYSTEM_PROMPT, extract_cq_script


async def stream(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> AsyncIterator[StreamEvent]:
    used_model = model or settings.ollama_model
    base_url = settings.ollama_base_url.rstrip("/")

    # Prepend system message
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    full_response = ""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Check Ollama is reachable
            try:
                await client.get(f"{base_url}/api/tags", timeout=3.0)
            except (httpx.ConnectError, httpx.TimeoutException):
                yield StreamEvent(
                    "error",
                    f"Cannot connect to Ollama at {base_url}. "
                    "Is Ollama running? Start with: ollama serve"
                )
                return

            # OpenAI-compatible streaming endpoint
            async with client.stream(
                "POST",
                f"{base_url}/v1/chat/completions",
                json={
                    "model": used_model,
                    "messages": full_messages,
                    "stream": True,
                    "options": {
                        "num_ctx": 8192,
                        "temperature": 0.7,
                    },
                },
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status_code == 404:
                    yield StreamEvent(
                        "error",
                        f"Model '{used_model}' not found in Ollama. "
                        f"Pull it with: ollama pull {used_model}"
                    )
                    return

                if response.status_code != 200:
                    body = await response.aread()
                    yield StreamEvent("error", f"Ollama error {response.status_code}: {body.decode()[:200]}")
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        text = chunk["choices"][0]["delta"].get("content", "")
                        if text:
                            full_response += text
                            yield StreamEvent("delta", text)
                    except (json.JSONDecodeError, KeyError):
                        continue

        script = extract_cq_script(full_response)
        if script:
            yield StreamEvent("code_extracted", script)
        yield StreamEvent("done", "")

    except httpx.ReadTimeout:
        yield StreamEvent("error", f"Ollama timed out generating with model '{used_model}'. Try a smaller model.")
    except Exception as exc:
        yield StreamEvent("error", f"Ollama error: {exc}")
