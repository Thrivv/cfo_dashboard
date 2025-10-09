"""Output schema definitions for the CFO dashboard."""

from typing import List

from pydantic import BaseModel


class Insight(BaseModel):
    category: str  # e.g., warning, suggestion
    message: str
    source_doc: str
    chunk_id: str


class InsightOutput(BaseModel):
    query: str
    insights: List[Insight]
