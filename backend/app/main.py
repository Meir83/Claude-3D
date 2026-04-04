from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import create_tables
from app.routers import chat, jobs, files
from app.utils.rate_limit import limiter
from app.workers.cad_worker import start_workers

logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    await create_tables()
    await start_workers()
    logger.info("Claude-3D backend started")
    yield
    # Shutdown (no-op for asyncio queue workers)
    logger.info("Claude-3D backend shutting down")


app = FastAPI(
    title="Claude-3D API",
    description="CAD model generation via Claude + CadQuery",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── Middleware ──────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Routers ─────────────────────────────────────────────────────────────────

app.include_router(chat.router)
app.include_router(jobs.router)
app.include_router(files.router)


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/health", tags=["health"])
async def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "version": "0.1.0",
        "queue_depth": app.state.limiter._storage._storage.__class__.__name__
        if hasattr(app.state, "limiter") else "unknown",
    })
