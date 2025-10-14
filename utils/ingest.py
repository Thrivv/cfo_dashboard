"""Data ingestion utilities for the CFO dashboard."""

import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pipeline import ingest_document

if __name__ == "__main__":
    # Ingest AP Invoice
    ap_invoice_path = "data/AP_Invoice.csv"
    ap_metadata = {"doc_name": "AP_invoice.csv", "source_type": "finance_AP"}
    ingest_document(ap_invoice_path, ap_metadata)
    print("✅ AP Invoice ingested")

    # Ingest AR Invoice
    ar_invoice_path = "data/AR_Invoice.csv"
    ar_metadata = {"doc_name": "AR_invoice.csv", "source_type": "finance_AR"}
    ingest_document(ar_invoice_path, ar_metadata)
    print("✅ AR Invoice ingested")

    # Ingest Regulations PDF
    regulations_path = "data/RPSR_RPSCSR_UAE.pdf"
    regulations_metadata = {"doc_name": "RPS_CSR_ENG.pdf", "source_type": "regulation"}
    ingest_document(regulations_path, regulations_metadata)
    print("✅ Regulations PDF ingested")

    # Ingest PO T&C PDF
    po_tc_path = "data/PO_T&C.pdf"
    po_tc_metadata = {"doc_name": "PO_T&C.pdf", "source_type": "terms_and_conditions"}
    ingest_document(po_tc_path, po_tc_metadata)
    print("✅ PO T&C PDF ingested")
