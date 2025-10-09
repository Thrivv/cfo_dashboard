import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="/home/ubuntu/cfo_dashboard/.env")

# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "financial_docs")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_USERNAME = os.getenv("REDIS_USERNAME")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# Embedding Model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Cohere
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# Runpod VLLM endpoint
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "lkbk4plvvt0vah")
