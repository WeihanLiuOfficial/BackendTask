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


def get_openai_client() -> AsyncOpenAI:
    """Return a configured async OpenAI client instance.

    Uses the API key from validated pydantic-settings configuration.
    """
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
