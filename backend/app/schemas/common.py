"""Shared Pydantic schemas used across the application.

These schemas define the foundational data structures that are
reused by survey schemas, API responses, and LLM output enforcement.
"""

from pydantic import BaseModel, Field


class LocalizedText(BaseModel):
    """A bilingual text field supporting English and French.

    This schema is used as the base type for all user-facing text in
    the survey system, ensuring native bilingual support.
    """

    en: str = Field(..., min_length=1, description="The English translation of the text.")
    fr: str = Field(..., min_length=1, description="The French translation of the text.")


class LocalizedTextInput(BaseModel):
    """A bilingual text field used in generation/translation requests.

    Unlike LocalizedText, both fields are optional and may be empty strings.
    This accommodates the Translation-Only mode where:
      - The user writes in English → fr is empty, en has content
      - The user writes in French  → en is empty, fr has content
    The LLM fills in whichever side is missing.
    """

    en: str = Field(default="", description="The English text. May be empty when the user is authoring in French.")
    fr: str = Field(default="", description="The French text. May be empty when the user is authoring in English.")


class ErrorResponse(BaseModel):
    """Standardized error response returned by all API error handlers.

    Ensures the React frontend always receives a predictable error
    structure regardless of the exception type.
    """

    error: str = Field(..., description="Machine-readable error code (e.g., 'validation_error', 'not_found').")
    detail: str = Field(..., description="Human-readable error description.")
    status_code: int = Field(..., description="HTTP status code.")
