"""Data ingestion utilities for the CFO dashboard."""

import os
import sys
import uuid

import pandas as pd
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import EMBEDDING_MODEL, QDRANT_API_KEY, QDRANT_URL
from utils.pipeline import ingest_document


def ingest_csv_to_qdrant_enhanced(
    file_path: str,
    collection_name: str,
    client: QdrantClient,
    embedding_model: SentenceTransformer,
):
    """
    Reads a CSV file, chunks each row with rich context, generates embeddings,
    and ingests them into Qdrant with specific payload fields for filtering.
    """
    try:
        df = pd.read_csv(file_path)
        embedding_dim = embedding_model.get_sentence_embedding_dimension()

        print(f"Creating collection '{collection_name}' with vector size {embedding_dim}...")
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=embedding_dim, distance=models.Distance.COSINE
            ),
        )

        points = []
        for _, row in df.iterrows():
            # Create a rich text chunk for semantic search.
            # Explicitly include important information like due date and payment status.
            if "Supplier Name" in row:
                name_field = "Supplier Name"
                name = row[name_field]
            else:
                name_field = "Customer Name"
                name = row[name_field]

            text_chunk = (
                f"Invoice record: Invoice No. {row['Invoice No.']}, issued on {row['Invoice Date']}, "
                f"from {name} for {row['Service Description']}. "
                f"The amount is {row['Amount (AED)']} AED. "
                f"The payment status is '{row['Payment Status']}' and the due date was '{row['Due Date']}'."
            )

            embedding = embedding_model.encode(text_chunk).tolist()

            # Use the entire row as a payload, including a normalized payment status.
            payload = row.to_dict()
            payload["source_file"] = file_path

            # Qdrant filters work best on well-defined types. Normalize payment status.
            payload["payment_status_keyword"] = str(row["Payment Status"]).strip().lower()

            # Create a unique ID for each point
            point_id = str(uuid.uuid4())

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        print(f"Ingesting {len(points)} points into '{collection_name}'...")
        client.upsert(collection_name=collection_name, points=points)
        print(f"Ingestion for '{collection_name}' completed.")

    except Exception as e:
        print(f"An error occurred during ingestion for {file_path}: {e}")


if __name__ == "__main__":
    # Initialize Qdrant client and embedding model
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    # Ingest AP Invoice using the new enhanced CSV function
    ap_invoice_path = "data/AP_Invoice.csv"
    ingest_csv_to_qdrant_enhanced(
        ap_invoice_path, "ap_invoices", qdrant_client, embedding_model
    )
    print("✅ AP Invoice ingested")

    # Ingest AR Invoice using the new enhanced CSV function
    ar_invoice_path = "data/AR_Invoice.csv"
    ingest_csv_to_qdrant_enhanced(
        ar_invoice_path, "ar_invoices", qdrant_client, embedding_model
    )
    print("✅ AR Invoice ingested")

    # Ingest Regulations PDF using the existing pipeline
    regulations_path = "data/RPSR_RPSCSR_UAE.pdf"
    regulations_metadata = {"doc_name": "RPS_CSR_ENG.pdf", "source_type": "regulation"}
    ingest_document(regulations_path, regulations_metadata)
    print("✅ Regulations PDF ingested")

    # Ingest PO T&C PDF using the existing pipeline
    po_tc_path = "data/PO_T&C.pdf"
    po_tc_metadata = {"doc_name": "PO_T&C.pdf", "source_type": "terms_and_conditions"}
    ingest_document(po_tc_path, po_tc_metadata)
    print("✅ PO T&C PDF ingested")