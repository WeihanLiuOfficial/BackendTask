"""Agent 1: The Generator.

This module implements the primary AI generation agent that produces
survey JSON using OpenAI's Structured Outputs. It is invoked synchronously
within the HTTP request path to minimize Time-To-First-Byte.

Key responsibilities:
- Construct the appropriate system prompt based on the Tri-Modal modality.
- Call the OpenAI Chat Completions API with Structured Outputs.
- Return a validated SurveySchema instance.

All OpenAI calls are wrapped in tenacity retry decorators for resilience.
"""

import logging
from typing import Optional

from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.schemas.survey import SurveySchema, GenerateSurveyRequest
from app.services.ai.prompts import (
    build_generator_system_prompt,
    build_generator_user_prompt,
)

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def generate_survey_with_llm(
    request: GenerateSurveyRequest,
    modality: str,
    openai_client: AsyncOpenAI,
    model: str = "gpt-4o-mini",
) -> SurveySchema:
    """Invoke Agent 1 to generate a survey using OpenAI Structured Outputs.

    Uses the beta `parse()` method which constrains the LLM output to
    match the SurveySchema Pydantic model exactly. This eliminates
    JSON parsing errors and guarantees type-safe responses.

    Args:
        request: The validated generation request payload.
        modality: The determined Tri-Modal path
                  ('zero_to_one', 'hybrid_expansion', 'translation_only').
        openai_client: Configured async OpenAI client.
        model: The OpenAI model identifier to use.

    Returns:
        A fully validated SurveySchema instance.

    Raises:
        OpenAIError: If the API call fails after all retry attempts.
    """
    system_prompt = build_generator_system_prompt(modality)
    user_prompt = build_generator_user_prompt(
        prompt=request.prompt,
        question_count=request.question_count,
        existing_questions=request.existing_questions,
    )

    logger.info(
        "Invoking Generator Agent (modality=%s, model=%s, question_count=%s)",
        modality,
        model,
        request.question_count,
    )

    completion = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=SurveySchema,
        temperature=0.7,
    )

    survey: Optional[SurveySchema] = completion.choices[0].message.parsed

    if survey is None:
        # This should never happen with Structured Outputs, but guard against it.
        raise ValueError(
            f"OpenAI returned unparseable response. "
            f"Refusal: {completion.choices[0].message.refusal}"
        )

    logger.info(
        "Generator produced survey: title='%s', questions=%d",
        survey.title.en,
        len(survey.questions),
    )
    return survey
