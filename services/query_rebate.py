import os
import sys
import json
from typing import Dict, List

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.embedding import embed_texts
from utils.vectorstore_qdrant import search
from utils.llm_client import call_vllm
from qdrant_client import QdrantClient
from utils.redis_client import get_metadata

try:
    from utils.config import QDRANT_API_KEY, REBATE_COLLECTION, QDRANT_URL
except ImportError:
    # Fallback for running from different directories
    from cfo_dashboard.utils.config import QDRANT_API_KEY, REBATE_COLLECTION, QDRANT_URL


def query_rebate_collection(query: str) -> List[Dict[str, any]]:
    """
    Queries the Rebate collection and extracts supplier and discount info.
    """
    # Initialize Qdrant client
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # Embed the query
    query_vector = embed_texts([query])[0]

    # Search Qdrant collection
    search_results = search(REBATE_COLLECTION, query_vector, top_k=30)

    # Group chunks by document name
    documents = {}
    for r in search_results:
        if "chunk_id" in r.payload:
            metadata = get_metadata(r.payload["chunk_id"])
            if metadata and "content" in metadata and "source" in metadata:
                doc_name = metadata["source"]
                if doc_name not in documents:
                    documents[doc_name] = []
                documents[doc_name].append(metadata["content"])

    if not documents:
        return []

    extracted_data = []
    for doc_name, chunks in documents.items():
        context = "\n---\n".join(chunks)

        # Strict extraction prompt
        prompt = f"""You are an information extraction engine.
Your task is to extract the supplier name and discount percentage from the provided text.

The supplier name is explicitly mentioned with the label \"Supplier Name:\".
The discount information can be found in a \"DISCOUNT\" section or under a numbered clause like \"4.4\".

Look for the following exact patterns:
- \"Supplier Name: <The supplier name>\"
- \"DISCOUNT: There will be a discount of <number>% if paid before Due date\"
- \"4.4 There will be a <number>% discount if paid before due date\"

Return a valid JSON object with this structure:
{{
  "supplier_name": "<exact supplier name or null>",
  "discount_percentage": "<exact discount (with %) or null>"
}}

Do NOT infer or guess. If the discount information is not explicitly in the text, return null for that field. but Definitely there will be supplier name.
It is very important to extract both the supplier name and the discount percentage.

Context:
{context}
"""

        # Call the LLM
        llm_response = call_vllm(prompt)

        # Parse LLM JSON safely
        try:
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_string = llm_response[json_start:json_end]
                extracted = json.loads(json_string)
                # Add doc_name to the extracted data
                extracted["document_name"] = doc_name
                extracted_data.append(extracted)
            else:
                continue
        except json.JSONDecodeError:
            continue

    return extracted_data

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Fetch rebate information from Qdrant.")
    parser.add_argument("query", type=str, help="The query to search for rebates.", default="Get all company discounts")
    args = parser.parse_args()

    rebates = query_rebate_collection(args.query)
    print(json.dumps(rebates, indent=2))