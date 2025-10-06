import json
import uuid
from qdrant_client.models import PointStruct

from utils.parser import parse_pdf, parse_csv
from utils.chunker import chunk_text
from utils.embedding import embed_texts
from utils.vectorstore_qdrant import init_collection, upsert_embeddings, search
from utils.rerank import rerank
from utils.llm_client import call_vllm
from utils.redis_client import store_metadata, get_metadata


def load_template(template_name: str) -> str:
    """Load template string from insight_templates.json"""
    with open("/home/ubuntu/cfo_dashboard/prompts/insights.json", "r") as f:
        templates = json.load(f)
    return templates.get(template_name, templates["default"])


def ingest_document(path: str, metadata: dict):
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
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        chunk_id = str(uuid.uuid4())
        full_metadata = {**metadata, "content": chunk, "chunk_id": chunk_id}
        store_metadata(chunk_id, full_metadata)

        points_to_upsert.append(
            PointStruct(
                id=chunk_id,
                vector=vector,
                payload={"chunk_id": chunk_id}  # Only store chunk_id in Qdrant payload
            )
        )

    upsert_embeddings(points_to_upsert)


from datetime import datetime, timedelta

def query_rag(query: str, template_name: str = "default", top_k: int = 20):
    q_vec = embed_texts([query])[0]
    results = search(q_vec, top_k=top_k)

    docs = []
    for r in results:
        chunk_id = r.payload["chunk_id"]
        full_metadata = get_metadata(chunk_id)
        if full_metadata and "content" in full_metadata:
            docs.append(full_metadata["content"])

    reranked = rerank(query, docs)

    # Manually add all relevant data to the context (truncated for performance)
    invoice_ar_md = parse_csv("/home/ubuntu/cfo_dashboard/data/AR_Invoice.csv")[0]
    invoice_ap_md = parse_csv("/home/ubuntu/cfo_dashboard/data/AP_Invoice.csv")[0]
    po_terms_text = parse_pdf("/home/ubuntu/cfo_dashboard/data/PO_T&C.pdf")
    regulations_text = parse_pdf("/home/ubuntu/cfo_dashboard/data/RPSR_RPSCSR_UAE.pdf")

    # Truncate large documents to prevent timeout
    max_length = 5000
    invoice_ar_md = invoice_ar_md[:max_length] + "..." if len(invoice_ar_md) > max_length else invoice_ar_md
    invoice_ap_md = invoice_ap_md[:max_length] + "..." if len(invoice_ap_md) > max_length else invoice_ap_md
    po_terms_text = po_terms_text[:max_length] + "..." if len(po_terms_text) > max_length else po_terms_text
    regulations_text = regulations_text[:max_length] + "..." if len(regulations_text) > max_length else regulations_text

    context_parts = [
        "Accounts Receivable Invoice Data:",
        invoice_ar_md,
        "Accounts Payable Data:",
        invoice_ap_md,
        "Purchase Order Terms:",
        po_terms_text,
        "Regulations:",
        regulations_text,
        "Retrieved Context:",
        "\n\n".join(reranked[:2]),  # Limit to top 5 results
    ]

    AR_context =["Accounts Receivable Invoice Data:",
        invoice_ar_md,
        "Regulations:",
        regulations_text,
        "Retrieved Context:",
        "\n\n".join(reranked[:2])]
    
    AP_context =["Accounts Payable Invoice Data:",
        invoice_ap_md,
        "Purchase Order Terms:",
        po_terms_text,
        "Regulations:",
        regulations_text,
        "Retrieved Context:",
        "\n\n".join(reranked[:2])]

    context = "\n\n".join(context_parts)
    AR_context = "\n\n".join(AR_context)
    AP_context = "\n\n".join(AP_context)
    template = load_template(template_name)

    now = datetime.now()
    current_date_str = now.strftime("%Y-%m-%d")
    date_plus_6_days_str = (now + timedelta(days=6)).strftime("%Y-%m-%d")
    template = template.replace("{current_date}", current_date_str)
    template = template.replace("{current_date_plus_6_days}", date_plus_6_days_str)
    
    prompt = template.format(context=context, query=query, AR_context=AR_context, AP_context=AP_context)

    return call_vllm(prompt, max_tokens=1024)