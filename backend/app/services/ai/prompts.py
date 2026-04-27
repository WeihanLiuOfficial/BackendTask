"""LLM prompt templates for the Generator and Critic agents.

All system prompts and user prompt builders are centralized here
to maintain a single source of truth for prompt engineering.
Modifying prompts in isolation prevents accidental regressions.
"""

from typing import Optional, List

from app.schemas.survey import QuestionSchema


def build_generator_system_prompt(modality: str) -> str:
    """Construct the system prompt for Agent 1 based on the Tri-Modal modality.

    Args:
        modality: One of 'zero_to_one', 'hybrid_expansion', 'translation_only'.

    Returns:
        The system prompt string.
    """
    # TODO: Return modality-specific system prompts that enforce:
    #   - Bilingual output (en + fr)
    #   - Correct question types matching frontend expectations
    #   - Auto-complete logic for empty options
    #   - requested_option_count enforcement
    raise NotImplementedError


def build_generator_user_prompt(
    prompt: str,
    existing_questions: Optional[List[QuestionSchema]] = None,
) -> str:
    """Construct the user message for Agent 1.

    Args:
        prompt: The user's natural language survey description.
        existing_questions: Optional list of manually authored questions
                           to include as locked context for Hybrid mode.

    Returns:
        The user prompt string.
    """
    # TODO: Serialize existing_questions to JSON if present
    raise NotImplementedError


def build_critic_prompt() -> str:
    """Construct the system prompt for Agent 2 (The Critic).

    The Critic evaluates surveys against a strict rubric:
    - Bias detection (leading questions)
    - Survey fatigue analysis (question type distribution)
    - French translation naturalness
    - Option mutual exclusivity for choice questions

    Returns:
        The critic system prompt string.
    """
    # TODO: Define the critic's evaluation rubric
    raise NotImplementedError
