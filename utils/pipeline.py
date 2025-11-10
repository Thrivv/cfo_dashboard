"""RAG pipeline utilities for document processing — Enhanced for CFO dashboard."""

from datetime import datetime, timedelta
import json
import os
import uuid

import pandas as pd
from qdrant_client.models import PointStruct

from services.rebate import extract_and_dump_rebates
from services.apply_and_save_rebates import apply_and_save_rebates
from utils.chunker import chunk_text
from utils.clear_data import clear_qdrant_collection
from utils.embedding import embed_texts
from utils.llm_client import call_vllm
from utils.config import (
    AR_INVOICE_COLLECTION,
    AP_INVOICE_COLLECTION,
    PO_TC_COLLECTION,
    REGULATIONS_COLLECTION,
    REBATE_COLLECTION,
)

# Local utility imports
from utils.parser import parse_csv, parse_pdf
from utils.redis_client import get_metadata, store_metadata, redis_client
from utils.rerank import rerank
from utils.vectorstore_qdrant import (
    init_collection,
    search,
    upsert_embeddings,
    qdrant_client,
)


# ---------------------------------------------------------------------------
# Step 1 — Invoice Update Logic
# ---------------------------------------------------------------------------


def update_invoice_status_and_save(file_path: str):
    """Reads a CSV file, adds/updates a 'Status' column with relative due date info, and saves it."""
    df = pd.read_csv(file_path)
    today = datetime.now().date()

    def get_status(row):
        try:
            due_date = pd.to_datetime(row["Due Date"], errors="coerce").date()
        except Exception:
            return "unknown"
        payment_status = str(row["Payment Status"]).lower().strip()

        if payment_status == "paid":
            return "paid"

        if not due_date:
            return "unknown"

        delta = (due_date - today).days
        if delta < 0:
            return f"overdue ({abs(delta)} days ago)"
        elif delta == 0:
            return "upcoming (today)"
        elif 0 < delta <= 7:
            return f"upcoming ({delta} days remaining)"
        else:
            return f"future ({delta} days remaining)"

    df["Status"] = df.apply(get_status, axis=1)
    df.to_csv(file_path, index=False)
    print(f"✅ Updated invoice statuses for {os.path.basename(file_path)}")


# ---------------------------------------------------------------------------
# Step 1.5 — Selective Redis Metadata Deletion
# ---------------------------------------------------------------------------


def delete_redis_metadata_for_collection(collection_name: str):
    """Deletes all Redis metadata associated with a Qdrant collection."""
    try:
        print(f"Fetching chunk_ids from {collection_name} to clear from Redis...")

        all_points = []
        offset = None
        while True:
            response, next_page_offset = qdrant_client.scroll(
                collection_name=collection_name,
                limit=100,
                with_payload=["chunk_id"],
                offset=offset,
            )
            all_points.extend(response)
            if not next_page_offset:
                break
            offset = next_page_offset

        chunk_ids = [
            point.payload["chunk_id"]
            for point in all_points
            if point.payload and "chunk_id" in point.payload
        ]

        if chunk_ids:
            pipe = redis_client.pipeline()
            for chunk_id in chunk_ids:
                pipe.delete(chunk_id)
            pipe.execute()
            print(
                f"✅ Deleted {len(chunk_ids)} metadata keys from Redis for {collection_name}."
            )
        else:
            print(f"ℹ️ No metadata found in Redis for {collection_name}.")

    except Exception as e:
        print(f"⚠️ Error clearing Redis metadata for {collection_name}: {e}")


# ---------------------------------------------------------------------------
# Step 2 — Rebate Update Logic
# ---------------------------------------------------------------------------


def check_for_new_rebate_files_and_apply():
    """
    Checks for new files in the rebate directory and applies rebates if new files are found.
    """
    rebate_dir = "data/Rebate/"
    processed_files_cache = "data/processed_rebate_files.json"

    # Get current files and their modification times
    current_files = {}
    if os.path.exists(rebate_dir):
        for filename in os.listdir(rebate_dir):
            filepath = os.path.join(rebate_dir, filename)
            if os.path.isfile(filepath):
                current_files[filename] = os.path.getmtime(filepath)

    # Load processed files cache
    processed_files = {}
    if os.path.exists(processed_files_cache):
        with open(processed_files_cache, "r") as f:
            try:
                processed_files = json.load(f)
            except json.JSONDecodeError:
                processed_files = {}  # Handle empty or corrupt file

    # Check for new or modified files
    new_or_modified_files = False
    if set(current_files.keys()) != set(processed_files.keys()):
        new_or_modified_files = True
    else:
        for filename, mtime in current_files.items():
            if processed_files.get(filename, 0) < mtime:
                new_or_modified_files = True
                break

    if new_or_modified_files:
        print(
            "🚀 New or modified rebate file detected — re-ingesting rebates and applying..."
        )

        # 1. Clear and re-ingest rebate documents
        print("🧹 Clearing and re-ingesting rebate collection...")
        delete_redis_metadata_for_collection(REBATE_COLLECTION)
        clear_qdrant_collection(REBATE_COLLECTION)

        for filename in os.listdir(rebate_dir):
            if filename.endswith(".pdf"):  # Assuming they are PDFs
                filepath = os.path.join(rebate_dir, filename)
                ingest_document(
                    path=filepath,
                    metadata={"doc_type": "rebate_document", "source": filename},
                    collection_name=REBATE_COLLECTION,
                )
        print("✅ Rebate documents ingested.")

        # 2. Apply rebates to AP invoices
        print("Applying rebates to AP invoices...")
        extract_and_dump_rebates()
        apply_and_save_rebates()
        print("✅ Rebates applied.\n")

        # 3. Update the processed files cache
        with open(processed_files_cache, "w") as f:
            json.dump(current_files, f)
    else:
        print("ℹ️ Rebate files are up-to-date.")


# ---------------------------------------------------------------------------
# Step 2.5 — Daily Invoice Refresh (Clear + Re-ingest)
# ---------------------------------------------------------------------------


def check_and_update_data():
    """
    Checks for new rebate files and applies rebates.
    If a new day has started, it also runs the clearing and ingestion scripts for invoices.
    """
    # Check for new rebate files and apply if necessary
    check_for_new_rebate_files_and_apply()

    date_cache_file = "data/last_update_date.txt"
    today_str = datetime.now().strftime("%Y-%m-%d")

    last_update_date = ""
    if os.path.exists(date_cache_file):
        with open(date_cache_file, "r") as f:
            last_update_date = f.read().strip()

    if last_update_date != today_str:
        print("🚀 New day detected — refreshing invoice data pipeline...")

        # 1. Clear AP and AR metadata from Redis
        print("🧹 Clearing AP and AR metadata from Redis...")
        delete_redis_metadata_for_collection(AR_INVOICE_COLLECTION)
        delete_redis_metadata_for_collection(AP_INVOICE_COLLECTION)

        # 2. Clear only invoice collections from Qdrant
        print("🧹 Clearing AP and AR invoice collections from Qdrant...")
        clear_qdrant_collection(AR_INVOICE_COLLECTION)
        clear_qdrant_collection(AP_INVOICE_COLLECTION)
        print("✅ Cleared Qdrant invoice collections.\n")

        # 3. Update invoice CSV statuses
        print("🔄 Updating invoice CSV files with current status...")
        update_invoice_status_and_save("data/AP_Invoice.csv")
        update_invoice_status_and_save("data/AR_Invoice.csv")

        # 4. Run ingestion for AR and AP
        print("🚚 Ingesting refreshed AP and AR data into Qdrant...")
        ingest_document(
            path="data/AP_Invoice.csv",
            metadata={"doc_type": "ap_invoice", "source": "AP_Invoice.csv"},
            collection_name=AP_INVOICE_COLLECTION,
        )
        ingest_document(
            path="data/AR_Invoice.csv",
            metadata={"doc_type": "ar_invoice", "source": "AR_Invoice.csv"},
            collection_name=AR_INVOICE_COLLECTION,
        )
        print("✅ Ingested refreshed AP and AR data.\n")

        # 5. Update the refresh timestamp
        with open(date_cache_file, "w") as f:
            f.write(today_str)

        print("✅ Data refresh complete for today.\n")
    else:
        print("ℹ️ Invoice data already up-to-date for today.\n")


# ---------------------------------------------------------------------------
# Step 3 — Prompt Template Loader
# ---------------------------------------------------------------------------


def load_template(template_name: str) -> str:
    """Load the selected template from insights.json."""
    try:
        with open("prompts/insights.json", "r") as f:
            templates = json.load(f)
        return templates.get(template_name, templates.get("qa_template", ""))
    except Exception as e:
        print(f"⚠️ Error loading prompt template: {e}")
        return ""


# ---------------------------------------------------------------------------
# Step 4 — Ingestion Pipeline (For PDFs and CSVs)
# ---------------------------------------------------------------------------


def ingest_document(path: str, metadata: dict, collection_name: str):
    """
    Generic document ingestion for PDFs or CSVs.
    Uses hybrid chunking for text and stores chunk metadata in Redis.
    """
    if path.endswith(".pdf"):
        text = parse_pdf(path)
        chunks = chunk_text(text)
    elif path.endswith(".csv"):
        chunks = parse_csv(path)
    else:
        raise ValueError("Unsupported file type")

    vectors = embed_texts(chunks)
    init_collection(collection_name, len(vectors[0]))

    points_to_upsert = []
    for chunk, vector in zip(chunks, vectors):
        chunk_id = str(uuid.uuid4())
        full_metadata = {**metadata, "content": chunk, "chunk_id": chunk_id}
        store_metadata(chunk_id, full_metadata)

        payload = {"chunk_id": chunk_id}
        if collection_name == REBATE_COLLECTION:
            payload["doc_name"] = metadata.get("doc_name")

        points_to_upsert.append(
            PointStruct(id=chunk_id, vector=vector, payload=payload)
        )

    upsert_embeddings(collection_name, points_to_upsert)
    print(f"✅ Ingested {len(points_to_upsert)} chunks into {collection_name}")


# ---------------------------------------------------------------------------
# Step 5 — Querying Rebate Collection
# ---------------------------------------------------------------------------


def query_rebate_collection(query: str, top_k: int = 20):
    """Query the rebate collection and return concatenated chunk contents."""
    q_vec = embed_texts([query])[0]
    results = search(REBATE_COLLECTION, q_vec, top_k=top_k)

    docs = []
    for r in results:
        if "chunk_id" in r.payload:
            metadata = get_metadata(r.payload["chunk_id"])
            if metadata and "content" in metadata:
                docs.append(metadata["content"])
        elif "content" in r.payload:
            docs.append(r.payload["content"])

    return "\n\n".join(docs)


# ---------------------------------------------------------------------------
# Step 6 — Main Unified RAG Query Pipeline
# ---------------------------------------------------------------------------


def query_rag(query: str, template_name: str = "qa_template", top_k: int = 20):
    """
    Unified RAG pipeline with invoice logic, semantic retrieval,
    reranking, and regulatory/PO context composition.
    """
    print(f"\n🔍 Running RAG Query: {query}\n")

    # Step 1 — Ensure data freshness
    check_and_update_data()

    # Step 2 — Vector Search across all collections
    q_vec = embed_texts([query])[0]
    collections = [
        AR_INVOICE_COLLECTION,
        AP_INVOICE_COLLECTION,
        PO_TC_COLLECTION,
        REGULATIONS_COLLECTION,
        REBATE_COLLECTION,
    ]

    all_results = []
    for coll in collections:
        try:
            results = search(coll, q_vec, top_k=top_k)
            all_results.extend(results)
        except Exception as e:
            print(f"⚠️ Skipped {coll}: {e}")

    # Step 3 — Retrieve document chunks
    docs = []
    for r in all_results:
        if "chunk_id" in r.payload:
            meta = get_metadata(r.payload["chunk_id"])
            if meta and "content" in meta:
                docs.append(meta["content"])
        elif "content" in r.payload:
            docs.append(r.payload["content"])

    # Step 4 — Rerank results
    reranked = rerank(query, docs)
    top_matches = "\n\n".join(reranked[:2])

    # Step 5 — Load invoice data + external docs
    ar_df = pd.read_csv("data/AR_Invoice.csv")
    ap_df = pd.read_csv("data/AP_Invoice.csv")
    po_text = parse_pdf("data/PO_T&C.pdf")
    reg_text = parse_pdf("data/RPSR_RPSCSR_UAE.pdf")

    # Step 6 — Normalize Due Dates and Status
    for df in [ar_df, ap_df]:
        if "Due Date" in df.columns:
            df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")

    today = datetime.now().date()
    next_week = today + timedelta(days=7)

    def label_status(df):
        """Derive status labels for each invoice."""

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

    # Step 7 — Filter by intent keywords
    q_lower = query.lower()
    if any(k in q_lower for k in ["upcoming", "this week", "next week"]):
        ar_filtered = ar_df[ar_df["Status"] == "Upcoming"]
        ap_filtered = ap_df[ap_df["Status"] == "Upcoming"]
    elif any(k in q_lower for k in ["overdue", "late", "crossed"]):
        ar_filtered = ar_df[ar_df["Status"] == "Overdue"]
        ap_filtered = ap_df[ap_df["Status"] == "Overdue"]
    elif "paid" in q_lower:
        ar_filtered = ar_df[ar_df["Status"] == "Paid"]
        ap_filtered = ap_df[ap_df["Status"] == "Paid"]
    else:
        ar_filtered, ap_filtered = ar_df, ap_df

    # Step 8 — Prepare CSV and document contexts
    def truncate(txt, max_len=6000):
        return txt[:max_len] + "..." if len(txt) > max_len else txt

    ar_csv = truncate(ar_filtered.to_csv(index=False))
    ap_csv = truncate(ap_filtered.to_csv(index=False))
    po_text = truncate(po_text)
    reg_text = truncate(reg_text)

    # Step 9 — Compose RAG context
    context = f"""
Accounts Receivable (AR) Data:
{ar_csv}

Accounts Payable (AP) Data:
{ap_csv}

Purchase Order Terms (PO):
{po_text}

Regulatory Documents:
{reg_text}

Top Retrieved Context:
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

    # Step 10 — Format LLM Prompt
    template = load_template(template_name)
    now_str = datetime.now().strftime("%Y-%m-%d")
    next_week_str = next_week.strftime("%Y-%m-%d")

    template = template.replace("{current_date}", now_str)
    template = template.replace("{current_date_plus_6_days}", next_week_str)

    prompt = template.format(
        context=context,
        query=query,
        Only_AR=ar_csv,
        Only_AP=ap_csv,
        AR_context=AR_context,
        AP_context=AP_context,
        regulations_context=reg_text,
        PO_context=po_text,
    )

    # Step 11 — Run LLM Call via RunPod/vLLM
    print("🧠 Sending contextualized query to LLM...")
    response = call_vllm(prompt, max_tokens=1024)
    print("✅ Response received.\n")

    return response
