"""
Prompts module for CFO Dashboard AI Assistant.

This module contains all system prompts and templates used by the AI Assistant.
"""

from .system_prompts import (
    get_system_prompt,
    get_retry_prompt,
    PROMPT_TYPES
)

__all__ = [
    'get_system_prompt',
    'get_retry_prompt',
    'PROMPT_TYPES'
]