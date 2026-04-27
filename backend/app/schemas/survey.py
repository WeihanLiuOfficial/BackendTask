"""Pydantic schemas for Survey API request/response validation.

These schemas enforce strict type boundaries on:
- Inbound generation requests (prompt, existing questions, flags)
- Outbound survey payloads (title, description, questions, options)
- LLM Structured Output enforcement (passed directly to OpenAI)
"""

import uuid
from typing import List, Literal, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import LocalizedText


# ── Question Type Enum ──────────────────────────────
# Must exactly match the React frontend's <select> option values
QuestionType = Literal[
    "singleChoice",
    "multipleChoice",
    "openQuestion",
    "shortAnswer",
    "scale",
    "npsScore",
]


# ── Core Survey Schemas ─────────────────────────────


class OptionSchema(BaseModel):
    """A single option within a multiple-choice or single-choice question."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the option.",
    )
    text: LocalizedText = Field(
        ...,
        description="The option text in both English and French.",
    )


class QuestionSchema(BaseModel):
    """A single survey question with its type, title, and optional choices."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the question.",
    )
    type: QuestionType = Field(
        ...,
        description="The question type. Must match one of the frontend's supported types.",
    )
    title: LocalizedText = Field(
        ...,
        description="The main question text in both English and French.",
    )
    options: Optional[List[OptionSchema]] = Field(
        default=None,
        description="List of answer options. Required for singleChoice and multipleChoice; null for all other types.",
    )
    requested_option_count: Optional[int] = Field(
        default=None,
        ge=2,
        le=10,
        description="If provided, the AI MUST generate exactly this many options. If null, the AI decides autonomously.",
    )
    saved: bool = Field(
        default=True,
        description="Whether the question is in 'saved' (read-only) state. Always true for AI-generated questions.",
    )


class SurveySchema(BaseModel):
    """The complete survey topology used for both storage and frontend rendering."""

    title: LocalizedText = Field(..., description="The survey title in both languages.")
    description: LocalizedText = Field(..., description="A short description of the survey in both languages.")
    is_ordered: bool = Field(default=True, description="Whether the frontend should auto-number the questions.")
    questions: List[QuestionSchema] = Field(..., description="The ordered list of survey questions.")


# ── API Request Schemas ─────────────────────────────


class GenerateSurveyRequest(BaseModel):
    """Inbound payload for the Tri-Modal generation endpoint.

    The combination of `existing_questions` and `add_more_questions`
    determines which modality the pipeline will execute:
    - Zero-to-One: existing_questions is empty/null
    - Hybrid Expansion: existing_questions present + add_more_questions=True
    - Translation Only: existing_questions present + add_more_questions=False
    """

    prompt: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="The user's natural language description of the desired survey.",
    )
    existing_questions: Optional[List[QuestionSchema]] = Field(
        default=None,
        description="The user's manually authored questions. If provided, enables Hybrid or Translation modes.",
    )
    add_more_questions: bool = Field(
        default=True,
        description="Whether the AI should invent additional questions beyond the existing ones.",
    )


class SurveyCreateRequest(BaseModel):
    """Inbound payload for manually saving a survey (no AI involved)."""

    title: LocalizedText = Field(..., description="The survey title.")
    description: LocalizedText = Field(..., description="The survey description.")
    is_ordered: bool = Field(default=True, description="Whether questions should be auto-numbered.")
    questions: List[QuestionSchema] = Field(..., description="The list of questions to save.")


# ── API Response Schemas ────────────────────────────


class SurveyResponse(BaseModel):
    """Outbound payload for a single survey."""

    id: str = Field(..., description="The survey's UUID.")
    survey: SurveySchema = Field(..., description="The full survey topology.")
    created_at: datetime = Field(..., description="When the survey was created.")
    updated_at: datetime = Field(..., description="When the survey was last modified.")
    cache_hit: Optional[bool] = Field(
        default=None,
        description="Whether this response was served from the semantic cache (generation endpoint only).",
    )


class GenerateSurveyResponse(BaseModel):
    """Outbound payload for the AI generation endpoint."""

    id: str = Field(..., description="The saved survey's UUID.")
    survey: SurveySchema = Field(..., description="The generated survey topology.")
    cache_hit: bool = Field(..., description="Whether the response was served from the semantic cache.")
    modality: Literal["zero_to_one", "hybrid_expansion", "translation_only"] = Field(
        ...,
        description="Which Tri-Modal execution path was used.",
    )


class SurveyListItem(BaseModel):
    """A lightweight survey summary for the left sidebar list."""

    id: str = Field(..., description="The survey's UUID.")
    title: LocalizedText = Field(..., description="The survey title.")
    created_at: datetime = Field(..., description="When the survey was created.")


class SurveyListResponse(BaseModel):
    """Outbound payload for listing all surveys."""

    surveys: List[SurveyListItem] = Field(..., description="List of survey summaries.")
    total: int = Field(..., description="Total number of surveys.")
