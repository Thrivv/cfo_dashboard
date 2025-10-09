from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

try:
    from .config import QDRANT_API_KEY, QDRANT_COLLECTION, QDRANT_URL
except ImportError:
    from config import QDRANT_API_KEY, QDRANT_COLLECTION, QDRANT_URL

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def init_collection(dim: int):
    """Create collection if not exists."""
    try:
        client.get_collection(collection_name=QDRANT_COLLECTION)
    except Exception:
        # For large-scale applications, consider configuring HNSW for performance:
        # from qdrant_client.models import HnswConfigDiff
        # hnsw_config = HnswConfigDiff(m=16, ef_construct=100)
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            # hnsw_config=hnsw_config
        )


def upsert_embeddings(points: list[PointStruct], batch_size: int = 100):
    """Upserts embeddings to Qdrant in batches."""
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=QDRANT_COLLECTION, points=batch)


def search(query_vector: list[float], top_k: int = 5):
    return client.search(
        collection_name=QDRANT_COLLECTION, query_vector=query_vector, limit=top_k
    )
