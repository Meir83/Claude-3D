"""
Providers router: lists available LLM providers and their availability status.
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.llm.base import PROVIDERS

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


async def _check_ollama() -> bool:
    """Return True if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def _get_ollama_models() -> list[str]:
    """Return list of models pulled in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            data = r.json()
            return [m["name"].split(":")[0] for m in data.get("models", [])]
    except Exception:
        return []


@router.get("")
async def list_providers() -> JSONResponse:
    """
    Return all providers with their availability status.
    Availability:
      - claude:  has ANTHROPIC_API_KEY set
      - gemini:  has GEMINI_API_KEY set
      - ollama:  Ollama HTTP server is reachable
    """
    ollama_available, ollama_models = await asyncio.gather(
        _check_ollama(),
        _get_ollama_models(),
    )

    result = {}
    for key, meta in PROVIDERS.items():
        available = False
        if key == "claude":
            available = bool(settings.anthropic_api_key)
        elif key == "gemini":
            available = bool(settings.gemini_api_key)
        elif key == "ollama":
            available = ollama_available

        # For Ollama, override model list with actually-pulled models
        models = meta["models"]
        if key == "ollama" and ollama_models:
            models = [
                {"id": m, "name": m, "default": m == ollama_models[0]}
                for m in ollama_models
            ]

        result[key] = {
            **meta,
            "available": available,
            "models": models,
            "default_model": (
                settings.claude_model if key == "claude"
                else settings.gemini_model if key == "gemini"
                else settings.ollama_model
            ),
        }

    return JSONResponse(result)
