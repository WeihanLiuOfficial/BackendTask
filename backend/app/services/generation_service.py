"""Generation service — Tri-Modal AI pipeline orchestrator.

This module is the single entry point for the /generate endpoint.
It coordinates all AI-related concerns:
    1. Modality detection (Zero-to-One / Hybrid / Translation-Only)
    2. Semantic cache lookup via pgvector
    3. Agent 1 (Generator) invocation
    4. Auto-save of generated surveys
    5. Agent 2 (Critic) dispatch to BackgroundTasks

survey_service.py handles CRUD only. This file handles AI orchestration only.
Neither imports the other's internal logic — they communicate through schemas.
"""

from uuid import UUID
from typing import Literal

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.config import settings
from app.schemas.survey import (
    GenerateSurveyRequest,
    GenerateSurveyResponse,
    SurveySchema,
    SurveyCreateRequest,
)
from app.schemas.common import LocalizedText
from app.services import survey_service
from app.services.cache import semantic_cache
from app.services.ai.generator import generate_survey_with_llm
from app.services.ai.critic import run_critic_audit


# ── Modality Detection ───────────────────────────────

ModalityType = Literal["zero_to_one", "hybrid_expansion", "translation_only"]


def determine_modality(request: GenerateSurveyRequest) -> ModalityType:
    """Determine which Tri-Modal execution path to use.

    Decision logic:
        - No existing questions → Zero-to-One (full synthesis)
        - Has existing questions + add_more_questions=True → Hybrid Expansion
        - Has existing questions + add_more_questions=False → Translation Only

    Args:
        request: The validated generation request.

    Returns:
        The modality string identifier.
    """
    if not request.existing_questions:
        return "zero_to_one"
    elif request.add_more_questions:
        return "hybrid_expansion"
    else:
        return "translation_only"


# ── Main Orchestrator ────────────────────────────────


async def generate_survey(
    request: GenerateSurveyRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    openai_client: AsyncOpenAI,
) -> GenerateSurveyResponse:
    """Execute the full Tri-Modal AI generation pipeline.

    Orchestration flow:
        1. Determine modality from request payload.
        2. For Zero-to-One: check semantic cache (pgvector cosine similarity).
        3. On cache miss: invoke Agent 1 (Generator) with Structured Outputs.
        4. Auto-save the generated survey to the surveys table.
        5. On cache miss: store the new prompt+embedding+result in survey_cache.
        6. Dispatch Agent 2 (Critic) to BackgroundTasks for async QA.
        7. Return the response immediately.

    Args:
        request: The validated generation request payload.
        background_tasks: FastAPI background task queue for Agent 2.
        db: Async database session.
        openai_client: Configured async OpenAI client singleton.

    Returns:
        The generated survey response with modality and cache_hit metadata.
    """
    modality = determine_modality(request)
    cache_hit = False
    survey_schema: SurveySchema

    # ── Step 1: Semantic Cache Lookup (Zero-to-One only) ──
    if modality == "zero_to_one":
        embedding = await semantic_cache.embed_prompt(request.prompt, openai_client)

        cached_result = await semantic_cache.find_similar_survey(embedding, db)
        if cached_result is not None:
            cached_data, similarity = cached_result
            survey_schema = SurveySchema(**cached_data)
            cache_hit = True

    # ── Step 2: LLM Generation (on cache miss) ───────────
    if not cache_hit:
        survey_schema = await generate_survey_with_llm(
            request=request,
            modality=modality,
            openai_client=openai_client,
            model=settings.OPENAI_MODEL,
        )

    # ── Step 3: Auto-Save to surveys table ───────────────
    save_payload = SurveyCreateRequest(
        title=survey_schema.title,
        description=survey_schema.description,
        is_ordered=survey_schema.is_ordered,
        questions=survey_schema.questions,
    )
    saved_survey = await survey_service.save_survey(save_payload, db)

    # ── Step 4: Cache the new result (on miss only) ──────
    if not cache_hit and modality == "zero_to_one":
        await semantic_cache.store_in_cache(
            prompt=request.prompt,
            embedding=embedding,  # type: ignore[possibly-unbound] — only reached when embedding was computed
            survey_data=survey_schema.model_dump(mode="json"),
            db=db,
        )

    # ── Step 5: Dispatch Critic to background (cache misses only) ──
    # Cached surveys were already audited when originally generated.
    if not cache_hit:
        background_tasks.add_task(
            run_critic_audit,
            survey_id=UUID(saved_survey.id),
            survey=survey_schema,
            openai_client=openai_client,
            db_url=settings.DATABASE_URL,
        )

    return GenerateSurveyResponse(
        id=saved_survey.id,
        survey=survey_schema,
        cache_hit=cache_hit,
        modality=modality,
    )
