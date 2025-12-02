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
from utils.pipeline import query_insights


def generate_insights():
    # Get AR/AP tables and AR_df
    due_data = generate_due_tables()
    due_data["AR_Due"]
    due_data["AP_Due"]
    ar_df = due_data["AR_df"]
    ap_df = due_data["AP_df"]

    # Get top on-time payers
    top_payers_ar = get_correct_time_payers(ar_df)

    # Get top overdue invoices for warnings
    top_ar_overdue = get_top_ar_overdue(ar_df, top_n=2)
    top_ap_overdue = get_top_ap_overdue(ap_df, top_n=2)

    # --- Warnings Generation ---
    ar_warnings = "No overdue AR invoices to generate warnings for."
    if not top_ar_overdue.empty:
        ar_cols = ['Invoice No.', 'Customer Name', 'Amount (AED)', 'Overdue Days', 'Service Description']
        # Ensure columns exist before selecting
        ar_cols_exist = [col for col in ar_cols if col in top_ar_overdue.columns]
        ar_context_df = top_ar_overdue[ar_cols_exist]
        ar_context_str = ar_context_df.to_string(index=False)
        ar_warning_query = "Generate warnings for the provided overdue AR invoices."
        ar_warnings = query_insights(ar_warning_query, ar_context_str, "ar_warning_summary")

    ap_warnings = "No overdue AP invoices to generate warnings for."
    if not top_ap_overdue.empty:
        ap_cols = ['Invoice No.', 'Supplier Name', 'Amount (AED)', 'Overdue Days', 'Service Description', 'Penalty', 'Penalty Note','Final Amount with Penalty']
        # Ensure columns exist before selecting
        ap_cols_exist = [col for col in ap_cols if col in top_ap_overdue.columns]
        ap_context_df = top_ap_overdue[ap_cols_exist]
        ap_context_str = ap_context_df.to_string(index=False)
        ap_warning_query = "Generate warnings for the provided overdue AP invoices."
        ap_warnings = query_insights(ap_warning_query, ap_context_str, "ap_warning_summary")

    # --- Opportunities Generation ---
    ar_opportunity_query = "Based on the following data of top on-time paying customers, generate up to 2 AR opportunities. Each opportunity must be based on a real invoice from the data. Do not invent any details like invoice numbers or amounts. Each opportunity should be a maximum of 3 lines."
    ar_opps = query_insights(ar_opportunity_query, top_payers_ar.to_string(index=False), "ar_opportunity_summary")

    ap_opportunity_query = "Generate up to 2 AP opportunities, each max 3 lines, with PO T&C or discount references."
    ap_opps = query_insights(ap_opportunity_query, ap_df.to_string(index=False), "ap_opportunity_summary")

    final_output = {
        "warnings": {"AR": ar_warnings, "AP": ap_warnings},
        "opportunities": {"AR": ar_opps, "AP": ap_opps},
    }

    return final_output


if __name__ == "__main__":
    insights = generate_insights()
    print(json.dumps(insights, indent=2))
