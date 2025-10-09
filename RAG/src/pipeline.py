import json
import uuid
from qdrant_client.models import PointStruct

try:
    # Try relative imports first (when imported as package)
    from .parser import parse_pdf, parse_csv
    from .chunker import chunk_text
    from .embedding import embed_texts
    from .vectorstore_qdrant import init_collection, upsert_embeddings, search
    from .rerank import rerank
    from .llm_client import call_vllm
    from .redis_client import store_metadata, get_metadata
except ImportError:
    # Fallback to absolute imports (when imported directly)
    from parser import parse_pdf, parse_csv
    from chunker import chunk_text
    from embedding import embed_texts
    from vectorstore_qdrant import init_collection, upsert_embeddings, search
    from rerank import rerank
    from llm_client import call_vllm
    from redis_client import store_metadata, get_metadata


def load_template(template_name: str) -> str:
    """Load template string from insight_templates.json"""
    with open("RAG/prompts/insights.json", "r") as f:
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


def query_rag(query: str, template_name: str = "default", top_k: int = 20):
    q_vec = embed_texts([query])[0]
    results = search(q_vec, top_k=top_k)

    docs = []
    for r in results:
        chunk_id = r.payload["chunk_id"]
        full_metadata = get_metadata(chunk_id)
        docs.append(full_metadata["content"])

    reranked = rerank(query, docs)

    # Manually add all relevant data to the context (truncated for performance)
    invoice_ar_md = parse_csv("RAG/data/AR_Invoice.csv")[0]
    invoice_ap_md = parse_csv("RAG/data/AP_Invoice.csv")[0]
    po_terms_text = parse_pdf("RAG/data/PO_T&C.pdf")
    regulations_text = parse_pdf("RAG/data/RPSR_RPSCSR_UAE.pdf")

    # Truncate large documents to prevent timeout
    max_length = 5000
    invoice_ar_md = invoice_ar_md[:max_length] + "..." if len(invoice_ar_md) > max_length else invoice_ar_md
    invoice_ap_md = invoice_ap_md[:max_length] + "..." if len(invoice_ap_md) > max_length else invoice_ap_md
    po_terms_text = po_terms_text[:max_length] + "..." if len(po_terms_text) > max_length else po_terms_text
    regulations_text = regulations_text[:max_length] + "..." if len(regulations_text) > max_length else regulations_text

    context_parts = [
        "Accounts Receivable Data:",
        invoice_ar_md,
        "Accounts Payable Data:",
        invoice_ap_md,
        "Purchase Order Terms:",
        po_terms_text,
        "Regulations:",
        regulations_text,
        "Retrieved Context:",
        "\n\n".join(reranked[:5]),  # Limit to top 5 results
    ]

    context = "\n\n".join(context_parts)
    template = load_template(template_name)
    prompt = template.format(context=context, query=query)

    return call_vllm(prompt, max_tokens=1024)
