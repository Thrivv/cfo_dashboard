import json
import uuid
from datetime import datetime, timedelta
import pandas as pd
from qdrant_client.models import PointStruct

# Local utility imports
from utils.parser import parse_pdf, parse_csv
from utils.chunker import chunk_text
from utils.embedding import embed_texts
from utils.vectorstore_qdrant import init_collection, upsert_embeddings, search
from utils.rerank import rerank
from utils.llm_client import call_vllm
from utils.redis_client import store_metadata, get_metadata


# -------- Template Loader --------
def load_template(template_name: str) -> str:
    """Load the selected template from insights.json"""
    with open("/home/ubuntu/cfo_dashboard/prompts/insights.json", "r") as f:
        templates = json.load(f)
    return templates.get(template_name, templates["default"])


# -------- Ingestion Pipeline --------
def ingest_document(path: str, metadata: dict):
    """Embed and index documents (PDF or CSV) into Qdrant"""
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
            PointStruct(
                id=chunk_id,
                vector=vector,
                payload={"chunk_id": chunk_id}
            )
        )

    upsert_embeddings(points_to_upsert)


# -------- Query Pipeline (Unified RAG + Invoice Logic) --------
def query_rag(query: str, template_name: str = "default", top_k: int = 20):
    """Main RAG query pipeline with intelligent invoice filtering and context composition"""
    
    # Step 1: Vector Search + Rerank
    q_vec = embed_texts([query])[0]
    results = search(q_vec, top_k=top_k)
    docs = [get_metadata(r.payload["chunk_id"])["content"] for r in results]
    reranked = rerank(query, docs)

    # Step 2: Load and preprocess data
    ar_df = pd.read_csv("/home/ubuntu/cfo_dashboard/data/AR_Invoice.csv")
    ap_df = pd.read_csv("/home/ubuntu/cfo_dashboard/data/AP_Invoice.csv")
    po_text = parse_pdf("/home/ubuntu/cfo_dashboard/data/PO_T&C.pdf")
    reg_text = parse_pdf("/home/ubuntu/cfo_dashboard/data/RPSR_RPSCSR_UAE.pdf")

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

    ar_csv, ap_csv = truncate(ar_filtered.to_csv(index=False)), truncate(ap_filtered.to_csv(index=False))
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
{'\n\n'.join(reranked[:2])}
"""

    AR_context = "\n\n".join([
        "Accounts Receivable Invoice Data:", ar_csv,
        "Regulations:", reg_text,
        "Retrieved Context:", "\n\n".join(reranked[:2])
    ])

    AP_context = "\n\n".join([
        "Accounts Payable Invoice Data:", ap_csv,
        "Purchase Order Terms:", po_text,
        "Regulations:", reg_text,
        "Retrieved Context:", "\n\n".join(reranked[:2])
    ])

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
        PO_context=po_text
    )

    # Step 8: Call LLM (Runpod / vLLM)
    return call_vllm(prompt, max_tokens=1024)
