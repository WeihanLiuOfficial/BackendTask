"""Semantic cache service using pgvector.

This module handles:
- Embedding user prompts via OpenAI's embedding API.
- Querying the SurveyCache table for cosine similarity matches.
- Storing new prompt/survey pairs in the cache on generation.

Cache scope: Global (shared across all users). There are no user
accounts in the current system, so all cached results are available
to anyone. In a multi-tenant system, cache entries would be scoped
by organization or user ID.
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.schemas.survey import SurveySchema
from app.models.survey import SurveyCache
from app.config import settings

logger = logging.getLogger(__name__)


async def embed_prompt(
    prompt: str,
    openai_client: AsyncOpenAI,
) -> List[float]:
    """Generate a 1536-dimensional embedding vector for a user prompt.

    Uses OpenAI's text-embedding-3-small model to convert the raw
    prompt text into a dense vector representation for similarity search.

    Args:
        prompt: The raw user prompt text.
        openai_client: Configured async OpenAI client.

    Returns:
        A list of 1536 floats representing the prompt's embedding.

    Raises:
        OpenAIError: If the embedding API call fails.
    """
    response = await openai_client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=prompt,
    )
    embedding = response.data[0].embedding
    logger.info(
        "Generated embedding for prompt (dim=%d, model=%s)",
        len(embedding),
        settings.OPENAI_EMBEDDING_MODEL,
    )
    return embedding


async def find_similar_survey(
    embedding: List[float],
    db: AsyncSession,
    threshold: float = settings.SIMILARITY_THRESHOLD,
) -> Optional[Tuple[dict, float]]:
    """Search the semantic cache for a survey matching the given embedding.

    Uses pgvector's cosine distance operator (<=>) to find the nearest
    cached prompt. Returns the cached survey_data JSONB if the similarity
    exceeds the configured threshold.

    The HNSW index on prompt_embedding provides O(log n) approximate
    nearest-neighbor lookup instead of O(n) full table scans.

    Args:
        embedding: The 1536-dim embedding vector of the new prompt.
        db: Async database session.
        threshold: Minimum cosine similarity to qualify as a cache hit.

    Returns:
        A tuple of (survey_data_dict, similarity_score) if a match is found,
        or None if no sufficiently similar prompt exists in the cache.
    """
    # pgvector's <=> operator returns cosine DISTANCE (0 = identical).
    # Similarity = 1 - distance. We filter where similarity > threshold.
    query = text("""
        SELECT survey_data, 1 - (prompt_embedding <=> :embedding) AS similarity
        FROM survey_cache
        WHERE 1 - (prompt_embedding <=> :embedding) > :threshold
        ORDER BY similarity DESC
        LIMIT 1
    """)

    result = await db.execute(
        query,
        {"embedding": str(embedding), "threshold": threshold},
    )
    row = result.first()

    if row is None:
        logger.info("Semantic cache MISS (threshold=%.2f)", threshold)
        return None

    survey_data, similarity = row
    logger.info(
        "Semantic cache HIT (similarity=%.4f, threshold=%.2f)",
        similarity,
        threshold,
    )
    return survey_data, similarity


async def store_in_cache(
    prompt: str,
    embedding: List[float],
    survey_data: dict,
    db: AsyncSession,
) -> None:
    """Store a new prompt/embedding/survey triplet in the semantic cache.

    Called after a successful LLM generation (cache miss) to ensure
    future identical or similar prompts return cached results.

    Args:
        prompt: The raw user prompt text.
        embedding: The 1536-dim embedding vector.
        survey_data: The generated survey payload as a dict (for JSONB storage).
        db: Async database session.
    """
    cache_entry = SurveyCache(
        prompt=prompt,
        prompt_embedding=embedding,
        survey_data=survey_data,
    )
    db.add(cache_entry)
    await db.flush()
    logger.info("Stored new cache entry for prompt: '%.60s...'", prompt)
