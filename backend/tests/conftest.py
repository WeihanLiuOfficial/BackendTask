"""Pytest fixtures for async testing.

Provides reusable fixtures for:
- An async test database session (using a test-specific PostgreSQL schema).
- A mock OpenAI client for deterministic AI agent testing.
- A configured FastAPI test client via httpx.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest_asyncio.fixture
async def async_client():
    """Yield an async HTTP client bound to the FastAPI application.

    This allows tests to make real HTTP requests against the API
    without starting Uvicorn.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# TODO: Add fixture for test database session (override get_db_session dependency)
# TODO: Add fixture for mock OpenAI client (override get_openai_client dependency)
