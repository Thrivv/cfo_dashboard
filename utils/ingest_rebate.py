"""Data ingestion for Rebate PDF."""

import os
import sys
from qdrant_client import QdrantClient
# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pipeline import ingest_document
from utils.config import QDRANT_URL, QDRANT_API_KEY


def ingest_rebate_pdf():
    """Initializes clients and ingests the Rebate PDF."""

    # Initialize Qdrant client
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # Ingest Rebate PDF using the existing pipeline
    rebate_path = "data/Rebate.pdf"
    rebate_metadata = {"doc_name": "Rebate.pdf", "source_type": "rebate"}
    ingest_document(rebate_path, rebate_metadata, REBATE_COLLECTION)
    print("✅ Rebate PDF ingested")


if __name__ == "__main__":
    ingest_rebate_pdf()