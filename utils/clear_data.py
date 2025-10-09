import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis
from qdrant_client import QdrantClient

from utils.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_USERNAME,
    REDIS_PASSWORD,
)


def clear_qdrant():
    """Deletes the Qdrant collection."""
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        client.delete_collection(collection_name=QDRANT_COLLECTION)
        print(f"✅ Qdrant collection '{QDRANT_COLLECTION}' deleted.")
    except Exception as e:
        print(
            f"⚠️ Qdrant collection '{QDRANT_COLLECTION}' could not be deleted. It might not exist. Error: {e}"
        )


def clear_redis():
    """Flushes the Redis database."""
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            db=0,
            decode_responses=True,
        )
        redis_client.flushdb()
        print("✅ Redis database flushed.")
    except Exception as e:
        print(f"⚠️ Redis database could not be flushed. Error: {e}")


if __name__ == "__main__":
    print("Clearing Qdrant and Redis...")
    clear_qdrant()
    clear_redis()
    print("✅ Done.")
