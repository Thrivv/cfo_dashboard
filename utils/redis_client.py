import json

import redis

try:
    from .config import REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_USERNAME
except ImportError:
    from config import REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_USERNAME

_redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    username=REDIS_USERNAME,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
)


def store_metadata(chunk_id: str, metadata: dict):
    """Stores metadata in Redis."""
    _redis_client.set(chunk_id, json.dumps(metadata))


def get_metadata(chunk_id: str) -> dict:
    """Retrieves metadata from Redis."""
    data = _redis_client.get(chunk_id)
    if data:
        return json.loads(data)
    return {}
