import pandas as pd
from datetime import datetime, timedelta


def generate_due_tables():
    """
    Loads AR/AP CSVs, parses dates/amounts and returns:
      - AR_Due: not-paid AR invoices due within next 15 days (sorted earliest first)
      - AP_Due: not-paid AP invoices due within next 15 days (sorted earliest first)
      - AR_df: full AR dataframe (cleaned)
      - AP_df: full AP dataframe (cleaned)
    """
    today = datetime.now()

    # Load AR and AP
    ar_df = pd.read_csv("/home/ubuntu/cfo_dashboard/data/AR_Invoice.csv")
    ap_df = pd.read_csv("/home/ubuntu/cfo_dashboard/data/AP_Invoice.csv")

    # --- Normalize column names (strip spaces) ---
    ar_df.columns = [c.strip() for c in ar_df.columns]
    ap_df.columns = [c.strip() for c in ap_df.columns]

    # Convert date columns robustly
    ar_df["Due Date"] = pd.to_datetime(ar_df.get("Due Date"), errors="coerce")
    ar_df["Invoice Date"] = pd.to_datetime(ar_df.get("Invoice Date"), errors="coerce")
    ar_df["Paid Date"] = pd.to_datetime(ar_df.get("Paid Date"), errors="coerce")

    ap_df["Due Date"] = pd.to_datetime(ap_df.get("Due Date"), errors="coerce")
    ap_df["Invoice Date"] = pd.to_datetime(ap_df.get("Invoice Date"), errors="coerce")
    ap_df["Paid Date"] = pd.to_datetime(ap_df.get("Paid Date"), errors="coerce")

    # Ensure Amount column is numeric
    if "Amount (AED)" in ar_df.columns:
        ar_df["Amount (AED)"] = pd.to_numeric(
            ar_df["Amount (AED)"], errors="coerce"
        ).fillna(0)
    if "Amount (AED)" in ap_df.columns:
        ap_df["Amount (AED)"] = pd.to_numeric(
            ap_df["Amount (AED)"], errors="coerce"
        ).fillna(0)

    # --- AR Due upcoming (not paid & due within next 15 days) ---
    ar_pending = ar_df[
        (ar_df["Payment Status"].astype(str).str.lower() == "not paid")
        & (ar_df["Due Date"].notnull())
        & (ar_df["Due Date"] > today)
        & (ar_df["Due Date"] <= (today + timedelta(days=15)))
    ].copy()
    ar_pending["Days Remaining"] = (ar_pending["Due Date"] - today).dt.days
    top_4_ar = ar_pending.nsmallest(8, "Due Date")

    # --- AP Due upcoming (not paid & due within next 15 days) ---
    ap_pending = ap_df[
        (ap_df["Payment Status"].astype(str).str.lower() == "not paid")
        & (ap_df["Due Date"].notnull())
        & (ap_df["Due Date"] > today)
        & (ap_df["Due Date"] <= (today + timedelta(days=15)))
    ].copy()
    ap_pending["Days Remaining"] = (ap_pending["Due Date"] - today).dt.days
    top_4_ap = ap_pending.nsmallest(8, "Due Date")

    return {"AR_Due": top_4_ar, "AP_Due": top_4_ap, "AR_df": ar_df, "AP_df": ap_df}


def get_correct_time_payers(ar_df, top_n=3):
    """Find top customers who consistently pay on/before due date."""
    ar_df = ar_df.copy()
    ar_df["Paid Date"] = pd.to_datetime(ar_df.get("Paid Date"), errors="coerce")
    ar_df["Due Date"] = pd.to_datetime(ar_df.get("Due Date"), errors="coerce")

    # Consider only rows that have a Paid Date to compute on-time ratio
    ar_with_paid = ar_df[ar_df["Paid Date"].notnull()].copy()
    if ar_with_paid.empty:
        return pd.DataFrame(columns=["Customer Name", "OnTime"])

    ar_with_paid["OnTime"] = ar_with_paid["Paid Date"] <= ar_with_paid["Due Date"]
    payer_stats = ar_with_paid.groupby("Customer Name")["OnTime"].mean().reset_index()
    payer_stats = payer_stats.rename(columns={"OnTime": "OnTimeRatio"})
    top_payers = payer_stats.sort_values("OnTimeRatio", ascending=False).head(top_n)
    return top_payers


def get_top_ar_overdue(ar_df, top_n=3):
    """Find top customers with overdue payments (largest overdue days)."""
    today = datetime.now()
    ar_df = ar_df.copy()
    ar_df["Due Date"] = pd.to_datetime(ar_df.get("Due Date"), errors="coerce")

    ar_overdue = ar_df[
        (ar_df["Payment Status"].astype(str).str.lower() == "not paid")
        & (ar_df["Due Date"].notnull())
        & (ar_df["Due Date"] < today)
    ].copy()

    if not ar_overdue.empty:
        ar_overdue["Overdue Days"] = (today - ar_overdue["Due Date"]).dt.days
        top_overdue = ar_overdue.nlargest(top_n, "Overdue Days")
    else:
        top_overdue = pd.DataFrame()
    return top_overdue


def get_top_ap_overdue(ap_df, top_n=3):
    """Find top suppliers with overdue payments (largest overdue days)."""
    today = datetime.now()
    ap_df = ap_df.copy()
    ap_df["Due Date"] = pd.to_datetime(ap_df.get("Due Date"), errors="coerce")

    ap_overdue = ap_df[
        (ap_df["Payment Status"].astype(str).str.lower() == "not paid")
        & (ap_df["Due Date"].notnull())
        & (ap_df["Due Date"] < today)
    ].copy()

    if not ap_overdue.empty:
        ap_overdue["Overdue Days"] = (today - ap_overdue["Due Date"]).dt.days
        top_overdue = ap_overdue.nlargest(top_n, "Overdue Days")
    else:
        top_overdue = pd.DataFrame()
    return top_overdue


def get_AR_risk_data(ar_df):
    """
    Categorizes AR invoices by payment delay risk.
    Returns:
      - risk_distribution: DataFrame with Risk / Count
      - high_risk_invoices: DataFrame of high risk invoices (Not paid & overdue)
      - high_risk_count, high_risk_total
    """
    today = datetime.now()
    ar = ar_df.copy()
    ar["Due Date"] = pd.to_datetime(ar.get("Due Date"), errors="coerce")
    ar["Amount (AED)"] = pd.to_numeric(ar.get("Amount (AED)"), errors="coerce").fillna(
        0
    )
    ar["Payment Status"] = ar["Payment Status"].astype(str).str.lower()

    # Define risk for NOT PAID invoices only
    def compute_risk(row):
        status = row["Payment Status"]
        due = row["Due Date"]
        if status == "not paid" and pd.notnull(due):
            days = (today - due).days
            if days > 0:
                return "High"  # overdue
            elif 0 >= days > -15:
                return "Medium"  # due in next 15 days
            else:
                return "Low"  # due far in future
        else:
            return "Low"  # paid or missing due date treated as low risk

    ar["Risk"] = ar.apply(compute_risk, axis=1)

    # Build risk distribution making sure all categories present
    risk_counts = (
        ar["Risk"]
        .value_counts()
        .reindex(["High", "Medium", "Low"], fill_value=0)
        .reset_index()
    )
    risk_counts.columns = ["Risk", "Count"]

    AR_high_risk_invoices = ar[ar["Risk"] == "High"].copy()
    AR_high_risk_count = int(len(AR_high_risk_invoices))
    AR_high_risk_total = float(AR_high_risk_invoices["Amount (AED)"].sum())

    return {
        "risk_distribution": risk_counts,
        "high_risk_invoices": AR_high_risk_invoices,
        "high_risk_count": AR_high_risk_count,
        "high_risk_total": AR_high_risk_total,
    }


def get_AP_risk_data(ap_df):
    """
    Categorizes AP invoices by payment delay risk.
    Returns same structure as get_AR_risk_data.
    """
    today = datetime.now()
    ap = ap_df.copy()
    ap["Due Date"] = pd.to_datetime(ap.get("Due Date"), errors="coerce")
    ap["Amount (AED)"] = pd.to_numeric(ap.get("Amount (AED)"), errors="coerce").fillna(
        0
    )
    ap["Payment Status"] = ap["Payment Status"].astype(str).str.lower()

    def compute_risk(row):
        status = row["Payment Status"]
        due = row["Due Date"]
        if status == "not paid" and pd.notnull(due):
            days = (today - due).days
            if days > 0:
                return "High"  # overdue
            elif 0 >= days > -15:
                return "Medium"  # due in next 15 days
            else:
                return "Low"  # due far in future
        else:
            return "Low"  # paid or missing due date treated as low risk

    ap["Risk"] = ap.apply(compute_risk, axis=1)

    risk_counts = (
        ap["Risk"]
        .value_counts()
        .reindex(["High", "Medium", "Low"], fill_value=0)
        .reset_index()
    )
    risk_counts.columns = ["Risk", "Count"]

    AP_high_risk_invoices = ap[ap["Risk"] == "High"].copy()
    AP_high_risk_count = int(len(AP_high_risk_invoices))
    AP_high_risk_total = float(AP_high_risk_invoices["Amount (AED)"].sum())

    return {
        "risk_distribution": risk_counts,
        "high_risk_invoices": AP_high_risk_invoices,
        "high_risk_count": AP_high_risk_count,
        "high_risk_total": AP_high_risk_total,
    }


def get_invoice_summary(ar_df, ap_df):
    """Calculates total amounts for AR and AP."""
    ar = ar_df.copy()
    ap = ap_df.copy()

    ar_total = pd.to_numeric(ar.get("Amount (AED)"), errors="coerce").fillna(0).sum()
    ap_total = pd.to_numeric(ap.get("Amount (AED)"), errors="coerce").fillna(0).sum()

    summary_df = pd.DataFrame(
        {
            "Type": ["Account Receivable", "Account Payable"],
            "Total Amount (AED)": [ar_total, ap_total],
        }
    )

    return {"ar_total": ar_total, "ap_total": ap_total, "summary_df": summary_df}


def view_risk_invoices(high_risk_invoices):
    """
    Returns a formatted dataframe of high-risk invoices for display in Streamlit.
    Shows Invoice No., (Customer/Supplier Name), Service Description, Amount (AED), Due Date, Overdue Days
    """
    if high_risk_invoices is None or high_risk_invoices.empty:
        return pd.DataFrame()

    df = high_risk_invoices.copy()

    # Prefer Customer Name or Supplier Name
    if "Customer Name" in df.columns:
        name_col = "Customer Name"
    elif "Supplier Name" in df.columns:
        name_col = "Supplier Name"
    else:
        name_col = None

    display_columns = ["Invoice No."]
    if name_col:
        display_columns.append(name_col)
    display_columns += ["Service Description", "Amount (AED)", "Due Date"]

    # Add Overdue Days if available
    if "Overdue Days" in df.columns:
        display_columns.append("Overdue Days")
    else:
        # compute Overdue Days if Due Date present
        today = datetime.now()
        if "Due Date" in df.columns:
            df["Overdue Days"] = (
                today - pd.to_datetime(df["Due Date"], errors="coerce")
            ).dt.days

            display_columns.append("Overdue Days")

    # Format Due Date and Amount for display
    df["Due Date"] = pd.to_datetime(df.get("Due Date"), errors="coerce").dt.date
    df["Amount (AED)"] = (
        pd.to_numeric(df.get("Amount (AED)"), errors="coerce").fillna(0).round(2)
    )

    # Ensure selected columns exist
    display_columns = [c for c in display_columns if c in df.columns]

    return df[display_columns].reset_index(drop=True)


if __name__ == "__main__":
    result = generate_due_tables()
    print("### Accounts Receivable Upcoming Due ###")
    print(result["AR_Due"])
    print("### Accounts Payable Upcoming Due ###")
    print(result["AP_Due"])
    top_payers = get_correct_time_payers(result["AR_df"])
    print("\n--- Top Correct-Time Payers (Opportunities) ---")
    print(top_payers)
