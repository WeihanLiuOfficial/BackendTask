"""FastAPI dependency injection providers.

This module defines reusable dependencies for database sessions and
the OpenAI client. These are injected into route handlers via FastAPI's
Depends() mechanism, ensuring proper resource lifecycle management.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.models.database import async_session_factory
from app.config import settings


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session and ensure it is closed after use.

    This dependency is injected into route handlers that require
    database access. The session is automatically committed on success
    or rolled back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── OpenAI Client Singleton ────────────────────────
# Created once at module load. The AsyncOpenAI client manages its own
# internal httpx connection pool — reusing a single instance avoids
# the overhead of establishing new TCP connections on every request.
_openai_client: AsyncOpenAI = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def get_openai_client() -> AsyncOpenAI:
    """Return the shared async OpenAI client singleton.

    The client is created once at module import time and reused
    across all requests to maximize connection pool efficiency.
    """
    return _openai_client
