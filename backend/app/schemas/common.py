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

    Unlike LocalizedText, the ``fr`` field is optional and may be an empty
    string. This accommodates the Translation-Only modal where the caller
    deliberately omits French content and asks the LLM to fill it in.
    """

    en: str = Field(..., min_length=1, description="The English text (required).")
    fr: str = Field(default="", description="The French text. May be empty when requesting translation.")


class ErrorResponse(BaseModel):
    """Standardized error response returned by all API error handlers.

    Ensures the React frontend always receives a predictable error
    structure regardless of the exception type.
    """

    error: str = Field(..., description="Machine-readable error code (e.g., 'validation_error', 'not_found').")
    detail: str = Field(..., description="Human-readable error description.")
    status_code: int = Field(..., description="HTTP status code.")
