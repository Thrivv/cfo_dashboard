"""Services for generating due tables and risk data."""

from datetime import datetime, timedelta

import pandas as pd


import pandas as pd
from datetime import timedelta

def generate_due_tables():
    """
    Loads AR/AP CSVs, cleans and filters them, and returns:
    - AR_Due: not-paid AR invoices due within next 15 days (selected columns only)
    - AP_Due: not-paid AP invoices due within next 15 days (selected columns only)
    - AR_df: full cleaned AR dataframe
    - AP_df: full cleaned AP dataframe
    """
    today = pd.to_datetime('today').normalize()

    # --- Load datasets ---
    ar_df = pd.read_csv("data/AR_Invoice.csv")
    ap_df = pd.read_csv("data/AP_Invoice.csv")

    # --- Normalize column names ---
    ar_df.columns = [c.strip() for c in ar_df.columns]
    ap_df.columns = [c.strip() for c in ap_df.columns]

    # --- Convert date columns ---
    for df in [ar_df, ap_df]:
        for col in ["Invoice Date", "Due Date", "Paid Date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    # --- Ensure Amount column is numeric ---
    for df in [ar_df, ap_df]:
        if "Amount (AED)" in df.columns:
            df["Amount (AED)"] = pd.to_numeric(df["Amount (AED)"], errors="coerce").fillna(0)

    # --- AR upcoming dues (within next 15 days & not paid) ---
    if "Payment Status" in ar_df.columns and "Due Date" in ar_df.columns:
        ar_due_filter = (
            (ar_df["Payment Status"].astype(str).str.lower() == "not paid")
            & (ar_df["Due Date"].notnull())
            & (ar_df["Due Date"] >= today)
            & (ar_df["Due Date"] <= (today + timedelta(days=15)))
        )
        ar_due = ar_df[ar_due_filter].copy()
        ar_due["Days Remaining"] = (ar_due["Due Date"] - today).dt.days
        ar_due["Days Remaining"] = ar_due["Days Remaining"].apply(
            lambda d: "today" if d == 0 else d
        )
        ar_due = ar_due.nsmallest(8, "Due Date")
    else:
        ar_due = pd.DataFrame()

    # --- AP upcoming dues (within next 15 days & not paid) ---
    if "Payment Status" in ap_df.columns and "Due Date" in ap_df.columns:
        ap_due_filter = (
            (ap_df["Payment Status"].astype(str).str.lower() == "not paid")
            & (ap_df["Due Date"].notnull())
            & (ap_df["Due Date"] >= today)
            & (ap_df["Due Date"] <= (today + timedelta(days=15)))
        )
        ap_due = ap_df[ap_due_filter].copy()
        ap_due["Days Remaining"] = (ap_due["Due Date"] - today).dt.days
        ap_due["Days Remaining"] = ap_due["Days Remaining"].apply(
            lambda d: "today" if d == 0 else d
        )
        ap_due = ap_due.nsmallest(8, "Due Date")
    else:
        ap_due = pd.DataFrame()

    # --- Select only required columns for output ---
    ar_columns = [
        "Invoice No.",
        "Invoice Date",
        "Due Date",
        "Customer Name",
        "Service Description",
        "Amount (AED)",
        "Payment Status",
        "VAT TRN",
        "VAT %",
        "Status",
    ]

    ap_columns = [
        "Invoice No.",
        "Invoice Date",
        "Due Date",
        "Supplier Name",
        "Service Description",
        "Amount (AED)",
        "Discount",
        "Discount Note",
        "Final Amount with Discount",
        "Payment Status",
        "VAT TRN",
        "VAT %",
        "Status",
    ]

    # Keep only columns that actually exist in each dataset
    ar_due = ar_due[[col for col in ar_columns if col in ar_due.columns]]
    ap_due = ap_due[[col for col in ap_columns if col in ap_due.columns]]

    return {
        "AR_Due": ar_due,
        "AP_Due": ap_due,
        "AR_df": ar_df,
        "AP_df": ap_df,
    }



def get_raw_ap_rebate_data():
    """Reads and returns the raw AP_Invoice_rebate.csv data."""
    ap_r = pd.read_csv("data/AP_Invoice_rebate.csv")
    return ap_r


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
    """Categorizes AR invoices by payment delay risk.

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
    """Categorizes AP invoices by payment delay risk.
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


import pandas as pd
from datetime import datetime

def view_risk_invoices(high_risk_invoices):
    """
    Returns a formatted dataframe of high-risk invoices for display in Streamlit.

    For AR invoices:
        Shows: Invoice No., Invoice Date, Due Date, Customer Name, Service Description,
               Amount (AED), Payment Status, VAT TRN, VAT %, Status.

    For AP invoices:
        Shows: Invoice No., Invoice Date, Due Date, Supplier Name, Service Description,
               Amount (AED), Payment Status, VAT TRN, VAT %, Status,
               Penalty, Penalty Note, Final Amount with Penalty.
    """
    if high_risk_invoices is None or high_risk_invoices.empty:
        return pd.DataFrame()

    df = high_risk_invoices.copy()

    # --- Detect AR vs AP ---
    if "Supplier Name" in df.columns:
        invoice_type = "AP"
    elif "Customer Name" in df.columns:
        invoice_type = "AR"
    else:
        invoice_type = "Unknown"

    # --- Convert date columns robustly ---
    for col in ["Invoice Date", "Due Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # --- Ensure Amount column numeric ---
    if "Amount (AED)" in df.columns:
        df["Amount (AED)"] = pd.to_numeric(df["Amount (AED)"], errors="coerce").fillna(0).round(2)

    # --- Safely compute Overdue Days ---
    if "Due Date" in df.columns:
        today = pd.Timestamp(datetime.now().date())
        valid_dates = df["Due Date"].notnull()
        df.loc[valid_dates, "Overdue Days"] = (today - df.loc[valid_dates, "Due Date"]).dt.days
        df.loc[df["Overdue Days"] < 0, "Overdue Days"] = 0
    else:
        df["Overdue Days"] = None

    # --- Sort by Overdue Days if available ---
    if "Overdue Days" in df.columns:
        df = df.sort_values(by="Overdue Days", ascending=False)

    # --- Format dates for display (convert back to date only) ---
    for col in ["Invoice Date", "Due Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    # --- Choose columns to display ---
    if invoice_type == "AP":
        display_columns = [
            "Invoice No.",
            "Invoice Date",
            "Due Date",
            "Supplier Name",
            "Service Description",
            "Amount (AED)",
            "Penalty",
            "Penalty Note",
            "Final Amount with Penalty",
            "Payment Status",
            "VAT TRN",
            "VAT %",
            "Status",
            
        ]
    else:  # AR
        display_columns = [
            "Invoice No.",
            "Invoice Date",
            "Due Date",
            "Customer Name",
            "Service Description",
            "Amount (AED)",
            "Payment Status",
            "VAT TRN",
            "VAT %",
            "Status",
        ]

    # --- Keep only columns that exist ---
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
