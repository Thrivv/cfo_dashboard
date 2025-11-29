"""Configuration settings for the CFO dashboard."""

import os

from dotenv import load_dotenv
import streamlit as st

# Try to load from .env first (for backward compatibility)
dotenv_path = ".env"
load_dotenv(dotenv_path=dotenv_path)


def get_secret(key, default=None):
    """Get secret from environment variables."""
    # Fallback to environment variables
    return os.getenv(key, default)


# Qdrant
QDRANT_URL = get_secret("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = get_secret("QDRANT_API_KEY")
AR_INVOICE_COLLECTION = get_secret("AR_INVOICE_COLLECTION", "ar_invoice")
AP_INVOICE_COLLECTION = get_secret("AP_INVOICE_COLLECTION", "ap_invoice")
PO_TC_COLLECTION = get_secret("PO_TC_COLLECTION", "po_tc")
REGULATIONS_COLLECTION = get_secret("REGULATIONS_COLLECTION", "regulations")
REBATE_COLLECTION = get_secret("REBATE_COLLECTION", "rebate")

# Redis
REDIS_HOST = get_secret("REDIS_HOST", "localhost")
REDIS_PORT = int(get_secret("REDIS_PORT", 6379))
REDIS_USERNAME = get_secret("REDIS_USERNAME")
REDIS_PASSWORD = get_secret("REDIS_PASSWORD")

# Embedding Model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Cohere
COHERE_API_KEY = get_secret("COHERE_API_KEY")

# Runpod VLLM endpoint
RUNPOD_API_KEY = get_secret("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = get_secret("RUNPOD_ENDPOINT_ID")

# OpenRouter
OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")
