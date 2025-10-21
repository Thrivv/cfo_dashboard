"""RAG pipeline utilities for document processing."""

from datetime import datetime, timedelta
import json
import os
import uuid

import pandas as pd
from qdrant_client.models import PointStruct

from utils.chunker import chunk_text
from utils.clear_data import clear_all_qdrant, clear_all_redis
from utils.embedding import embed_texts
from utils.llm_client import call_vllm

# Local utility imports
from utils.parser import parse_csv, parse_pdf
from utils.redis_client import get_metadata, store_metadata
from utils.rerank import rerank
from utils.vectorstore_qdrant import init_collection, search, upsert_embeddings


def update_invoice_status_and_save(file_path: str):
    """Reads a CSV file, adds/updates a 'Status' column, and saves it."""
    df = pd.read_csv(file_path)
    today = datetime.now().date()

    def get_status(row):
        due_date = pd.to_datetime(row["Due Date"]).date()
        payment_status = str(row["Payment Status"]).lower().strip()

        if payment_status == "paid":
            return "paid"

        delta = (due_date - today).days

        if delta < 0:
            return f"overdue ({abs(delta)} days ago)"
        elif 0 <= delta <= 7:
            return f"upcoming ({delta} days remaining)"
        else:
            return f"future ({delta} days remaining)"

    df["Status"] = df.apply(get_status, axis=1)
    df.to_csv(file_path, index=False)


def check_and_update_data():
    """
    Checks the last update date and runs the clearing and ingestion scripts if a new day has started.
    """
    # Import here to avoid circular dependency
    from utils.ingest import ingest_all_data

    date_cache_file = "data/last_update_date.txt"
    today_str = datetime.now().strftime("%Y-%m-%d")

    last_update_date = ""
    if os.path.exists(date_cache_file):
        with open(date_cache_file, "r") as f:
            last_update_date = f.read().strip()

    if last_update_date != today_str:
        print("🚀 New day detected. Clearing old data and ingesting fresh data...")

        # 1. Clear all existing data from Qdrant and Redis
        print("🧹 Clearing Qdrant and Redis data...")
        clear_all_qdrant()
        clear_all_redis()
        print("✅ Caches, vectors, and metadata wiped clean.")

        # 2. Update invoice CSV files with the latest status
        print("🔄 Updating invoice statuses...")
        update_invoice_status_and_save("/home/rohith/Git_Thrivv/Git_Use_Thrivv/cfo_new/cfo_dashboard/data/AP_Invoice.csv")
        update_invoice_status_and_save("/home/rohith/Git_Thrivv/Git_Use_Thrivv/cfo_new/cfo_dashboard/data/AR_Invoice.csv")
        print("✅ Invoice statuses updated.")

        # 3. Ingest all data from scratch
        print("🚚 Ingesting fresh data...")
        ingest_all_data()

        # 4. Update the date cache to prevent re-running today
        with open(date_cache_file, "w") as f:
            f.write(today_str)

        print("✅ Data refresh complete for today.")
    else:
        print("ℹ️ Data is already up-to-date for today.")


# -------- Template Loader --------
def load_template(template_name: str) -> str:
    """Load the selected template from insights.json."""
    with open("prompts/insights.json", "r") as f:
        templates = json.load(f)
    return templates.get(template_name, templates["default"])


# -------- Ingestion Pipeline --------
def ingest_document(path: str, metadata: dict):
    """Embed and index documents (PDF or CSV) into Qdrant."""
    if path.endswith(".pdf"):
        text = parse_pdf(path)
        chunks = chunk_text(text)
    elif path.endswith(".csv"):
        chunks = parse_csv(path)
    else:
        raise ValueError("Unsupported file type")

    vectors = embed_texts(chunks)
    init_collection(len(vectors[0]))

    points_to_upsert = []
    for chunk, vector in zip(chunks, vectors):
        chunk_id = str(uuid.uuid4())
        full_metadata = {**metadata, "content": chunk, "chunk_id": chunk_id}
        store_metadata(chunk_id, full_metadata)

        points_to_upsert.append(
            PointStruct(id=chunk_id, vector=vector, payload={"chunk_id": chunk_id})
        )

    upsert_embeddings(points_to_upsert)


# -------- Query Pipeline (Unified RAG + Invoice Logic) --------
def query_rag(query: str, template_name: str = "default", top_k: int = 20):
    """Main RAG query pipeline with intelligent invoice filtering and context composition."""
    # Check and update data at the beginning of the pipeline
    check_and_update_data()

    # Step 1: Vector Search + Rerank
    q_vec = embed_texts([query])[0]
    results = search(q_vec, top_k=top_k)
    docs = []
    for r in results:
        metadata = get_metadata(r.payload["chunk_id"])
        if metadata and "content" in metadata:
            docs.append(metadata["content"])
    reranked = rerank(query, docs)
    top_matches = "\n\n".join(reranked[:2])

    # Step 2: Load and preprocess data
    ar_df = pd.read_csv("data/AR_Invoice.csv")
    ap_df = pd.read_csv("data/AP_Invoice.csv")
    po_text = parse_pdf("data/PO_T&C.pdf")
    reg_text = parse_pdf("data/RPSR_RPSCSR_UAE.pdf")

    # Normalize dates
    for df in [ar_df, ap_df]:
        if "Due Date" in df.columns:
            df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")

    today = datetime.now().date()
    next_week = today + timedelta(days=7)

    # Step 3: Label status based on payment & due date
    def label_status(df):
        def status_fn(row):
            if pd.isna(row["Due Date"]):
                return "Unknown"
            elif str(row["Payment Status"]).lower() != "not paid":
                return "Paid"
            elif row["Due Date"].date() < today:
                return "Overdue"
            elif today <= row["Due Date"].date() <= next_week:
                return "Upcoming"
            else:
                return "Future"

        df["Status"] = df.apply(status_fn, axis=1)
        return df

    ar_df, ap_df = label_status(ar_df), label_status(ap_df)

    # Step 4: Query intent filtering
    q_lower = query.lower()
    if any(k in q_lower for k in ["upcoming", "this week", "next week"]):
        ar_filtered = ar_df[ar_df["Status"] == "Upcoming"]
        ap_filtered = ap_df[ap_df["Status"] == "Upcoming"]
    elif any(k in q_lower for k in ["overdue", "late", "crossed"]):
        ar_filtered = ar_df[ar_df["Status"] == "Overdue"]
        ap_filtered = ap_df[ap_df["Status"] == "Overdue"]
    else:
        ar_filtered, ap_filtered = ar_df, ap_df

    # Step 5: Prepare context strings
    def truncate(txt, max_len=5000):
        return txt[:max_len] + "..." if len(txt) > max_len else txt

    ar_csv, ap_csv = truncate(ar_filtered.to_csv(index=False)), truncate(
        ap_filtered.to_csv(index=False)
    )
    po_text, reg_text = truncate(po_text), truncate(reg_text)

    # Step 6: Build full context
    context = f"""
Accounts Receivable (AR) Data:
{ar_csv}

Accounts Payable (AP) Data:
{ap_csv}

Purchase Order Terms:
{po_text}

Regulatory Context:
{reg_text}

Retrieved Context (Top Matches):
{top_matches}
"""

    AR_context = "\n\n".join(
        [
            "Accounts Receivable Invoice Data:",
            ar_csv,
            "Regulations:",
            reg_text,
            "Retrieved Context:",
            top_matches,
        ]
    )

    AP_context = "\n\n".join(
        [
            "Accounts Payable Invoice Data:",
            ap_csv,
            "Purchase Order Terms:",
            po_text,
            "Regulations:",
            reg_text,
            "Retrieved Context:",
            top_matches,
        ]
    )

    # Step 7: Template formatting
    template = load_template(template_name)
    now_str = datetime.now().strftime("%Y-%m-%d")
    next_week_str = next_week.strftime("%Y-%m-%d")

    template = template.replace("{current_date}", now_str)
    template = template.replace("{current_date_plus_6_days}", next_week_str)

    prompt = template.format(
        context=context,
        query=query,
        AR_context=AR_context,
        AP_context=AP_context,
        regulations_context=reg_text,
        PO_context=po_text,
    )

    # Step 8: Call LLM (Runpod / vLLM)
    return call_vllm(prompt, max_tokens=1024)
