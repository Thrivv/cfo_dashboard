from sentence_transformers import SentenceTransformer
import logging

logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

try:
    from .config import EMBEDDING_MODEL
except ImportError:
    from config import EMBEDDING_MODEL

_model = SentenceTransformer(EMBEDDING_MODEL)

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for list of texts."""
    return _model.encode(texts, show_progress_bar=False).tolist()
