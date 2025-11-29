import os
import sys
import json
import argparse
from typing import Dict, List

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.embedding import embed_texts
from utils.vectorstore_qdrant import search
from utils.llm_client import call_llm
from qdrant_client import QdrantClient

try:
    from utils.config import QDRANT_API_KEY, REBATE_COLLECTION, QDRANT_URL
except ImportError:
    # Fallback for running from different directories
    from cfo_dashboard.utils.config import QDRANT_API_KEY, REBATE_COLLECTION, QDRANT_URL


def fetch_rebate_data(query: str) -> List[Dict[str, any]]:
    """
    Queries the Rebate collection and extracts supplier and discount info.
    """
    # Initialize Qdrant client
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # Embed the query
    query_vector = embed_texts([query])[0]

    # Search Qdrant collection
    search_results = search(REBATE_COLLECTION, query_vector, top_k=5)

    # Extract context from search results
    context_parts = [r.payload.get("page_content", "") for r in search_results]
    context = "\n---\n".join(filter(None, context_parts))

    if not context:
        return []

    # Strict extraction prompt
    prompt = f"""
You are an information extraction engine.
Extract ONLY information that is explicitly written in the text below.
Do NOT infer or guess.
If something does not appear, return null for that field.

Look for exact phrases such as:
 - "Supplier Name : <name>"
 - "There will be a discount of <number>%"
 - "Discount of <number>% if paid before"

Return a valid JSON array with this structure:

[
  {{
    "supplier_name": "<exact supplier name or null>",
    "discount_percentage": "<exact discount (with %) or null>"
  }}
]

If multiple suppliers or discounts appear, return each as a separate object in the array.

Context:
{context}
"""

    # Call the LLM
    llm_response = call_vllm(prompt)

    # Parse LLM JSON safely
    try:
        json_start = llm_response.find('[')
        json_end = llm_response.rfind(']') + 1
        if json_start != -1 and json_end > json_start:
            json_string = llm_response[json_start:json_end]
            extracted = json.loads(json_string)
        else:
            return []
    except json.JSONDecodeError:
        return []

    # Validate that values actually appear in context
    for item in extracted:
        supplier = item.get("supplier_name")
        discount = item.get("discount_percentage")

        if supplier and supplier.lower() not in context.lower():
            item["supplier_name"] = None
        if discount and discount.strip('%') not in context:
            item["discount_percentage"] = None

    return extracted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch rebate information from Qdrant.")
    parser.add_argument("query", type=str, help="The query to search for rebates.", default="Get all company discounts")
    args = parser.parse_args()

    rebates = fetch_rebate_data(args.query)
    print(json.dumps(rebates, indent=2))
