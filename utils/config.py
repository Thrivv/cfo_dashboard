"""Configuration settings for the CFO dashboard."""

import os

from dotenv import load_dotenv
import streamlit as st

# Try to load from .env first (for backward compatibility)
load_dotenv(dotenv_path="/home/ubuntu/cfo_dashboard/.env")


def get_secret(key, default=None):
    """Get secret from Streamlit secrets or environment variables as fallback."""
    try:
        return st.secrets[key]
    except (KeyError, AttributeError):
        # Fallback to environment variables
        return os.getenv(key, default)


# Qdrant
QDRANT_URL = get_secret("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = get_secret("QDRANT_API_KEY")
QDRANT_COLLECTION = get_secret("QDRANT_COLLECTION", "financial_docs")

# Redis
REDIS_HOST = get_secret("REDIS_HOST", "localhost")
REDIS_PORT = int(get_secret("REDIS_PORT", 6379))
REDIS_USERNAME = get_secret("REDIS_USERNAME")
REDIS_PASSWORD = get_secret("REDIS_PASSWORD")

# FinBERT Model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Cohere
COHERE_API_KEY = get_secret("COHERE_API_KEY")

# Runpod VLLM endpoint
RUNPOD_API_KEY = get_secret("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = get_secret("RUNPOD_ENDPOINT_ID", "lkbk4plvvt0vah")
