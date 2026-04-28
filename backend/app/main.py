"""FastAPI application factory and lifespan management.

This module creates the FastAPI application instance, registers all
middleware (CORS, rate limiting, auth), exception handlers, and
mounts the versioned API routers. The lifespan context manager
handles startup (DB connection pool) and shutdown (pool disposal).
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.router import api_router
from app.models.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.rate_limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    Startup:
        - Configure structured logging.
        - Verify database connectivity.
    Shutdown:
        - Dispose of the async engine connection pool.
    """
    # ── Startup ─────────────────────────────────────
    configure_logging(settings.LOG_LEVEL)
    # TODO: Verify DB connectivity and pgvector extension availability
    yield
    # ── Shutdown ────────────────────────────────────
    await engine.dispose()


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    application = FastAPI(
        title="Boundary AI — Survey Generator",
        description="AI-powered Tri-Modal survey generation engine with semantic caching.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── CORS Middleware ─────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate Limiter ────────────────────────────────
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    application.state.limiter = limiter
    application.add_middleware(SlowAPIMiddleware)
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Exception Handlers ──────────────────────────
    register_exception_handlers(application)

    # ── API Routers ─────────────────────────────────
    application.include_router(api_router, prefix="/api/v1")

    return application


# Application instance used by Uvicorn
app = create_app()
