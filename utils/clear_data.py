import sys
import os
import redis
from qdrant_client import QdrantClient
from qdrant_client.http import models
from utils.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_USERNAME,
    REDIS_PASSWORD,
)

def clear_all_qdrant():
    """Deletes all collections (and their vectors + metadata) in Qdrant."""
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        collections = client.get_collections().collections

        if not collections:
            print("ℹ️ No Qdrant collections found to delete.")
            return

        for coll in collections:
            name = coll.name
            client.delete_collection(collection_name=name)
            print(f"✅ Deleted Qdrant collection: {name}")

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