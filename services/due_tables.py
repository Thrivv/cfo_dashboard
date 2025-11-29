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


'''
if __name__ == "__main__":
    result = generate_due_tables()
    print("### Accounts Receivable Upcoming Due ###")
    print(result["AR_Due"])
    print("### Accounts Payable Upcoming Due ###")
    print(result["AP_Due"])
    top_payers = get_correct_time_payers(result["AR_df"])
    print("\n--- Top Correct-Time Payers (Opportunities) ---")
    print(top_payers)
'''

# ==============================================================
#                  FINANCIAL SUMMARY
# ==============================================================
import pandas as pd
import numpy as np
from typing import Dict, Any

def financial_summary() -> Dict[str, Any]:
    """Generates full financial summary for AP & AR. Hardened against missing columns/NaNs."""

    due_data = generate_due_tables()
    ar_df = due_data.get("AR_df", pd.DataFrame()).copy()
    ap_df = due_data.get("AP_df", pd.DataFrame()).copy()

    # Safety: ensure expected numeric columns exist
    for df in (ar_df, ap_df):
        if "Amount (AED)" not in df.columns:
            df["Amount (AED)"] = 0.0
        # normalize date column type if exists
        if "Due Date" in df.columns:
            df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")

    # Risk extraction (expects these functions to exist and handle empty dfs)
    ar_risk = get_AR_risk_data(ar_df)
    ap_risk = get_AP_risk_data(ap_df)

    # -------------------------------------------------------
    # TOTAL AP + AR
    # -------------------------------------------------------
    total_ap = float(ap_df["Amount (AED)"].sum())
    total_ar = float(ar_df["Amount (AED)"].sum())
    total_all = float(total_ap + total_ar)

    # -------------------------------------------------------
    # GROUP BY SUPPLIER / CUSTOMER
    # -------------------------------------------------------
    ap_by_supplier = (
        ap_df.groupby("Supplier Name")["Amount (AED)"].sum().reset_index()
        if "Supplier Name" in ap_df.columns else pd.DataFrame(columns=["Supplier Name", "Amount (AED)"])
    )
    ar_by_customer = (
        ar_df.groupby("Customer Name")["Amount (AED)"].sum().reset_index()
        if "Customer Name" in ar_df.columns else pd.DataFrame(columns=["Customer Name", "Amount (AED)"])
    )

    # -------------------------------------------------------
    # UPCOMING NEXT 7 DAYS
    # -------------------------------------------------------
    today = pd.Timestamp.today().normalize()
    next_7 = today + pd.Timedelta(days=7)

    # Normalize payment status columns to string safely
    ap_df["Payment Status"] = ap_df.get("Payment Status", "").astype(str)
    ar_df["Payment Status"] = ar_df.get("Payment Status", "").astype(str)

    # safe lowercase column for filtering
    ap_payment_lower = ap_df["Payment Status"].astype(str).str.lower()
    ar_payment_lower = ar_df["Payment Status"].astype(str).str.lower()

    # remove rows with invalid due date for upcoming filters
    upcoming_ap = ap_df[
        (ap_payment_lower == "not paid")
        & (ap_df.get("Due Date") >= today)
        & (ap_df.get("Due Date") <= next_7)
    ] if "Due Date" in ap_df.columns else ap_df.iloc[0:0]

    upcoming_ar = ar_df[
        (ar_payment_lower == "not paid")
        & (ar_df.get("Due Date") >= today)
        & (ar_df.get("Due Date") <= next_7)
    ] if "Due Date" in ar_df.columns else ar_df.iloc[0:0]

    # AP totals: handle optional 'Final Amount with Discount'
    ap_with_disc_total = float(
        upcoming_ap.get("Final Amount with Discount", upcoming_ap.get("Amount (AED)", pd.Series(0))).fillna(0).sum()
    )
    ap_without_disc_total = float(upcoming_ap.get("Amount (AED)", pd.Series(0)).fillna(0).sum())

    ap_by_supplier_next_7 = (
        upcoming_ap.groupby("Supplier Name").agg(
            with_discount=("Final Amount with Discount", lambda s: s.fillna(0).sum()),
            without_discount=("Amount (AED)", lambda s: s.fillna(0).sum())
        ).reset_index()
        if not upcoming_ap.empty and "Supplier Name" in upcoming_ap.columns else pd.DataFrame(columns=["Supplier Name","with_discount","without_discount"])
    )

    # AR totals: check if AR has a 'Final Amount with Discount' (if not, use Amount)
    ar_with_col = "Final Amount with Discount" if "Final Amount with Discount" in upcoming_ar.columns else "Amount (AED)"
    ar_with_disc_total = float(upcoming_ar.get(ar_with_col, pd.Series(0)).fillna(0).sum())
    ar_without_disc_total = float(upcoming_ar.get("Amount (AED)", pd.Series(0)).fillna(0).sum())

    ar_by_customer_next_7 = (
        upcoming_ar.groupby("Customer Name").agg(
            with_discount=(ar_with_col, lambda s: s.fillna(0).sum()),
            without_discount=("Amount (AED)", lambda s: s.fillna(0).sum())
        ).reset_index()
        if not upcoming_ar.empty and "Customer Name" in upcoming_ar.columns else pd.DataFrame(columns=["Customer Name","with_discount","without_discount"])
    )

    # -------------------------------------------------------
    # OVERDUE TOTALS
    # -------------------------------------------------------
    overdue_ap = ap_risk.get("high_risk_invoices", pd.DataFrame())
    overdue_ar = ar_risk.get("high_risk_invoices", pd.DataFrame())

    overdue_without_penalty = float(
        overdue_ap.get("Amount (AED)", pd.Series(0)).fillna(0).sum()
        + overdue_ar.get("Amount (AED)", pd.Series(0)).fillna(0).sum()
    )

    # Use Final Amount with Penalty for both AP and AR if present; fall back to Amount (AED)
    def sum_with_penalty(df):
        if df is None or df.empty:
            return 0.0
        if "Final Amount with Penalty" in df.columns:
            return float(df["Final Amount with Penalty"].fillna(df.get("Amount (AED)", 0)).sum())
        return float(df.get("Amount (AED)", pd.Series(0)).fillna(0).sum())

    overdue_with_penalty = float(sum_with_penalty(overdue_ap) + sum_with_penalty(overdue_ar))

    # -------------------------------------------------------
    # REBATE (DISCOUNT EARNED)
    # -------------------------------------------------------
    paid_ap = ap_df[ap_df.get("Status", "").astype(str).str.lower() == "paid"].copy()
    if "Final Amount with Discount" in paid_ap.columns:
        paid_ap["discount_earned"] = (paid_ap.get("Amount (AED)", 0) - paid_ap["Final Amount with Discount"]).fillna(0)
    else:
        # if no final amount field, assume 0 discount earned
        paid_ap["discount_earned"] = 0.0

    total_rebate = float(paid_ap["discount_earned"].sum())

    rebate_by_supplier = (
        paid_ap.groupby("Supplier Name")["discount_earned"].sum().reset_index()
        if "Supplier Name" in paid_ap.columns else pd.DataFrame(columns=["Supplier Name", "discount_earned"])
    )

    # -------------------------------------------------------
    # OUTPUT (ensure python-native types where possible)
    # -------------------------------------------------------
    return {
        "total_amount_all": total_all,

        "total_account_payable": total_ap,
        "ap_by_supplier": ap_by_supplier,

        "total_account_receivable": total_ar,
        "ar_by_customer": ar_by_customer,

        "upcoming_ap": {
            "total_with_discount": ap_with_disc_total,
            "total_without_discount": ap_without_disc_total,
            "by_supplier": ap_by_supplier_next_7
        },

        "upcoming_ar": {
            "total_with_discount": ar_with_disc_total,
            "total_without_discount": ar_without_disc_total,
            "by_customer": ar_by_customer_next_7
        },

        "overdue": {
            "total_without_penalty": overdue_without_penalty,
            "total_with_penalty": overdue_with_penalty,
            "overdue_ap_rows": overdue_ap,   # include DataFrames if downstream wants them
            "overdue_ar_rows": overdue_ar
        },

        "rebates": {
            "total_rebate_earned": total_rebate,
            "rebate_by_supplier": rebate_by_supplier
        }
    }

# ==============================================================
#                      MANUAL TEST
# ==============================================================

if __name__ == "__main__":
    summary = financial_summary()
    print("=== Financial Summary ===")
    for key, value in summary.items():
        print(f"\n--- {key} ---")
        print(value)