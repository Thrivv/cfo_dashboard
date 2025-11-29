"""Data ingestion utilities for the CFO dashboard — Enhanced version with typed payloads and Qdrant indexes."""

import os
import sys
import uuid
from datetime import datetime

import pandas as pd
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from utils.redis_client import store_metadata

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import (
    EMBEDDING_MODEL,
    QDRANT_API_KEY,
    QDRANT_URL,
    AR_INVOICE_COLLECTION,
    AP_INVOICE_COLLECTION,
    PO_TC_COLLECTION,
    REGULATIONS_COLLECTION,
    REBATE_COLLECTION,
)


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def epoch_from_date_str(date_str: str):
    """Convert string date to Unix epoch for numeric filtering."""
    if not date_str or str(date_str).lower() in ("nan", "none", ""):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            dt = datetime.strptime(str(date_str), fmt)
            return int(dt.timestamp())
        except Exception:
            continue
    try:
        return int(datetime.fromisoformat(str(date_str)).timestamp())
    except Exception:
        return None


def ensure_collection_and_indexes(client: QdrantClient, collection_name: str, embedding_dim: int):
    """Ensure the collection exists and has necessary payload indexes."""
    try:
        client.get_collection(collection_name=collection_name)
        print(f"Collection '{collection_name}' already exists.")
    except Exception:
        print(f"Creating collection '{collection_name}' with vector size {embedding_dim}...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=embedding_dim, distance=models.Distance.COSINE),
        )

    # Create common payload indexes
    index_fields = {
        "payment_status_keyword": "keyword",
        "invoice_no": "keyword",
        "doc_name": "keyword",
        "amount_value": "float",
        "due_date_epoch": "integer",
    }

    for field, schema in index_fields.items():
        try:
            client.create_payload_index(collection_name=collection_name, field_name=field, field_schema=schema)
            print(f"✅ Created payload index on '{field}' for '{collection_name}'.")
        except Exception as e:
            # Already exists or other non-critical error
            print(f"ℹ️ Could not create payload index '{field}' for '{collection_name}': {e}")


def ingest_csv_row_as_point(row, file_path, embedding_model):
    """Convert one CSV row into a Qdrant PointStruct with typed payloads."""
    # Determine name field
    name_field = "Supplier Name" if "Supplier Name" in row else "Customer Name"
    name = row.get(name_field, "")

    # Build semantic text chunk
    text_chunk = (
        f"Invoice record: Invoice No. {row.get('Invoice No.', '')}, issued on {row.get('Invoice Date', '')}, "
        f"from {row.get('Supplier Name', '')} for {row.get('Service Description', '')}. "
        f"The original amount is {row.get('Amount (AED)', '')} AED. "
        f"Final amount with penalty is {row.get('Final Amount with Penalty', '')} AED, "
        f"and final amount with discount is {row.get('Final Amount with Discount', '')} AED. "
        f"The VAT TRN is {row.get('VAT TRN', '')} with a VAT rate of {row.get('VAT %', '')}%. "
        f"The payment status is '{row.get('Payment Status', '')}', with a due date of {row.get('Due Date', '')} "
        f"and paid date recorded as {row.get('Paid Date', '')}. "
        f"Status: {row.get('Status', '')}. "
        f"Discount applied: {row.get('Discount', '')} (Note: {row.get('Discount Note', '')}). "
        f"Penalty applied: {row.get('Penalty', '')} (Note: {row.get('Penalty Note', '')})."
   )

    embedding = embedding_model.encode(text_chunk).tolist()
    point_id = str(uuid.uuid4())

    # Build typed payload
    payload = row.to_dict()
    payload["source_file"] = file_path
    payload["content"] = text_chunk
    payload["doc_name"] = os.path.basename(file_path)
    payload["invoice_no"] = str(row.get("Invoice No.", "")).strip()
    payload["chunk_id"] = point_id

    # Normalize amount
    try:
        payload["amount_value"] = float(str(row.get("Amount (AED)", "")).replace(",", "").strip() or 0.0)
    except Exception:
        payload["amount_value"] = None

    # Normalize payment status
    payload["payment_status_keyword"] = str(row.get("Payment Status", "")).strip().lower()

    # Add epoch date fields
    payload["due_date_epoch"] = epoch_from_date_str(row.get("Due Date", ""))
    payload["paid_date_epoch"] = epoch_from_date_str(row.get("Paid Date", ""))
    
    store_metadata(point_id, payload)

    return models.PointStruct(id=point_id, vector=embedding, payload=payload)


def ingest_csv_to_qdrant_enhanced(file_path, collection_name, client, embedding_model):
    """Read CSV, prepare points, ensure collection & indexes, and ingest."""
    try:
        df = pd.read_csv(file_path)
        embedding_dim = embedding_model.get_sentence_embedding_dimension()

        ensure_collection_and_indexes(client, collection_name, embedding_dim)

        points = []
        for _, row in df.iterrows():
            point = ingest_csv_row_as_point(row, file_path, embedding_model)
            points.append(point)

        print(f"Ingesting {len(points)} points into '{collection_name}'...")
        client.upsert(collection_name=collection_name, points=points)
        print(f"✅ Ingestion for '{collection_name}' completed.")

    except Exception as e:
        print(f"❌ Error during ingestion for {file_path}: {e}")


# ---------------------------------------------------------------------------
# Master Ingestion Entry Point
# ---------------------------------------------------------------------------

def ingest_all_data():
    """Initialize client/model and ingest all CFO datasets into Qdrant."""
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    # --- Ingest AP Invoices ---
    ap_invoice_path = "data/AP_Invoice.csv"
    ingest_csv_to_qdrant_enhanced(ap_invoice_path, AP_INVOICE_COLLECTION, qdrant_client, embedding_model)
    print("✅ AP Invoices ingested\n")

    # --- Ingest AR Invoices ---
    ar_invoice_path = "data/AR_Invoice.csv"
    ingest_csv_to_qdrant_enhanced(ar_invoice_path, AR_INVOICE_COLLECTION, qdrant_client, embedding_model)
    print("✅ AR Invoices ingested\n")

    # --- Ingest Regulations PDF ---
    regulations_path = "data/RPSR_RPSCSR_UAE.pdf"
    regulations_metadata = {"doc_name": "RPSR_RPSCSR_UAE.pdf", "source_type": "regulation"}
    ingest_document(regulations_path, regulations_metadata, REGULATIONS_COLLECTION)
    print("✅ Regulations PDF ingested\n")

    # --- Ingest PO Terms & Conditions PDF ---
    po_tc_path = "data/PO_T&C.pdf"
    po_tc_metadata = {"doc_name": "PO_T&C.pdf", "source_type": "terms_and_conditions"}
    ingest_document(po_tc_path, po_tc_metadata, PO_TC_COLLECTION)
    print("✅ PO T&C PDF ingested\n")

    # --- Ingest Rebate PDFs ---
    rebate_dir = "data/Rebate"
    if os.path.exists(rebate_dir):
        for rebate_file in os.listdir(rebate_dir):
            if rebate_file.endswith(".pdf"):
                rebate_path = os.path.join(rebate_dir, rebate_file)
                rebate_metadata = {"doc_name": rebate_file, "source_type": "rebate"}
                ingest_document(rebate_path, rebate_metadata, REBATE_COLLECTION)
                print(f"✅ Rebate PDF {rebate_file} ingested")
    else:
        print("⚠️ No rebate directory found — skipping.")


# ---------------------------------------------------------------------------
# Script Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ingest_all_data()
