"""
Shared pytest fixtures for backend tests.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.main import app

# ── In-memory SQLite for tests ──────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncIterator[AsyncSession]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="session")
async def setup_test_db():
    """Create all tables once per test session."""
    from app.models import job, message, session as session_model  # noqa: F401
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_test_db) -> AsyncIterator[AsyncSession]:
    """Per-test database session, rolled back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(setup_test_db) -> AsyncIterator[AsyncClient]:
    """HTTP test client with test DB override."""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def session_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def mock_claude_response():
    """A fixture script that a mocked Claude API would return."""
    return '''\
Here is a simple box:

```python
import cadquery as cq

width = 40.0
depth = 30.0
height = 20.0

result = (
    cq.Workplane("XY")
    .box(width, depth, height, centered=(True, True, False))
)

cq.exporters.export(result, "output.stl")
```

This creates a 40×30×20mm box.
'''
