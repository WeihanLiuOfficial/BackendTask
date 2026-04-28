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

from app.schemas.common import LocalizedText, LocalizedTextInput


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

class QuestionInputSchema(BaseModel):
    """Question schema used inside GenerateSurveyRequest.existing_questions.

    Uses LocalizedTextInput so callers can send English-only questions
    when requesting translation (fr is allowed to be empty).
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the question.",
    )
    type: QuestionType = Field(
        ...,
        description="The question type.",
    )
    title: LocalizedTextInput = Field(
        ...,
        description="The main question text. fr may be empty when requesting translation.",
    )
    options: Optional[List["OptionInputSchema"]] = Field(
        default=None,
        description="Answer options. fr may be empty when requesting translation.",
    )
    saved: bool = Field(default=True)


class OptionInputSchema(BaseModel):
    """Option schema used inside GenerateSurveyRequest.existing_questions."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: LocalizedTextInput = Field(..., description="Option text. fr may be empty.")


# Resolve forward reference
QuestionInputSchema.model_rebuild()


class QuestionSchema(BaseModel):
    """A single survey question — strict bilingual schema used in responses,
    saves, and as the LLM Structured Output target. Both en and fr are required."""

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


# ── Quality Issue Schemas ───────────────────────────


class QualityIssue(BaseModel):
    """A single quality concern identified by the Critic agent.

    Can be question-level (targets a specific question by ID)
    or survey-level (applies to the survey as a whole).
    """

    issue_type: Literal["question_level", "survey_level"] = Field(
        ...,
        description="Whether this issue targets a specific question or the survey overall.",
    )
    question_id: Optional[str] = Field(
        default=None,
        description="The UUID of the affected question. Null for survey-level issues.",
    )
    severity: Literal["info", "warning", "critical"] = Field(
        ...,
        description="Issue severity: info (suggestion), warning (should fix), critical (must fix).",
    )
    message_en: str = Field(
        ...,
        description="Human-readable issue description in English.",
    )
    message_fr: str = Field(
        ...,
        description="Human-readable issue description in French.",
    )


class CriticResponse(BaseModel):
    """Structured Output schema for the Critic agent's evaluation.

    Passed directly to OpenAI's response_format to enforce valid JSON output.
    """

    issues: List[QualityIssue] = Field(
        default_factory=list,
        description="List of quality issues found. Empty list means the survey passed all checks.",
    )


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
    existing_questions: Optional[List[QuestionInputSchema]] = Field(
        default=None,
        description="The user's manually authored questions. If provided, enables Hybrid or Translation modes. fr fields may be empty for Translation-Only mode.",
    )
    add_more_questions: bool = Field(
        default=True,
        description="Whether the AI should invent additional questions beyond the existing ones.",
    )
    question_count: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Desired number of questions. If null, the AI decides based on the topic and description.",
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
    quality_issues: Optional[List[QualityIssue]] = Field(
        default=None,
        description="Quality concerns identified by the Critic agent. Null = not yet audited, [] = audited and clean.",
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
    has_quality_issues: bool = Field(
        default=False,
        description="Whether the Critic has flagged quality issues. Used to visually mark surveys in the sidebar.",
    )


class SurveyListResponse(BaseModel):
    """Outbound payload for listing all surveys."""

    surveys: List[SurveyListItem] = Field(..., description="List of survey summaries.")
    total: int = Field(..., description="Total number of surveys.")
