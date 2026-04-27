"""Application configuration via pydantic-settings.

All environment variables are validated at startup. If a required variable
is missing, the application will fail fast with a clear error message
instead of silently using a broken default at runtime.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Type-safe, validated application settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ────────────────────────────────────
    DATABASE_URL: str = Field(
        ...,
        description="Async PostgreSQL connection string (postgresql+asyncpg://...)",
    )

    # ── OpenAI ──────────────────────────────────────
    OPENAI_API_KEY: str = Field(
        ...,
        description="OpenAI API key for LLM generation and embeddings.",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model identifier for survey generation.",
    )
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model identifier for prompt embedding.",
    )

    # ── Security ────────────────────────────────────
    API_BEARER_TOKEN: str = Field(
        ...,
        description="Secret Bearer token for API authentication.",
    )

    # ── Application ─────────────────────────────────
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins for the React frontend.",
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for semantic cache hits (0.0 to 1.0).",
    )
    RATE_LIMIT: str = Field(
        default="10/minute",
        description="Rate limit string for the generation endpoint (slowapi format).",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging verbosity level.",
    )


# Singleton instance — imported throughout the application
settings = Settings()
