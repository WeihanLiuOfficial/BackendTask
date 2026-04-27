"""Aggregated API router.

Mounts all versioned sub-routers under a single parent router
that is then included in the FastAPI application instance.
"""

from fastapi import APIRouter

from app.api.v1.surveys import router as surveys_router
from app.api.v1.health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(surveys_router, prefix="/surveys", tags=["Surveys"])
