import pandas as pd
from datetime import datetime, timedelta

def generate_due_tables():
    today = datetime.now()

    # Load AR and AP
    ar_df = pd.read_csv("RAG/data/AR_Invoice.csv")
    ap_df = pd.read_csv("RAG/data/AP_Invoice.csv")

    # Convert dates
    ar_df["Due Date"] = pd.to_datetime(ar_df["Due Date"])
    ar_df["Paid Date"] = pd.to_datetime(ar_df["Paid Date"], errors='coerce')
    ap_df["Due Date"] = pd.to_datetime(ap_df["Due Date"])

    # --- AR Overdue ---
    ar_overdue = ar_df[ar_df["Payment Status"].str.lower() == "overdue"].copy()
    ar_overdue["Overdue Days"] = (today - ar_overdue["Due Date"]).dt.days
    top_4_ar = ar_overdue.nlargest(4, "Overdue Days")

    ar_table = "| Customer | Service | Amount Pending (AED) | Due Date | Overdue Days |\n|---|---|---|---|---|\n"
    for _, row in top_4_ar.iterrows():
        ar_table += f"| {row['Customer Name']} | {row['Service Description']} | {row['Amount (AED)']} | {row['Due Date'].strftime('%Y-%m-%d')} | {row['Overdue Days']} |\n"

    # --- AP Nearing Due ---
    ap_pending = ap_df[(ap_df["Payment Status"].str.lower() == "not paid") &
                       (ap_df["Due Date"] > today) &
                       (ap_df["Due Date"] <= today + timedelta(days=15))].copy()
    ap_pending["Days Remaining"] = (ap_pending["Due Date"] - today).dt.days
    top_4_ap = ap_pending.nsmallest(4, "Due Date")

    ap_table = "| Supplier | Amount to Pay (AED) | Due Date | Days Remaining |\n|---|---|---|---|\n"
    for _, row in top_4_ap.iterrows():
        ap_table += f"| {row['Supplier Name']} | {row['Amount (AED)']} | {row['Due Date'].strftime('%Y-%m-%d')} | {row['Days Remaining']} |\n"

    return {"AR_Due": ar_table, "AP_Due": ap_table, "AR_df": ar_df, "AP_df": ap_df}

def get_correct_time_payers(ar_df, top_n=3):
    """Find top customers who consistently pay on/before due date."""
    ar_df = ar_df.copy()
    ar_df["OnTime"] = (ar_df["Paid Date"] <= ar_df["Due Date"])
    payer_stats = ar_df.groupby("Customer Name")["OnTime"].mean().reset_index()
    top_payers = payer_stats.sort_values("OnTime", ascending=False).head(top_n)
    return top_payers

if __name__ == "__main__":
    result = generate_due_tables()
    print("### Accounts Receivable Overdue ###")
    print(result["AR_Due"])
    print("### Accounts Payable Nearing Due ###")
    print(result["AP_Due"])
    top_payers = get_correct_time_payers(result["AR_df"])
    print("\n--- Top Correct-Time Payers (Opportunities) ---")
    print(top_payers)
