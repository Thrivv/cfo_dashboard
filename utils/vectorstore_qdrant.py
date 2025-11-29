"""Qdrant vector store utilities for document storage."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

try:
    from .config import (
        QDRANT_API_KEY,
        QDRANT_URL,
        AR_INVOICE_COLLECTION,
        AP_INVOICE_COLLECTION,
        PO_TC_COLLECTION,
        REGULATIONS_COLLECTION,
        REBATE_COLLECTION,
    )
except ImportError:
    from config import (
        QDRANT_API_KEY,
        QDRANT_URL,
        AR_INVOICE_COLLECTION,
        AP_INVOICE_COLLECTION,
        PO_TC_COLLECTION,
        REGULATIONS_COLLECTION,
        REBATE_COLLECTION,
    )

qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def init_collection(collection_name: str, dim: int):
    """Create collection if not exists."""
    try:
        qdrant_client.get_collection(collection_name=collection_name)
    except Exception:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def upsert_embeddings(
    collection_name: str, points: list[PointStruct], batch_size: int = 100
):
    """Upserts embeddings to Qdrant in batches."""
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        qdrant_client.upsert(collection_name=collection_name, points=batch)


def search(collection_name: str, query_vector: list[float], top_k: int = 5):
    return qdrant_client.search(
        collection_name=collection_name, query_vector=query_vector, limit=top_k
    )