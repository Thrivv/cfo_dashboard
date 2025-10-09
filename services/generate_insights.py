import json
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.due_tables import (
    generate_due_tables,
    get_correct_time_payers,
    get_top_ap_overdue,
    get_top_ar_overdue,
)
from utils.pipeline import query_rag


def generate_insights():
    # Get AR/AP tables and AR_df
    due_data = generate_due_tables()
    due_data["AR_Due"]
    due_data["AP_Due"]
    ar_df = due_data["AR_df"]
    ap_df = due_data["AP_df"]

    # Get top on-time payers
    top_payers = get_correct_time_payers(ar_df)

    # Get top overdue invoices for warnings
    top_ar_overdue = get_top_ar_overdue(ar_df, top_n=2)
    top_ap_overdue = get_top_ap_overdue(ap_df, top_n=2)

    # --- Warnings Generation ---
    ar_warning_query = f"""
Based on these overdue AR invoices:
{top_ar_overdue}

Generate exactly 2 AR warnings, each max 3 lines.
Include customer, invoice number, overdue days, Article reference, and why it matters.
"""
    ar_warnings = query_rag(ar_warning_query, template_name="ar_warning_summary")

    ap_warning_query = f"""
Based on these overdue AP invoices:
{top_ap_overdue}

Generate exactly 2 AP warnings, each max 3 lines.
Include supplier, invoice number, overdue days, PO T&C clause/regulation, and why it matters.
"""
    ap_warnings = query_rag(ap_warning_query, template_name="ap_warning_summary")

    # --- Opportunities Generation ---
    (
        f"Top correct-time paying customers:\n{top_payers.to_string(index=False)}"
    )
    ar_opportunity_query = "Generate up to 2 AR opportunities, each max 3 lines, with regulation references."
    ar_opps = query_rag(ar_opportunity_query, template_name="ar_opportunity_summary")

    ap_opportunity_query = (
        "Generate up to 2 AP opportunities, each max 3 lines, with PO T&C references."
    )
    ap_opps = query_rag(ap_opportunity_query, template_name="ap_opportunity_summary")

    final_output = {
        "warnings": {"AR": ar_warnings, "AP": ap_warnings},
        "opportunities": {"AR": ar_opps, "AP": ap_opps},
    }

    return final_output


if __name__ == "__main__":
    insights = generate_insights()
    print(json.dumps(insights, indent=2))
