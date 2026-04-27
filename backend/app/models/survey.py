"""SQLAlchemy ORM models for Survey and SurveyCache.

Survey: Stores user-saved surveys (manual + AI-generated) with full
        relational integrity for CRUD operations.

SurveyCache: Stores embedded prompts and their corresponding AI-generated
             JSONB payloads for semantic similarity caching via pgvector.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Boolean, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from app.models.database import Base


class Survey(Base):
    """Persisted survey entity supporting CRUD operations.

    Stores the full survey topology (title, description, questions, options)
    as a JSONB document alongside relational metadata for efficient querying.
    """

    __tablename__ = "surveys"

    id: uuid.UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    title_en: str = Column(String(500), nullable=False, doc="Survey title in English.")
    title_fr: str = Column(String(500), nullable=False, doc="Survey title in French.")
    description_en: str = Column(Text, nullable=False, doc="Survey description in English.")
    description_fr: str = Column(Text, nullable=False, doc="Survey description in French.")
    is_ordered: bool = Column(Boolean, default=True, doc="Whether the frontend should auto-number questions.")
    survey_data: dict = Column(JSONB, nullable=False, doc="Full survey topology (questions, options, localized text).")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SurveyCache(Base):
    """Semantic cache for AI-generated surveys.

    Stores the original user prompt, its vector embedding, and the
    generated JSONB payload. The embedding column is indexed for
    fast nearest-neighbor cosine similarity searches via pgvector.
    """

    __tablename__ = "survey_cache"

    id: uuid.UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    prompt: str = Column(Text, nullable=False, doc="The raw user prompt text.")
    prompt_embedding = Column(
        Vector(1536),
        nullable=False,
        doc="1536-dim embedding vector from text-embedding-3-small.",
    )
    survey_data: dict = Column(
        JSONB,
        nullable=False,
        doc="The cached AI-generated survey payload.",
    )
    similarity_score: float = Column(
        Float,
        nullable=True,
        doc="The cosine similarity score when this cache entry was created (for analytics).",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
