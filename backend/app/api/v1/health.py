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

    Returns:
        A JSON object with the API and database status.
    """
    # TODO: Execute a lightweight DB probe (SELECT 1) and report status
    raise NotImplementedError
