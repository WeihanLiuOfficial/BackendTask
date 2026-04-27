"""Agent 2: The Critic (Asynchronous Background Task).

This module implements the secondary QA agent that audits AI-generated
surveys for qualitative issues. It runs OUTSIDE the HTTP request path
via FastAPI BackgroundTasks, ensuring zero impact on user-perceived latency.

Key responsibilities:
- Check for question bias or leading phrasing.
- Evaluate survey fatigue (too many open-ended questions, etc.).
- Validate French translation naturalness.
- Patch the database record if issues are found.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.schemas.survey import SurveySchema
from app.services.ai.prompts import build_critic_prompt


async def run_critic_audit(
    survey_id: UUID,
    survey: SurveySchema,
    openai_client: AsyncOpenAI,
    db_url: str,
) -> None:
    """Execute the Critic agent as a background task.

    This function creates its own database session (since it runs
    outside the request lifecycle) and patches the survey record
    if the Critic identifies quality issues.

    Args:
        survey_id: The UUID of the survey to audit.
        survey: The generated survey payload to evaluate.
        openai_client: Configured async OpenAI client.
        db_url: Database connection string for creating an independent session.
    """
    # TODO: Build critic prompt via build_critic_prompt()
    # TODO: Call OpenAI to evaluate the survey quality
    # TODO: If issues found, create a new async session and patch the DB record
    # TODO: Optionally log the audit results via structlog
    raise NotImplementedError
