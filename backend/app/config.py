from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Anthropic / Claude ───────────────────────────────────────────────────
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 8192

    # ── Google Gemini ────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── Ollama (local / free) ────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "codellama"

    # ── Default provider ─────────────────────────────────────────────────────
    # Resolved at startup: first provider whose key/service is available.
    # Can be overridden per-request.
    default_provider: str = "claude"

    # ── Server ───────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/storage/claude3d.db"

    # ── Storage ──────────────────────────────────────────────────────────────
    storage_dir: Path = BASE_DIR / "storage" / "jobs"

    # ── Execution sandbox ────────────────────────────────────────────────────
    script_timeout_seconds: int = 60
    max_script_size_bytes: int = 51200         # 50 KB
    max_stl_size_bytes: int = 52428800         # 50 MB
    max_virtual_memory_bytes: int = 536870912  # 512 MB

    # ── Rate limiting ────────────────────────────────────────────────────────
    chat_rate_limit: str = "10/minute"
    download_rate_limit: str = "100/minute"

    # ── Queue ────────────────────────────────────────────────────────────────
    worker_concurrency: int = 2


settings = Settings()
