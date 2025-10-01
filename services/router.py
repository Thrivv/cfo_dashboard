from __future__ import annotations
from typing import Callable, Dict
import pandas as pd

from .chatbot_llm_services import process_financial_question


def intent_router() -> Dict[str, Callable[[str, pd.DataFrame], str]]:
    return {
        "chat": lambda query, df: process_financial_question(query),
    }


