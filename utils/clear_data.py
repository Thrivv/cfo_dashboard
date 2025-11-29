import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
import redis

from utils.config import (
    QDRANT_API_KEY,
    QDRANT_URL,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    REDIS_USERNAME,
)


def clear_qdrant_collection(collection_name: str):
    """Deletes a specific collection from Qdrant."""
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        client.delete_collection(collection_name=collection_name)
        print(f"✅ Deleted Qdrant collection: {collection_name}")
    except Exception as e:
        print(f"⚠️ Could not delete Qdrant collection {collection_name}. Error: {e}")


def clear_all_qdrant():
    """Deletes all collections (and their vectors + metadata) in Qdrant."""
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        collections = client.get_collections().collections

        if not collections:
            print("ℹ️ No Qdrant collections found to delete.")
            return

        for coll in collections:
            clear_qdrant_collection(coll.name)

        print("✅ All Qdrant collections deleted (vectors + metadata removed).")

    except Exception as e:
        print(f"⚠️ Could not clear Qdrant data. Error: {e}")


def clear_all_redis():
    """Flushes all Redis databases (not just DB 0)."""
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
        redis_client.flushall()
        print("✅ All Redis databases flushed (keys + metadata cleared).")
    except Exception as e:
        print(f"⚠️ Could not flush Redis. Error: {e}")


if __name__ == "__main__":
    print("⚠️ WARNING: This will permanently delete ALL data from Qdrant and Redis.")
    confirm = input("Type 'YES' to continue: ")

    if confirm.strip().upper() == "YES":
        print("🧹 Clearing Qdrant and Redis data...")
        clear_all_qdrant()
        clear_all_redis()
        print("✅ Done. All caches, vectors, and metadata have been wiped clean.")
    else:
        print("❌ Operation cancelled.")