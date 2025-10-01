import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))
from pipeline import query_rag
from due_tables import generate_due_tables, get_correct_time_payers

def generate_insights():
    # Get AR/AP tables and AR_df
    due_data = generate_due_tables()
    ar_table = due_data["AR_Due"]
    ap_table = due_data["AP_Due"]
    ar_df = due_data["AR_df"]
    ap_df = due_data["AP_df"]

    # Get top on-time payers
    top_payers = get_correct_time_payers(ar_df)

    # --- Warnings Generation ---
    ar_warning_query = f"Based on the following overdue AR invoices:\n{ar_table}\nGenerate multiple one-line AR warnings comparing with Regulations (each line one warning)."
    ar_warnings = query_rag(ar_warning_query, template_name="ar_warning_summary")

    ap_warning_query = f"Based on the following AP nearing-due invoices:\n{ap_table}\nGenerate multiple one-line AP warnings comparing with PO T&C (each line one warning)."
    ap_warnings = query_rag(ap_warning_query, template_name="ap_warning_summary")

    # --- Opportunities Generation ---
    ar_opp_context = f"Top correct-time paying customers:\n{top_payers.to_string(index=False)}"
    ar_opportunity_query = f"Generate multiple one-line AR opportunities using above data and Regulations."
    ar_opps = query_rag(ar_opportunity_query, template_name="ar_opportunity_summary")

    ap_opp_context = f"AP invoices nearing due:\n{ap_table}\nPO T&C document data available."
    ap_opportunity_query = "Generate multiple one-line AP opportunities highlighting early payment benefits based on PO T&C."
    ap_opps = query_rag(ap_opportunity_query, template_name="ap_opportunity_summary")

    final_output = {
        "warnings": {
            "AR": ar_warnings,
            "AP": ap_warnings
        },
        "opportunities": {
            "AR": ar_opps,
            "AP": ap_opps
        }
    }

    return final_output

if __name__ == "__main__":
    generate_insights()