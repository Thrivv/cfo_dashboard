from pydantic import BaseModel
from typing import List


class Insight(BaseModel):
    category: str  # e.g., warning, suggestion
    message: str
    source_doc: str
    chunk_id: str


class InsightOutput(BaseModel):
    query: str
    insights: List[Insight]
