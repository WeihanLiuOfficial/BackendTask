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

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.schemas.survey import SurveySchema, GenerateSurveyRequest
from app.services.ai.prompts import build_generator_prompt


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

    Args:
        request: The validated generation request payload.
        modality: The determined Tri-Modal path ('zero_to_one', 'hybrid_expansion', 'translation_only').
        openai_client: Configured async OpenAI client.
        model: The OpenAI model identifier to use.

    Returns:
        A fully validated SurveySchema instance.

    Raises:
        OpenAIError: If the API call fails after all retry attempts.
    """
    # TODO: Build system + user prompts via build_generator_prompt()
    # TODO: Call openai_client.beta.chat.completions.parse() with response_format=SurveySchema
    # TODO: Return the parsed SurveySchema
    raise NotImplementedError
