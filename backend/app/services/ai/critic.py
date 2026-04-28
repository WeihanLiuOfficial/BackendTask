"""Agent 2: The Critic (Asynchronous Background Task).

This module implements the secondary QA agent that audits AI-generated
surveys for qualitative issues. It runs OUTSIDE the HTTP request path
via FastAPI BackgroundTasks, ensuring zero impact on user-perceived latency.

Trigger policy:
- Automatically dispatched on AI-generated surveys (cache misses only).
- Manually triggered via POST /api/v1/surveys/{id}/audit endpoint.
- Does NOT auto-run on manual survey creates/updates (to save API costs).

Key responsibilities:
- Check for question bias or leading phrasing.
- Evaluate survey fatigue (too many open-ended questions, etc.).
- Validate French translation naturalness.
- Write quality_issues JSONB to the survey record.
"""

import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from openai import AsyncOpenAI

from app.schemas.survey import SurveySchema, CriticResponse
from app.services.ai.prompts import build_critic_prompt

logger = logging.getLogger(__name__)


async def run_critic_audit(
    survey_id: UUID,
    survey: SurveySchema,
    openai_client: AsyncOpenAI,
    db_url: str,
    model: str = "gpt-4o-mini",
) -> None:
    """Execute the Critic agent as a background task.

    This function creates its own database session (since it runs
    outside the request lifecycle) and patches the survey record
    with any quality issues found.

    Args:
        survey_id: The UUID of the survey to audit.
        survey: The generated survey payload to evaluate.
        openai_client: Configured async OpenAI client.
        db_url: Database connection string for creating an independent session.
        model: The OpenAI model identifier to use for evaluation.
    """
    logger.info("Critic audit starting for survey %s", survey_id)

    try:
        # Build the evaluation prompt
        system_prompt = build_critic_prompt()
        user_prompt = (
            "Evaluate the following survey for quality issues:\n\n"
            f"```json\n{json.dumps(survey.model_dump(mode='json'), indent=2)}\n```"
        )

        # Call OpenAI with Structured Output enforcement
        completion = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=CriticResponse,
            temperature=0.3,  # Low temperature for consistent evaluation
        )

        critic_result = completion.choices[0].message.parsed
        if critic_result is None:
            logger.warning(
                "Critic returned unparseable response for survey %s. Refusal: %s",
                survey_id,
                completion.choices[0].message.refusal,
            )
            return

        # Serialize issues to dicts for JSONB storage
        issues_data = [issue.model_dump(mode="json") for issue in critic_result.issues]

        logger.info(
            "Critic found %d issues for survey %s (severities: %s)",
            len(issues_data),
            survey_id,
            [i["severity"] for i in issues_data] if issues_data else "none",
        )

        # Write quality_issues to the database using an independent session.
        # BackgroundTasks run after the response is sent, so the request's
        # DB session is already closed. We must create our own.
        engine = create_async_engine(db_url, pool_size=1, max_overflow=0)
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            from app.models.survey import Survey  # Late import to avoid circular deps

            result = await session.execute(
                select(Survey).where(Survey.id == survey_id)
            )
            survey_row = result.scalar_one_or_none()

            if survey_row is None:
                logger.warning("Survey %s not found during Critic audit — may have been deleted", survey_id)
                return

            survey_row.quality_issues = issues_data
            await session.commit()

        await engine.dispose()

        logger.info("Critic audit completed for survey %s — wrote %d issues", survey_id, len(issues_data))

    except Exception:
        logger.exception("Critic audit FAILED for survey %s", survey_id)
        # Critic failures are non-fatal — the survey is already saved.
        # We log the error but do not propagate it.
