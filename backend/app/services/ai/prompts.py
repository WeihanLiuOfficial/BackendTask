"""LLM prompt templates for the Generator and Critic agents.

All system prompts and user prompt builders are centralized here
to maintain a single source of truth for prompt engineering.
Modifying prompts in isolation prevents accidental regressions.
"""

import json
from typing import Optional, List

from app.schemas.survey import QuestionSchema


# ── Question Type Reference ─────────────────────────
# Shared across prompts so the LLM knows exactly which types to use.
QUESTION_TYPES_REFERENCE = """
Available question types (use EXACTLY these values):
- "singleChoice": Single-selection from options (radio buttons)
- "multipleChoice": Multi-selection from options (checkboxes)
- "openQuestion": Long-form free text response (paragraph)
- "shortAnswer": Brief free text response (one line)
- "scale": Numeric rating scale (1-5 or 1-10)
- "npsScore": Net Promoter Score (0-10 scale)

Rules for options:
- singleChoice and multipleChoice MUST have "options" with 2-6 answer choices.
- openQuestion, shortAnswer, scale, and npsScore MUST have "options" set to null.
"""


# ── Generator System Prompts ────────────────────────


def build_generator_system_prompt(modality: str) -> str:
    """Construct the system prompt for Agent 1 based on the Tri-Modal modality.

    Args:
        modality: One of 'zero_to_one', 'hybrid_expansion', 'translation_only'.

    Returns:
        The system prompt string.
    """
    base_instructions = """You are a professional survey designer creating high-quality bilingual (English + French) surveys.

CRITICAL RULES:
1. Every text field MUST have both "en" (English) and "fr" (French) values.
2. French translations must be natural and idiomatic — not word-for-word machine translations.
3. Use a DIVERSE mix of question types — never generate all questions as the same type.
4. For singleChoice and multipleChoice questions, generate 3-5 meaningful, mutually exclusive options.
5. Each question must have a unique UUID as its "id". Each option must have a unique UUID as its "id".
6. Set "saved" to true for every question.
7. The survey title should be concise and descriptive.
8. The survey description should be 1-2 sentences summarizing the survey's purpose.

""" + QUESTION_TYPES_REFERENCE

    modality_instructions = {
        "zero_to_one": """
MODE: ZERO-TO-ONE (Full Generation)
Generate a COMPLETE survey from scratch based on the user's description.
- Include a thoughtful mix of question types appropriate for the topic.
- Structure questions in a logical flow (general → specific → feedback).
- Ensure questions are unbiased, clear, and non-leading.
""",
        "hybrid_expansion": """
MODE: HYBRID EXPANSION
The user has provided existing questions. Your job is to:
1. KEEP all existing questions EXACTLY as they are (do not modify their text, type, or options).
2. Generate ADDITIONAL questions that complement and expand the existing survey.
3. New questions should fill gaps in topic coverage that existing questions don't address.
4. Place new questions in logical positions relative to existing ones.
""",
        "translation_only": """
MODE: TRANSLATION & FORMATTING
The user has provided existing questions. Your job is to:
1. KEEP all questions EXACTLY as they are — do not add, remove, or reorder any questions.
2. Ensure every text field has proper bilingual content (en + fr).
3. If a question only has English text, provide a natural French translation.
4. If a question only has French text, provide a natural English translation.
5. Do NOT invent new questions or modify existing question logic.
""",
    }

    return base_instructions + modality_instructions.get(modality, modality_instructions["zero_to_one"])


def build_generator_user_prompt(
    prompt: str,
    question_count: Optional[int] = None,
    existing_questions: Optional[List[QuestionSchema]] = None,
) -> str:
    """Construct the user message for Agent 1.

    Args:
        prompt: The user's natural language survey description.
        question_count: Optional desired number of questions.
        existing_questions: Optional list of manually authored questions
                           to include as locked context for Hybrid mode.

    Returns:
        The user prompt string.
    """
    parts = [f"Survey topic: {prompt}"]

    if question_count is not None:
        parts.append(f"\nGenerate exactly {question_count} questions.")
    else:
        parts.append("\nGenerate an appropriate number of questions for this topic (typically 5-12).")

    if existing_questions:
        serialized = json.dumps(
            [q.model_dump(mode="json") for q in existing_questions],
            indent=2,
        )
        parts.append(f"\nExisting questions (DO NOT modify these):\n```json\n{serialized}\n```")

    return "\n".join(parts)


# ── Critic System Prompt ────────────────────────────


def build_critic_prompt() -> str:
    """Construct the system prompt for Agent 2 (The Critic).

    The Critic evaluates surveys against a strict rubric covering
    both question-level and survey-level quality concerns.

    Returns:
        The critic system prompt string.
    """
    return """You are a survey quality auditor. Evaluate the provided survey for quality issues.

Report TWO types of issues:

## Question-Level Issues (issue_type: "question_level")
Set "question_id" to the UUID of the affected question. Check for:
- **Bias or leading phrasing**: Questions that push respondents toward a specific answer.
- **Ambiguity**: Questions that could be interpreted in multiple ways.
- **Double-barreled questions**: Questions that ask about two things at once.
- **Poor French translation**: Translations that are literal/unnatural or significantly different in meaning from the English.
- **Missing options**: singleChoice/multipleChoice questions with fewer than 2 options or missing obvious answer choices.
- **Inappropriate type**: Question type doesn't match the content (e.g., using openQuestion when scale would be better).

## Survey-Level Issues (issue_type: "survey_level")
Set "question_id" to null. Check for:
- **Question type fatigue**: Too many consecutive questions of the same type (3+ in a row).
- **Survey length**: Too few questions (<3) or too many (>20) for a standard survey.
- **Missing coverage**: Important sub-topics that should be covered but are not.
- **Poor ordering**: Questions not arranged in a logical flow.
- **Missing demographic questions**: Surveys that would benefit from basic demographic context.

## Severity Levels
- "info": Minor suggestion for improvement (stylistic, nice-to-have).
- "warning": Should be addressed for professional quality.
- "critical": Must fix — the question is biased, misleading, or technically broken.

## Rules
- Be HONEST but not harsh. Only flag genuine quality concerns.
- If the survey is well-constructed, return an EMPTY issues list.
- Provide bilingual messages (message_en + message_fr) for every issue.
- Keep messages concise (1-2 sentences max).
"""
