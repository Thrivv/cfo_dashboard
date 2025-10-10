"""Embedding utilities for vector operations."""

import logging

from sentence_transformers import SentenceTransformer

logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

from utils.config import EMBEDDING_MODEL

_model = SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for list of texts."""
    return _model.encode(texts, show_progress_bar=False).tolist()
