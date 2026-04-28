"""Survey CRUD and AI generation endpoints.

This module contains all survey-related route handlers:
- Standard CRUD operations (list, get, create, update, delete)
- Tri-Modal AI generation endpoint with semantic caching (Phase 4)
- All endpoints are protected by Bearer token auth (Option B: disabled by default)
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.dependencies import get_db_session, get_openai_client
from app.middleware.auth import verify_bearer_token
from app.middleware.rate_limiter import limiter
from app.config import settings
from app.schemas.survey import (
    GenerateSurveyRequest,
    GenerateSurveyResponse,
    SurveyCreateRequest,
    SurveyResponse,
    SurveyListResponse,
)
from app.services import survey_service
from app.services import generation_service
from app.services.ai.critic import run_critic_audit

router = APIRouter()


# ── CRUD Endpoints ──────────────────────────────────


@router.get("", response_model=SurveyListResponse)
async def list_surveys(
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_bearer_token),
) -> SurveyListResponse:
    """List all saved surveys for the left sidebar navigation.

    Returns:
        A list of survey summaries (id, title, created_at).
    """
    return await survey_service.list_surveys(db)


@router.get("/deleted", response_model=SurveyListResponse)
async def list_deleted_surveys(
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_bearer_token),
) -> SurveyListResponse:
    """List all soft-deleted surveys for the Recently Deleted panel.

    Must be defined BEFORE /{survey_id} so FastAPI does not try to
    parse the literal string 'deleted' as a UUID.

    Returns:
        A list of soft-deleted survey summaries ordered by deletion date.
    """
    return await survey_service.list_deleted_surveys(db)


@router.get("/{survey_id}", response_model=SurveyResponse)
async def get_survey(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_bearer_token),
) -> SurveyResponse:
    """Retrieve a specific survey by ID.

    Args:
        survey_id: The UUID of the survey to retrieve.

    Returns:
        The full survey payload including all questions and options.
    """
    result = await survey_service.get_survey_by_id(survey_id, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey with id '{survey_id}' not found.",
        )
    return result


@router.post("", response_model=SurveyResponse, status_code=201)
async def create_survey(
    payload: SurveyCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_bearer_token),
) -> SurveyResponse:
    """Save a manually authored survey.

    Args:
        payload: The survey data (title, description, questions).

    Returns:
        The persisted survey with a generated UUID.
    """
    return await survey_service.save_survey(payload, db)


@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(
    survey_id: UUID,
    payload: SurveyCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_bearer_token),
) -> SurveyResponse:
    """Update an existing survey with manual edits.

    Args:
        survey_id: The UUID of the survey to update.
        payload: The updated survey data.

    Returns:
        The updated survey payload.
    """
    result = await survey_service.update_survey(survey_id, payload, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey with id '{survey_id}' not found.",
        )
    return result


@router.delete("/{survey_id}", status_code=204)
async def delete_survey(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_bearer_token),
) -> None:
    """Soft-delete a survey by ID.

    The survey is marked as deleted but remains in the database
    for potential recovery.

    Args:
        survey_id: The UUID of the survey to delete.
    """
    deleted = await survey_service.delete_survey(survey_id, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey with id '{survey_id}' not found.",
        )


@router.patch("/{survey_id}/restore", response_model=SurveyResponse)
async def restore_survey(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_bearer_token),
) -> SurveyResponse:
    """Restore a soft-deleted survey.

    Reverts the is_deleted flag and clears the deleted_at timestamp,
    making the survey visible again in all queries.

    Args:
        survey_id: The UUID of the soft-deleted survey to restore.

    Returns:
        The restored survey payload.
    """
    result = await survey_service.restore_survey(survey_id, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey with id '{survey_id}' not found or is not deleted.",
        )
    return result



@router.delete("/{survey_id}/permanent", status_code=204)
async def permanently_delete_survey(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_bearer_token),
) -> None:
    """Permanently and irreversibly delete a soft-deleted survey.

    This is a hard DELETE — the survey cannot be recovered after this call.
    Only surveys that are already soft-deleted can be permanently deleted.

    Args:
        survey_id: The UUID of the soft-deleted survey to permanently destroy.
    """
    deleted = await survey_service.permanently_delete_survey(survey_id, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey with id '{survey_id}' not found or is not deleted.",
        )


# ── AI Generation Endpoint ──────────────────────────


@router.post("/generate", response_model=GenerateSurveyResponse)
@limiter.limit(settings.RATE_LIMIT)
async def generate_survey(
    request: Request,
    payload: GenerateSurveyRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    _auth: str = Depends(verify_bearer_token),
) -> GenerateSurveyResponse:
    """Tri-Modal AI survey generation endpoint.

    Rate-limited to protect OpenAI API credits.

    Execution flow:
        1. Determine modality (Zero-to-One / Hybrid / Translation-Only).
        2. For Zero-to-One: check semantic cache via pgvector similarity search.
        3. On cache miss: invoke Agent 1 (Generator) with Structured Outputs.
        4. Auto-save the generated survey.
        5. Return the generated survey immediately to the client.
        6. Dispatch Agent 2 (Critic) to BackgroundTasks for async QA.

    Args:
        request: The raw HTTP request (required by slowapi rate limiter).
        payload: The generation request containing the prompt,
                 optional existing questions, and configuration flags.
        background_tasks: FastAPI background task queue for Agent 2.
        db: Async database session.
        openai_client: Configured async OpenAI client.

    Returns:
        The generated survey payload ready for frontend rendering.
    """
    return await generation_service.generate_survey(
        request=payload,
        background_tasks=background_tasks,
        db=db,
        openai_client=openai_client,
    )


# ── Manual Audit Endpoint ───────────────────────────


@router.post("/{survey_id}/audit", response_model=SurveyResponse)
async def audit_survey(
    survey_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    _auth: str = Depends(verify_bearer_token),
) -> SurveyResponse:
    """Manually trigger the Critic agent on any survey.

    Dispatches Agent 2 (Critic) to evaluate the survey for quality
    issues. The audit runs in the background — quality_issues will
    be populated after a few seconds.

    Args:
        survey_id: The UUID of the survey to audit.
        background_tasks: FastAPI background task queue.
        db: Async database session.
        openai_client: Configured async OpenAI client.

    Returns:
        The current survey payload (quality_issues may still be null
        until the background audit completes).
    """
    result = await survey_service.get_survey_by_id(survey_id, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey with id '{survey_id}' not found.",
        )

    # Reconstruct the SurveySchema for the Critic
    from app.schemas.survey import SurveySchema
    survey_schema = result.survey

    background_tasks.add_task(
        run_critic_audit,
        survey_id=survey_id,
        survey=survey_schema,
        openai_client=openai_client,
        db_url=settings.DATABASE_URL,
    )

    return result
