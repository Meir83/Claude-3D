"""
Shared types and utilities for all LLM providers.
"""
from __future__ import annotations

import re
from pathlib import Path

# ── System prompt (loaded once) ──────────────────────────────────────────────

_SKILL_MD_PATH = Path(__file__).resolve().parents[4] / "SKILL.md"
_DESIGN_REVIEW_PATH = Path(__file__).resolve().parents[4] / "design-review.md"


def _load_system_prompt() -> str:
    parts: list[str] = []
    if _SKILL_MD_PATH.exists():
        parts.append(_SKILL_MD_PATH.read_text())
    if _DESIGN_REVIEW_PATH.exists():
        parts.append("\n\n---\n\n")
        parts.append(_DESIGN_REVIEW_PATH.read_text())
    return "".join(parts)


SYSTEM_PROMPT = _load_system_prompt()

# ── Code extraction ──────────────────────────────────────────────────────────

_CODE_BLOCK_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def extract_cq_script(text: str) -> str | None:
    """Return the last ```python``` block in text, if any."""
    matches = _CODE_BLOCK_RE.findall(text)
    return matches[-1].strip() if matches else None


# ── SSE event type ────────────────────────────────────────────────────────────

class StreamEvent:
    """Typed SSE event yielded by every provider adapter."""

    __slots__ = ("event", "data")

    def __init__(self, event: str, data: str) -> None:
        self.event = event
        self.data = data

    def to_sse(self) -> str:
        return f"event: {self.event}\ndata: {self.data}\n\n"


# ── Provider metadata ─────────────────────────────────────────────────────────

PROVIDERS: dict[str, dict] = {
    "claude": {
        "name": "Claude (Anthropic)",
        "models": [
            {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (Recommended)", "default": True},
            {"id": "claude-opus-4-6",   "name": "Claude Opus 4.6"},
            {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5"},
        ],
        "requires_key": True,
        "key_env": "ANTHROPIC_API_KEY",
        "free": False,
    },
    "gemini": {
        "name": "Gemini (Google)",
        "models": [
            {"id": "gemini-2.0-flash",   "name": "Gemini 2.0 Flash (Recommended)", "default": True},
            {"id": "gemini-1.5-pro",     "name": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-flash",   "name": "Gemini 1.5 Flash"},
        ],
        "requires_key": True,
        "key_env": "GEMINI_API_KEY",
        "free": False,
    },
    "ollama": {
        "name": "Ollama (Local / Free)",
        "models": [
            {"id": "codellama",         "name": "CodeLlama 7B", "default": True},
            {"id": "llama3.1",          "name": "Llama 3.1 8B"},
            {"id": "qwen2.5-coder",     "name": "Qwen 2.5 Coder 7B"},
            {"id": "deepseek-coder-v2", "name": "DeepSeek Coder V2"},
        ],
        "requires_key": False,
        "key_env": None,
        "free": True,
    },
}
