"""RAG pipeline utilities for document processing — Enhanced for CFO dashboard."""

from datetime import datetime, timedelta
import json
import os

import pandas as pd
from prompts.rag_chatbot import RAG_CHATBOT_PROMPT

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
from utils.redis_client import get_metadata
from utils.rerank import rerank
from utils.vectorstore_qdrant import search
from utils.data_refresh import check_and_update_data

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
    collections_map = {
        "po": PO_TC_COLLECTION,
        "reg": REGULATIONS_COLLECTION,
        "ar": AR_INVOICE_COLLECTION,
        "ap": AP_INVOICE_COLLECTION,
        "rebate": REBATE_COLLECTION,
    }

    docs_by_collection = {key: [] for key in collections_map}
    all_docs = []

    for name, coll in collections_map.items():
        try:
            results = search(coll, q_vec, top_k=top_k)
            
            # Retrieve content for each collection
            coll_docs = []
            for r in results:
                content = None
                if "chunk_id" in r.payload:
                    meta = get_metadata(r.payload["chunk_id"])
                    if meta and "content" in meta:
                        content = meta["content"]
                elif "content" in r.payload:  # Fallback
                    content = r.payload["content"]
                
                if content:
                    coll_docs.append(content)

            docs_by_collection[name] = coll_docs
            all_docs.extend(coll_docs)

        except Exception as e:
            print(f"⚠️ Skipped search for {coll}: {e}")

    # Step 3 & 4 — Rerank all retrieved documents
    reranked_docs = rerank(query, all_docs)
    top_matches = "\n\n".join(reranked_docs[:2])

    # Step 5 — Load invoice data and construct document contexts from search
    ar_df = pd.read_csv("data/AR_Invoice.csv")
    ap_df = pd.read_csv("data/AP_Invoice.csv")
    
    # Use retrieved chunks instead of parsing full PDFs
    po_text = "\n\n".join(docs_by_collection["po"])
    reg_text = "\n\n".join(docs_by_collection["reg"])

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
    template = RAG_CHATBOT_PROMPT
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

def query_insights(query: str, data_context: str, template_name: str):
    """
    Lightweight query function for structured insight generation (warnings/opportunities)
    that bypasses full RAG context to prevent unwanted markdown or table formatting.
    """
    print(f"\n🔍 Running RAG Query: {query}\n")

    # Step 1 — Ensure data freshness
    check_and_update_data()

    # Load the strict plain-text template
    template = load_template(template_name)

    # Build a minimal, controlled prompt (no CSV tables or regulatory context)
    prompt = template.format(
        query=query,
        context=data_context,
        AR_context=data_context,
        AP_context=data_context,
        regulations_context="",
        PO_context="",
    )

    # Send to LLM
    response = call_vllm(prompt, max_tokens=512)
    print("✅ Query Insights response received.\n")

    return response