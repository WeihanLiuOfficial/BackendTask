"""Survey service — business logic orchestrator.

This module acts as the intermediary between the API layer and the
underlying AI agents + database. It handles all CRUD operations and
determines the Tri-Modal execution path for generation requests.

All queries filter out soft-deleted surveys (is_deleted=false).
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.survey import Survey
from app.schemas.survey import (
    SurveyCreateRequest,
    SurveyResponse,
    SurveyListResponse,
    SurveyListItem,
    SurveySchema,
    QualityIssue,
)
from app.schemas.common import LocalizedTextInput


# ── Reusable filter for soft-deleted surveys ─────────
def _not_deleted():
    """Return a SQLAlchemy filter clause excluding soft-deleted surveys."""
    return Survey.is_deleted == False  # noqa: E712 — SQLAlchemy requires == not 'is'


async def list_surveys(
    db: AsyncSession,
) -> SurveyListResponse:
    """Retrieve all non-deleted surveys ordered by creation date (descending).

    Args:
        db: Async database session.

    Returns:
        A list of survey summaries for the left sidebar.
    """
    result = await db.execute(
        select(Survey)
        .where(_not_deleted())
        .order_by(Survey.created_at.desc())
    )
    surveys = result.scalars().all()

    items = [
        SurveyListItem(
            id=str(survey.id),
            title=LocalizedTextInput(en=survey.title_en, fr=survey.title_fr),
            created_at=survey.created_at,
            has_quality_issues=bool(survey.quality_issues),
        )
        for survey in surveys
    ]

    return SurveyListResponse(surveys=items, total=len(items))


async def get_survey_by_id(
    survey_id: uuid.UUID,
    db: AsyncSession,
) -> Optional[SurveyResponse]:
    """Retrieve a single non-deleted survey by its UUID.

    Args:
        survey_id: The UUID of the target survey.
        db: Async database session.

    Returns:
        The full survey response, or None if not found.
    """
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, _not_deleted())
    )
    survey = result.scalar_one_or_none()

    if survey is None:
        return None

    return _orm_to_response(survey)


async def save_survey(
    payload: SurveyCreateRequest,
    db: AsyncSession,
) -> SurveyResponse:
    """Persist a manually authored survey.

    Args:
        payload: The survey data to save.
        db: Async database session.

    Returns:
        The persisted survey with generated metadata.
    """
    survey = Survey(
        id=uuid.uuid4(),
        title_en=payload.title.en,
        title_fr=payload.title.fr,
        description_en=payload.description.en,
        description_fr=payload.description.fr,
        is_ordered=payload.is_ordered,
        survey_data=payload.model_dump(mode="json"),
    )
    db.add(survey)
    await db.flush()
    await db.refresh(survey)

    return _orm_to_response(survey)


async def update_survey(
    survey_id: uuid.UUID,
    payload: SurveyCreateRequest,
    db: AsyncSession,
) -> Optional[SurveyResponse]:
    """Update an existing non-deleted survey with new data.

    Args:
        survey_id: The UUID of the survey to update.
        payload: The updated survey data.
        db: Async database session.

    Returns:
        The updated survey response, or None if not found.
    """
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, _not_deleted())
    )
    survey = result.scalar_one_or_none()

    if survey is None:
        return None

    survey.title_en = payload.title.en
    survey.title_fr = payload.title.fr
    survey.description_en = payload.description.en
    survey.description_fr = payload.description.fr
    survey.is_ordered = payload.is_ordered
    survey.survey_data = payload.model_dump(mode="json")
    # Clear stale audit results — the previous Critic run is no longer valid
    # after the user edits the survey. null signals "not yet audited".
    survey.quality_issues = None

    await db.flush()
    await db.refresh(survey)

    return _orm_to_response(survey)


async def delete_survey(
    survey_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    """Soft-delete a survey by setting is_deleted=True and deleted_at.

    The survey remains in the database for potential recovery.

    Args:
        survey_id: The UUID of the survey to soft-delete.
        db: Async database session.

    Returns:
        True if the survey was found and soft-deleted, False if not found.
    """
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, _not_deleted())
    )
    survey = result.scalar_one_or_none()

    if survey is None:
        return False

    survey.is_deleted = True
    survey.deleted_at = datetime.now(timezone.utc)
    await db.flush()

    return True


async def restore_survey(
    survey_id: uuid.UUID,
    db: AsyncSession,
) -> Optional[SurveyResponse]:
    """Restore a soft-deleted survey by clearing the deletion flags.

    Only surveys that are currently soft-deleted can be restored.

    Args:
        survey_id: The UUID of the survey to restore.
        db: Async database session.

    Returns:
        The restored survey response, or None if not found or not deleted.
    """
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.is_deleted == True)  # noqa: E712
    )
    survey = result.scalar_one_or_none()

    if survey is None:
        return None

    survey.is_deleted = False
    survey.deleted_at = None

    await db.flush()
    await db.refresh(survey)

    return _orm_to_response(survey)


# ── Deleted Survey Management ────────────────────────


async def list_deleted_surveys(db: AsyncSession) -> SurveyListResponse:
    """Retrieve all soft-deleted surveys ordered by deletion date (most recent first).

    Args:
        db: Async database session.

    Returns:
        A SurveyListResponse containing only soft-deleted surveys.
    """
    result = await db.execute(
        select(Survey)
        .where(Survey.is_deleted == True)  # noqa: E712
        .order_by(Survey.deleted_at.desc())
    )
    surveys = result.scalars().all()

    items = [
        SurveyListItem(
            id=str(s.id),
            title=LocalizedTextInput(en=s.title_en, fr=s.title_fr),
            created_at=s.created_at,
            has_quality_issues=False,
        )
        for s in surveys
    ]
    return SurveyListResponse(surveys=items, total=len(items))


async def permanently_delete_survey(survey_id: uuid.UUID, db: AsyncSession) -> bool:
    """Permanently and irreversibly delete a soft-deleted survey from the database.

    Only surveys that are already soft-deleted can be permanently deleted.
    This is a hard DELETE — no recovery is possible after this call.

    Args:
        survey_id: The UUID of the survey to permanently delete.
        db: Async database session.

    Returns:
        True if found and deleted, False if not found or not soft-deleted.
    """
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.is_deleted == True)  # noqa: E712
    )
    survey = result.scalar_one_or_none()

    if survey is None:
        return False

    await db.delete(survey)
    await db.flush()
    return True


# ── Private Helpers ──────────────────────────────────


def _orm_to_response(survey: Survey) -> SurveyResponse:
    """Convert a SQLAlchemy Survey ORM instance to a Pydantic SurveyResponse.

    Args:
        survey: The ORM instance.

    Returns:
        A validated SurveyResponse.
    """
    survey_data = survey.survey_data

    # Parse quality_issues from JSONB if present
    quality_issues = None
    if survey.quality_issues is not None:
        quality_issues = [QualityIssue(**qi) for qi in survey.quality_issues]

    return SurveyResponse(
        id=str(survey.id),
        survey=SurveySchema(
            title=LocalizedTextInput(en=survey.title_en, fr=survey.title_fr),
            description=LocalizedTextInput(
                en=survey.description_en, fr=survey.description_fr
            ),
            is_ordered=survey.is_ordered if survey.is_ordered is not None else True,
            questions=survey_data.get("questions", []),
        ),
        created_at=survey.created_at,
        updated_at=survey.updated_at,
        quality_issues=quality_issues,
    )
