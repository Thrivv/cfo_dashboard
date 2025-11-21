"""RAG pipeline utilities for document processing — Enhanced for CFO dashboard."""

from datetime import datetime, timedelta
import json
import os
import re
import pandas as pd
from prompts.rag_chatbot import RAG_CHATBOT_PROMPT, DOC_CHATBOT_PROMPT

from utils.embedding import embed_texts
from utils.llm_client import call_vllm
from utils.config import (
    #AR_INVOICE_COLLECTION,
    #AP_INVOICE_COLLECTION,
    PO_TC_COLLECTION,
    REGULATIONS_COLLECTION,
    #REBATE_COLLECTION,
)

# Local utility imports
from utils.redis_client import get_metadata
from utils.rerank import rerank
from utils.vectorstore_qdrant import search
from utils.data_refresh import check_and_update_data

# Define column sets for dynamic table generation
BASE_COLS = ['Invoice No.', 'Invoice Date', 'Due Date', 'Service Description', 'Amount (AED)', 'Payment Status', 'VAT TRN', 'VAT %', 'Paid Date', 'Status']
AP_COLS_SUPPLIER = ['Supplier Name']
AR_COLS_CUSTOMER = ['Customer Name']
DISCOUNT_COLS = ['Discount', 'Discount Note', 'Final Amount with Discount']
PENALTY_COLS = ['Penalty', 'Penalty Note', 'Final Amount with Penalty']

# Upcoming: Base + Supplier + Discount
AP_UPCOMING_COLS = BASE_COLS[:3] + AP_COLS_SUPPLIER + BASE_COLS[3:6] + DISCOUNT_COLS + PENALTY_COLS + BASE_COLS[6:]
# Overdue: Base + Supplier + Penalty
AP_OVERDUE_COLS = BASE_COLS[:3] + AP_COLS_SUPPLIER + BASE_COLS[3:6] + PENALTY_COLS + BASE_COLS[6:]
# Default/Paid: All columns
AP_DEFAULT_COLS = BASE_COLS[:3] + AP_COLS_SUPPLIER + BASE_COLS[3:6] + DISCOUNT_COLS + PENALTY_COLS + BASE_COLS[6:]

# AR columns don't have discount/penalty, so they are simpler
AR_COLS = BASE_COLS[:3] + AR_COLS_CUSTOMER + BASE_COLS[3:]

# ---------------------------------------------------------------------------
# Main Unified RAG Query Pipeline
# ---------------------------------------------------------------------------


def query_rag(query: str, template_name: str = "qa_template", top_k: int = 20):
    """
    Unified RAG pipeline with invoice logic, semantic retrieval,
    reranking, and regulatory/PO context composition.

    This version uses a single unified routing + chained filtering pipeline
    (routing by AR/AP/both, then sequential filters for paid/unpaid -> status ->
    customer/supplier name -> discount/penalty), while preserving all original features.
    """
    print(f"\n🔍 Running RAG Query: {query}\n")

    # Step 1 — Ensure data freshness
    check_and_update_data()

    # Step 2 — Vector Search across all collections
    q_vec = embed_texts([query])[0]
    collections_map = {
        "po": PO_TC_COLLECTION,
        "reg": REGULATIONS_COLLECTION,
        #"ar": AR_INVOICE_COLLECTION,
        #"ap": AP_INVOICE_COLLECTION,
        #"rebate": REBATE_COLLECTION,
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

    strict_keywords = {'ar', 'ap'}
    loose_keywords = {'invoice', 'customer', 'supplier','payable','receivable', 'vendor', 'due', 'overdue','upcoming','unpaid', 'paid', 'accounts payable', 'accounts receivable', "payment status", 'discount', 'penalty', 'rebate'}
    rebate_summary_keywords = ['rebate summary', 'rebate rule summary','rebate rules summary', 'rebate details', 'rebate information', "rebate condition for", "all reabte policy", "all rebate policies"] # Moved this definition up
    
    q_lower = query.lower()

    if any(k in q_lower for k in rebate_summary_keywords):
        print("🎯 Detected Rebate Summary Query. Routing to JSON file.")
        try:
            with open("data/rebate_output.json", "r") as f:
                rebate_data = json.load(f)
            rebate_context = json.dumps(rebate_data, indent=2)
            
            prompt = f"""You are a financial assistant. Answer the following user query based *only* on the provided JSON data.

**JSON Data:**
```json
{rebate_context}
```

**User Query:**
{query}

**Answer:**
"""
            print("🧠 Sending rebate summary query to LLM...")
            response = call_vllm(prompt, max_tokens=1024)
            print("✅ Response received.\n")
            return response
            
        except Exception as e:
            print(f"⚠️ Error loading rebate_output.json: {e}")
            return "I am sorry, but I encountered an error trying to access the rebate summary data."
        

    is_invoice_query = any(re.search(r'\b' + re.escape(k.strip()) + r'\b', q_lower) for k in strict_keywords) or \
                       any(k.strip() in q_lower for k in loose_keywords)
    
    is_document_only_query = any(k in q_lower for k in ['regulation', 'regulations', 'purchase order', 'purchase orders', 'po terms', 'po term', "card scheme", "retail payment", "card scheme regulation", "retail payment system", 'terms of purchase order', 'terms of purchase orders', "company policy", "compliance", "regulatory", "regulator"])

    if is_document_only_query and not is_invoice_query:
        # ROUTE 1: Document-only query for regulations, POs, etc.
        print("🎯 Detected Document-Only Query. Routing to document context.")
        
        doc_context_texts = docs_by_collection.get("reg", []) + docs_by_collection.get("po", [])
        
        if not doc_context_texts:
            print("⚠️ No document context found for this query.")
            return "I couldn't find any relevant documents to answer your question. Please try a different query."

        reranked_doc_context = rerank(query, doc_context_texts)
        final_context = "\n\n".join(reranked_doc_context[:2])

        template = DOC_CHATBOT_PROMPT
        
        prompt = template.format(
            context=final_context,
            query=query
        )
        
        print("🧠 Sending document-focused query to LLM...")
        response = call_vllm(prompt, max_tokens=1024)
        print("✅ Response received.\n")
        return response

    # ROUTE 2: General query involving invoices.
    print("🎯 Detected General/Invoice Query. Routing to full context.")

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

    # Keep original column-selection defaults
    ap_cols_to_use = AP_DEFAULT_COLS
    ar_cols_to_use = AR_COLS

    # Ensure 'Status' and 'Payment Status' columns exist and normalize text
    for df in [ar_df, ap_df]:
        if "Status" in df.columns:
            df["Status"] = df["Status"].astype(str).str.strip().str.lower()
        if "Payment Status" in df.columns:
            df["Payment Status"] = df["Payment Status"].astype(str).str.strip().str.lower()

    # ---------------------------
    # Step 7 (UNIFIED) — Routing + Chained Filtering Pipeline (Option B)
    # ---------------------------

    # Helper: safe apply a boolean mask; if filtered empty, return original (to avoid discarding earlier results)
    def safe_filter_df(original_df, filtered_df):
        """Return filtered_df if it has rows, otherwise return original_df."""
        if filtered_df is None:
            return original_df
        return filtered_df if not filtered_df.empty else original_df

    # Make working copies
    source_ar_df = ar_df.copy()
    source_ap_df = ap_df.copy()

    # Start with both by default
    working_ar = source_ar_df.copy()
    working_ap = source_ap_df.copy()

    # Determine initial routing based on explicit keywords (preserve original routing behavior)
    # If user mentions phrases indicating "both", keep both; else restrict to AP or AR if mentioned.
    if any(k in q_lower for k in ["both payable and receivable", "customer and supplier", "all invoices", "all payments", "all receivables", "all payables", "both ar and ap", "both accounts receivable and accounts payable"]):
        print("Routing: both AR and AP (explicit 'both' detected).")
        # keep both
    elif any(k in q_lower for k in ["accounts payable", "accounts_payable", " ap ", "supplier", "vendor", "payable", "payables"]):
        print("Routing: restrict to AP only (supplier/vendor detected).")
        working_ar = pd.DataFrame(columns=working_ar.columns)  # empty AR
    elif any(k in q_lower for k in ["accounts receivable", "accounts_receivable", " ar ", "customer", "receivable", "receivables"]):
        print("Routing: restrict to AR only (customer/receivable detected).")
        working_ap = pd.DataFrame(columns=working_ap.columns)  # empty AP
    else:
        print("Routing: default to both AR and AP.")

    # We'll record which filters applied (for debugging/logging)
    applied_filters = []

    # ------- 1) Paid / Unpaid filter -------
    if any(k in q_lower for k in ["unpaid", "not paid", "pending", " due ", "to be paid", "un-paid"]):
        applied_filters.append("payment_status:not_paid")
        try:
            if "Payment Status" in working_ar.columns:
                filtered = working_ar[working_ar["Payment Status"] == "not paid"]
                working_ar = safe_filter_df(working_ar, filtered)
            if "Payment Status" in working_ap.columns:
                filtered = working_ap[working_ap["Payment Status"] == "not paid"]
                working_ap = safe_filter_df(working_ap, filtered)
            print("Applied filter: unpaid / not paid")
        except Exception as e:
            print(f"⚠️ Skipped unpaid filter due to: {e}")

    elif "paid" in q_lower:
        applied_filters.append("payment_status:paid")
        try:
            if "Status" in working_ar.columns:
                filtered = working_ar[working_ar["Status"].str.contains("paid", case=False, na=False)]
                working_ar = safe_filter_df(working_ar, filtered)
            if "Status" in working_ap.columns:
                filtered = working_ap[working_ap["Status"].str.contains("paid", case=False, na=False)]
                working_ap = safe_filter_df(working_ap, filtered)
            print("Applied filter: paid")
        except Exception as e:
            print(f"⚠️ Skipped paid filter due to: {e}")

    # ------- 2) Status filter (overdue / upcoming / future) -------
    # We'll set AP column selection if upcoming/overdue matched
    status_ap_cols_override = None

    if any(k in q_lower for k in ["overdue", "late", "crossed", "past due", "due date passed", "payments overdue", "invoices overdue"]):
        applied_filters.append("status:overdue")
        try:
            if "Status" in working_ar.columns:
                filtered = working_ar[working_ar["Status"].str.contains("overdue", case=False, na=False)]
                working_ar = safe_filter_df(working_ar, filtered)
            if "Status" in working_ap.columns:
                filtered = working_ap[working_ap["Status"].str.contains("overdue", case=False, na=False)]
                working_ap = safe_filter_df(working_ap, filtered)
                status_ap_cols_override = AP_OVERDUE_COLS
            print("Applied filter: overdue")
        except Exception as e:
            print(f"⚠️ Skipped overdue filter due to: {e}")

    elif any(k in q_lower for k in ["upcoming", "this week", "next 7 days", "payments to make this week", "due this week", "due in the next 7 days", "due soon"]):
        applied_filters.append("status:upcoming")
        try:
            if "Status" in working_ar.columns:
                filtered = working_ar[working_ar["Status"].str.contains("upcoming", case=False, na=False)]
                working_ar = safe_filter_df(working_ar, filtered)
            if "Status" in working_ap.columns:
                filtered = working_ap[working_ap["Status"].str.contains("upcoming", case=False, na=False)]
                working_ap = safe_filter_df(working_ap, filtered)
                status_ap_cols_override = AP_UPCOMING_COLS
            print("Applied filter: upcoming")
        except Exception as e:
            print(f"⚠️ Skipped upcoming filter due to: {e}")

    elif any(k in q_lower for k in ["future", "next week", "after this week", "payments to make next week", "due next week", "due after this week"]):
        applied_filters.append("status:future")
        try:
            if "Status" in working_ar.columns:
                filtered = working_ar[working_ar["Status"].str.contains("future", case=False, na=False)]
                working_ar = safe_filter_df(working_ar, filtered)
            if "Status" in working_ap.columns:
                filtered = working_ap[working_ap["Status"].str.contains("future", case=False, na=False)]
                working_ap = safe_filter_df(working_ap, filtered)
                status_ap_cols_override = AP_UPCOMING_COLS
            print("Applied filter: future")
        except Exception as e:
            print(f"⚠️ Skipped future filter due to: {e}")

    
    # if an AP column override was set, use it
    if status_ap_cols_override:
        ap_cols_to_use = status_ap_cols_override

    # ------- 3) Customer / Supplier name filter -------
    # We'll try to detect a name mentioned in the query by looking at unique names in the working dataframes
    try:
        # gather candidate names from the current working sets (lowercased)
        candidate_customers = []
        candidate_suppliers = []

        if "Customer Name" in working_ar.columns and not working_ar.empty:
            candidate_customers = [str(x).strip().lower() for x in working_ar["Customer Name"].dropna().unique()]

        if "Supplier Name" in working_ap.columns and not working_ap.empty:
            candidate_suppliers = [str(x).strip().lower() for x in working_ap["Supplier Name"].dropna().unique()]

        # Find company names by checking if any meaningful words from the query appear in the candidate names
        stop_words = {'a', 'an', 'the', 'is', 'in', 'it', 'of', 'for', 'on', 'with', 'at', 'by', 'to', 'from', 'up', 'out', 'and', 'or', 'but', 'what', 'who', 'when', 'where', 'why', 'how', 'show', 'me', 'list', 'all', 'give', 'tell'}
        query_tokens = {word.strip(".,?!") for word in q_lower.split()}
        meaningful_query_words = {word for word in query_tokens if word not in stop_words and len(word) > 2}

        matched_customer_names = [
            name for name in candidate_customers if name and any(word in name for word in meaningful_query_words)
        ]
        matched_supplier_names = [
            name for name in candidate_suppliers if name and any(word in name for word in meaningful_query_words)
        ]

        # If user explicitly mentions a name which matches candidate list, apply the filter
        if matched_customer_names:
            applied_filters.append(f"customer_name:{matched_customer_names}")
            try:
                mask = working_ar["Customer Name"].astype(str).str.lower().isin(matched_customer_names)
                filtered = working_ar[mask]
                working_ar = safe_filter_df(working_ar, filtered)
                print(f"Applied filter: Customer Name match — {matched_customer_names}")
            except Exception as e:
                print(f"⚠️ Skipped Customer Name filter due to: {e}")

        if matched_supplier_names:
            applied_filters.append(f"supplier_name:{matched_supplier_names}")
            try:
                mask = working_ap["Supplier Name"].astype(str).str.lower().isin(matched_supplier_names)
                filtered = working_ap[mask]
                working_ap = safe_filter_df(working_ap, filtered)
                print(f"Applied filter: Supplier Name match — {matched_supplier_names}")
            except Exception as e:
                print(f"⚠️ Skipped Supplier Name filter due to: {e}")
    except Exception as e:
        print(f"⚠️ Name-matching step failed: {e}")

    # ------- 4) Discount / Penalty filter -------
    if any(k in q_lower for k in ["discount", "rebate", "early payment discount", "discounted"]):
        applied_filters.append("has_discount")
        try:
            if "Discount" in working_ar.columns:
                working_ar = working_ar[working_ar["Discount"].notna() & (working_ar["Discount"].astype(str).str.strip() != "")]
            else:
                working_ar = pd.DataFrame(columns=working_ar.columns)  # Empty it

            if "Discount" in working_ap.columns:
                working_ap = working_ap[working_ap["Discount"].notna() & (working_ap["Discount"].astype(str).str.strip() != "")]
            else:
                working_ap = pd.DataFrame(columns=working_ap.columns)
            print("Applied filter: discount/rebate")
        except Exception as e:
            print(f"⚠️ Skipped discount filter due to: {e}")

    if any(k in q_lower for k in ["penalty", "late fee", "late_fee", "penalised", "penalized", "penaltized", "penalty invoices", "late fee applied", "penalty suitable", "incur a penalty", "incur penalty"]):
        applied_filters.append("has_penalty")
        print("Filtering for penalty-related invoices...")
        try:
            if "Penalty" in working_ar.columns:
                ar_has_penalty = (
                    working_ar["Status"].str.contains("overdue", case=False, na=False) &
                    working_ar["Penalty"].notna()
                )
                working_ar = working_ar[ar_has_penalty]
            else:
                working_ar = pd.DataFrame(columns=working_ar.columns)

            if "Penalty" in working_ap.columns:
                ap_has_penalty = (
                    working_ap["Status"].str.contains("overdue", case=False, na=False) &
                    working_ap["Penalty"].notna()
                )
                working_ap = working_ap[ap_has_penalty]
            else:
                working_ap = pd.DataFrame(columns=working_ap.columns)
            
            ap_cols_to_use = AP_OVERDUE_COLS
            print(f"Penalty AR rows: {len(working_ar)}, Penalty AP rows: {len(working_ap)}")

        except Exception as e:
            print(f"⚠️ Skipped penalty filter due to: {e}")

    # ------- 5) Additional fallback date-based filters (optional but preserves original intent) -------
    # Preserve the ability to query "due this week" by date comparison if no explicit status column matched
    try:
        if any(k in q_lower for k in ["this week", "next 7 days", "due this week", "due in the next 7 days"]) and ("Due Date" in working_ap.columns or "Due Date" in working_ar.columns):
            applied_filters.append("date:next_7_days")
            start_date = today
            end_date = next_week
            if "Due Date" in working_ar.columns and not working_ar.empty:
                filtered = working_ar[(working_ar["Due Date"].dt.date >= start_date) & (working_ar["Due Date"].dt.date <= end_date)]
                working_ar = safe_filter_df(working_ar, filtered)
            if "Due Date" in working_ap.columns and not working_ap.empty:
                filtered = working_ap[(working_ap["Due Date"].dt.date >= start_date) & (working_ap["Due Date"].dt.date <= end_date)]
                working_ap = safe_filter_df(working_ap, filtered)
            print("Applied filter: due within next 7 days (date-based)")
    except Exception as e:
        print(f"⚠️ Skipped date-based filter due to: {e}")

    # DONE: unified filter chain applied. Log summary
    print(f"Filters applied in order: {applied_filters}")
    print(f"Post-filter AR rows: {len(working_ar)}, Post-filter AP rows: {len(working_ap)}")

    # Final filtered dfs
    ar_filtered = working_ar.copy()
    ap_filtered = working_ap.copy()

    # Ensure selected columns exist in the dataframe before selection
    ap_cols_exist = [col for col in ap_cols_to_use if col in ap_filtered.columns]
    ar_cols_exist = [col for col in ar_cols_to_use if col in ar_filtered.columns]
    
    ap_filtered = ap_filtered[ap_cols_exist]
    ar_filtered = ar_filtered[ar_cols_exist]

    # Step 8 — Prepare Markdown tables
    ap_csv = ap_filtered.to_markdown(index=False, missingval='-', numalign="left", stralign="left") if not ap_filtered.empty else ""
    ar_csv = ar_filtered.to_markdown(index=False, missingval='-', numalign="left", stralign="left") if not ar_filtered.empty else ""

    # Step 8 — Prepare CSV and document contexts
    def truncate(txt, max_len=6000):
        return txt[:max_len] + "..." if len(txt) > max_len else txt

    po_text = truncate(po_text)
    reg_text = truncate(reg_text)

    # Step 9 — Compose RAG context
    context = f"""
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

# ---------------------------------------------------------------------------
# Prompt Template Loader
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

def query_insights(query: str, data_context: str, template_name: str):
    """
    Lightweight query function for structured insight generation (warnings/opportunities)
    that bypasses full RAG context to prevent unwanted markdown or table formatting.
    """
    print(f"\n🔍 Running RAG Query: {query}\n")

    # Step 1 — Ensure data freshness
    check_and_update_data()
    q_lower = query.lower()

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