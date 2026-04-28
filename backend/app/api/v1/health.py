"""Health check endpoint.

Provides a lightweight probe for Docker healthchecks and
external monitoring systems to verify API + database connectivity.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.dependencies import get_db_session

router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Verify API liveness and database connectivity.

    Executes a lightweight SELECT 1 against the database to confirm
    the connection pool is healthy and the database is responding.

    Returns:
        A JSON object with the API and database status.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "api": "healthy",
        "database": db_status,
    }
