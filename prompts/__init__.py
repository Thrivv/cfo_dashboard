"""Prompts module for CFO Dashboard AI Assistant.

This module contains all system prompts and templates used by the AI Assistant.
"""

from .system_prompts import (
    PROMPT_TYPES,
    get_system_prompt,
    get_retry_prompt,
    get_smart_prompt,
    get_general_question_prompt,
    get_greeting_prompt,
)

__all__ = ["get_system_prompt", "get_retry_prompt", "get_smart_prompt", "get_general_question_prompt", "get_greeting_prompt", "PROMPT_TYPES"]
