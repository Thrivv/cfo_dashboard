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

from utils.config import QDRANT_API_KEY, REBATE_COLLECTION, QDRANT_URL

def query_rebate_collection(query: str) -> List[Dict[str, any]]:
    """
    Queries the Rebate collection and dynamically extracts supplier and discount/penalty info.
    """
    from utils.embedding import embed_texts
    from utils.vectorstore_qdrant import search
    from utils.llm_client import call_vllm
    from utils.redis_client import get_metadata
    from qdrant_client import QdrantClient
    from utils.config import QDRANT_API_KEY, REBATE_COLLECTION, QDRANT_URL
    import json

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    query_vector = embed_texts([query])[0]
    search_results = search(REBATE_COLLECTION, query_vector, top_k=30)

    documents = {}
    for r in search_results:
        if "chunk_id" in r.payload:
            metadata = get_metadata(r.payload["chunk_id"])
            if metadata and "content" in metadata and "source" in metadata:
                doc_name = metadata["source"]
                documents.setdefault(doc_name, []).append(metadata["content"])

    if not documents:
        return []

    extracted_data = []
    for doc_name, chunks in documents.items():
        context = "\n---\n".join(chunks)

        # 💡 Dynamic prompt for generalizable extraction
        prompt = f"""
You are a contracts and purchase-order analyst.
Your job is to extract clear, structured supplier rebate and penalty information from the given text.

You will receive unstructured text from a purchase order or contract.

---

### 🎯 Your Objectives

1. **Supplier Name**
   - Identify the supplier, vendor, or company name.

2. **Discount / Rebate Clause**
   - Detect *any* condition that gives a financial benefit for early or on-time payment.
   - Examples:
     - “2% discount if paid within 10 days”
     - “4% rebate for early settlement”
     - “payment before due date shall reduce total by 2%”
   - Extract both:
     - A **short, plain-English clause**
     - The **numeric discount percentage** (like “2%”)
   - If no discount is present, return `null` for both fields.

3. **Penalty Clause**
   - Detect *any* clause that describes a financial penalty, including:
     - **Late payment** penalties
     - **Late delivery** or **liquidated damages**
     - **Service delay** penalties
   - Recognize terms such as “penalty”, “deduction”, “liquidated damages”, “charge”, “interest”, “fee”.
   - Extract both:
     - A **short, plain-English clause**
     - The **numeric penalty percentage or rate**
   - If no penalty appears, return `null` for both.

4. **Contextual Understanding**
   - Reason semantically, not just by keywords.
   - Examples:
     - “A penalty of 1.5% charged per month for late payment” → penalty 1.5%
     - “The deduction will be 0.5% of the value of delayed items for each week of delay” → penalty 0.5%
     - “There will be a discount of 2% if paid before due date” → discount 2%
   - Capture meaning faithfully, even if not explicitly labeled “penalty” or “discount”.

---

### 🧩 Output Schema

Return **only** valid JSON in this exact structure:

{{
  "supplier_name": "<exact supplier name or null>",
  "discount_clause": "<short clear clause or null>",
  "discount": "<numeric value like '2%' or null>",
  "penalty_clause": "<short clear clause or null>",
  "penalty": "<numeric value like '0.5%' or null>"
}}

Rules:
- Return *only JSON* — no explanations or text outside the object.
- Keep clauses concise and in plain English.
- Normalize percentages (e.g., “0.5%”, not “0.5 percent”).
- Include both discount and penalty if both exist.

---

### 🧠 Examples

Example 1:
Input:
Supplier: Gulf Tech Solutions LLC
Clause: "A discount of 7% shall be applied if payment is made before the due date."
→ {{
  "supplier_name": "Gulf Tech Solutions LLC",
  "discount_clause": "7% discount if paid before due date",
  "discount": "7%",
  "penalty_clause": null,
  "penalty": null
}}

Example 2:
Vendor: Arabian Construction Co.
Clause: "There will be a discount of 2% if paid before Due date. A penalty of 1.5% per month applies for late payments."
→ {{
  "supplier_name": "Arabian Construction Co.",
  "discount_clause": "2% discount if paid before due date",
  "discount": "2%",
  "penalty_clause": "1.5% penalty per month for late payment",
  "penalty": "1.5%"
}}

Example 3:
Vendor: Emirates Logistics FZC
Clause: "The Buyer is entitled to deduct liquidated damages at 0.5% of the delayed items' value per week of delay."
→ {{
  "supplier_name": "Emirates Logistics FZC",
  "discount_clause": null,
  "discount": null,
  "penalty_clause": "0.5% penalty per week of delay for late delivery",
  "penalty": "0.5%"
}}

---

Now analyze the following document and extract the structured data:

---
{context}
---
Return **only** the JSON object.
"""

        llm_response = call_vllm(prompt)

        try:
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_string = llm_response[json_start:json_end]
                extracted = json.loads(json_string)
                extracted["document_name"] = doc_name
                extracted_data.append(extracted)
        except json.JSONDecodeError:
            continue

    return extracted_data

def extract_and_dump_rebates() -> list[dict]:
    """
    Fetches rebate data from Qdrant, dumps it into a JSON file, and returns it.
    """
    print("🔍 Fetching all company rebate and penalty details from Qdrant...")

    # Run the extraction
    rebates = query_rebate_collection("get all company rebate")

    if not rebates:
        print("⚠️ No rebate information found.")
        return []

    # Define JSON output file
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "rebate_output.json")

    # Dump to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(rebates, f, indent=2, ensure_ascii=False)

    print(f"✅ Extracted {len(rebates)} rebate entries saved to {output_file}")
    return rebates


# Optional manual test
if __name__ == '__main__':
    extract_and_dump_rebates()

'''

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Fetch rebate information from Qdrant and dump to JSON.")
    parser.add_argument("query", type=str, nargs="?", default="get all company rebate",
                        help="The query to search for rebates.")
    args = parser.parse_args()

    # 🔍 Extract rebates from Qdrant
    rebates = query_rebate_collection(args.query)
    print(json.dumps(rebates, indent=2))

    # 💾 Define dump file path
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "rebate_output.json")

    # 🧾 Save to JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(rebates, f, indent=2, ensure_ascii=False)

    print(f"✅ Extracted {len(rebates)} rebate entries saved to {output_file}")

'''
