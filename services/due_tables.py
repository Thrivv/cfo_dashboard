import pandas as pd
from datetime import datetime, timedelta

def generate_due_tables():
    today = datetime.now()

    # Load AR and AP
    ar_df = pd.read_csv("/home/ubuntu/cfo_dashboard/data/AR_Invoice.csv")
    ap_df = pd.read_csv("/home/ubuntu/cfo_dashboard/data/AP_Invoice.csv")

    # Convert dates
    ar_df["Due Date"] = pd.to_datetime(ar_df["Due Date"])
    ar_df["Paid Date"] = pd.to_datetime(ar_df["Paid Date"], errors='coerce')
    ap_df["Due Date"] = pd.to_datetime(ap_df["Due Date"])

    # --- AR Overdue ---
    ar_overdue = ar_df[ar_df["Payment Status"].str.lower() == "overdue"].copy()
    ar_overdue["Overdue Days"] = (today - ar_overdue["Due Date"]).dt.days
    top_4_ar = ar_overdue.nlargest(5, "Overdue Days")

    # --- AP Nearing Due ---
    ap_pending = ap_df[(ap_df["Payment Status"].str.lower() == "not paid") &
                       (ap_df["Due Date"] > today) &
                       (ap_df["Due Date"] <= today + timedelta(days=15))].copy()
    ap_pending["Days Remaining"] = (ap_pending["Due Date"] - today).dt.days
    top_4_ap = ap_pending.nsmallest(5, "Due Date")

    return {"AR_Due": top_4_ar, "AP_Due": top_4_ap, "AR_df": ar_df, "AP_df": ap_df}

def get_correct_time_payers(ar_df, top_n=3):
    """Find top customers who consistently pay on/before due date."""
    ar_df = ar_df.copy()
    ar_df["OnTime"] = (ar_df["Paid Date"] <= ar_df["Due Date"])
    payer_stats = ar_df.groupby("Customer Name")["OnTime"].mean().reset_index()
    top_payers = payer_stats.sort_values("OnTime", ascending=False).head(top_n)
    return top_payers

def get_payment_risk_data(ar_df):
    """Categorizes AR invoices by payment delay risk."""
    today = datetime.now()
    ar_df['Overdue Days'] = (today - ar_df['Due Date']).dt.days

    def assign_risk(days):
        if days > 0:  # Overdue invoices are high risk
            return 'High'
        elif -15 < days <= 0:  # Due in the next 15 days are medium risk
            return 'Medium'
        else:  # All others are low risk
            return 'Low'

    ar_df['Risk'] = ar_df['Overdue Days'].apply(assign_risk)
    
    risk_counts = ar_df['Risk'].value_counts().reset_index()
    risk_counts.columns = ['Risk', 'Count']

    high_risk_invoices = ar_df[ar_df['Risk'] == 'High']
    high_risk_count = len(high_risk_invoices)
    high_risk_total = high_risk_invoices['Amount (AED)'].sum()

    return {
        "risk_distribution": risk_counts,
        "high_risk_invoices": high_risk_invoices,
        "high_risk_count": high_risk_count,
        "high_risk_total": high_risk_total
    }

def get_invoice_summary(ar_df, ap_df):
    """Calculates total amounts for AR and AP."""
    ar_total = ar_df['Amount (AED)'].sum()
    ap_total = ap_df['Amount (AED)'].sum()
    
    summary_df = pd.DataFrame({
        'Type': ['Account Receivable', 'Account Payable'],
        'Total Amount (AED)': [ar_total, ap_total]
    })
    
    return {
        "ar_total": ar_total,
        "ap_total": ap_total,
        "summary_df": summary_df
    }

def view_risk_invoices(high_risk_invoices):
    """Returns a dataframe of high-risk invoices for display."""
    return high_risk_invoices[['Invoice No.', 'Customer Name', 'Service Description', 'Amount (AED)', 'Due Date']]


if __name__ == "__main__":
    result = generate_due_tables()
    print("### Accounts Receivable Overdue ###")
    print(result["AR_Due"])
    print("### Accounts Payable Nearing Due ###")
    print(result["AP_Due"])
    top_payers = get_correct_time_payers(result["AR_df"])
    print("\n--- Top Correct-Time Payers (Opportunities) ---")
    print(top_payers)