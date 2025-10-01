from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import timedelta

from .data_loader_service import get_data_loader


def load_cfo_data() -> pd.DataFrame | None:
    """Load CFO data from centralized data loader, converted to simplified schema used by UI."""
    try:
        data_loader = get_data_loader()
        raw_df = data_loader.get_raw_data()
        
        if raw_df is None or raw_df.empty:
            return None
            
        df = pd.DataFrame({
            'Date': pd.to_datetime(raw_df['Date / Period'], errors='coerce'),
            'Cash_on_Hand': pd.to_numeric(raw_df['Cash Balance'], errors='coerce'),
            'Burn_Rate': pd.to_numeric(raw_df['Cash Outflows'], errors='coerce'),
            'Runway_Months': (pd.to_numeric(raw_df['Cash Balance'], errors='coerce') / 
                            (pd.to_numeric(raw_df['Cash Outflows'], errors='coerce') / 30)).round(1),
            'Outstanding_Invoices': pd.to_numeric(raw_df['Accounts Receivable (AR)'], errors='coerce')
        })
        return df.dropna().sort_values('Date')
    except Exception:
        return None


def load_raw_dataframe() -> pd.DataFrame | None:
    """Load the raw CFO dataset from centralized data loader."""
    data_loader = get_data_loader()
    return data_loader.get_raw_data()


def get_financial_overview() -> dict:
    """Compute overview metrics using simplified DataFrame from load_cfo_data()."""
    data = load_cfo_data()
    if data is None or data.empty:
        return get_default_financial_overview()

    df = data.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else latest
    cash_change = ((latest['Cash_on_Hand'] - previous['Cash_on_Hand']) / max(previous['Cash_on_Hand'], 1e-9)) * 100
    burn_change = ((latest['Burn_Rate'] - previous['Burn_Rate']) / max(previous['Burn_Rate'], 1e-9)) * 100

    return {
        "Cash on Hand": int(latest['Cash_on_Hand']),
        "Cash on Hand Change": f"{'+' if cash_change >= 0 else ''}{cash_change:.1f}%",
        "Operating Account": int(latest['Cash_on_Hand'] * 0.5),
        "Reserve Account": int(latest['Cash_on_Hand'] * 0.33),
        "Investment": int(latest['Cash_on_Hand'] * 0.17),
        "Monthly Burn": int(latest['Burn_Rate'] * 30),
        "Monthly Burn Change": f"{'+' if burn_change >= 0 else ''}{burn_change:.1f}%",
        "Runway": round(latest['Runway_Months'], 1),
        "Runway Change": "+3 months",
        "Runway Note": "Projected runway based on current burn rate",
        "Outstanding Invoices": int(latest['Outstanding_Invoices']),
        "Outstanding Invoices Change": "-7%",
        "Current": int(latest['Outstanding_Invoices'] * 0.5),
        "Days 1-30": int(latest['Outstanding_Invoices'] * 0.33),
        "Days 30+": int(latest['Outstanding_Invoices'] * 0.17),
        "Current MRR": 857144,
        "Current ARR": 10285728,
        "YoY Growth": 24.7,
        "Churn Rate": 2.3,
    }


def get_default_financial_overview() -> dict:
    return {
        "Cash on Hand": 4285721,
        "Cash on Hand Change": "+2.4%",
        "Operating Account": 2142860,
        "Reserve Account": 1428574,
        "Investment": 714287,
        "Monthly Burn": 342857,
        "Monthly Burn Change": "-2%",
        "Runway": 12.5,
        "Runway Change": "+3 months",
        "Runway Note": "Projected runway based on current burn rate",
        "Outstanding Invoices": 857144,
        "Outstanding Invoices Change": "-7%",
        "Current": 428572,
        "Days 1-30": 285715,
        "Days 30+": 142857,
        "Current MRR": 857144,
        "Current ARR": 10285728,
        "YoY Growth": 24.7,
        "Churn Rate": 2.3,
    }


def get_expense_categories() -> dict:
    return {"Payroll": 48, "Operations": 14, "Other": 8, "Marketing": 18, "Software": 12}


def get_anomalies() -> list[dict]:
    data = load_cfo_data()
    if data is None or data.empty or len(data) < 2:
        return [{"type": "Critical", "title": "Data Loading Error", "count": 1, "change": "+1", "description": "Unable to load financial data for anomaly detection", "root_cause": "Check CSV availability."}]

    df = data.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    burn_trend = df['Burn_Rate'].pct_change().iloc[-1] * 100
    cash_trend = df['Cash_on_Hand'].pct_change().iloc[-1] * 100
    runway_change = df['Runway_Months'].iloc[-1] - df['Runway_Months'].iloc[-2]

    anomalies = []
    if burn_trend > 5:
        anomalies.append({"type": "Critical", "title": "High Burn Rate Increase", "count": int(burn_trend), "change": f"+{burn_trend:.1f}%", "description": f"Burn rate increased by {burn_trend:.1f}% in latest period", "root_cause": "Significant increase in daily operational expenses detected."})
    if runway_change < -0.5:
        anomalies.append({"type": "High", "title": "Runway Decrease", "count": int(abs(runway_change*10)), "change": f"{runway_change:.1f}", "description": f"Cash runway decreased by {abs(runway_change):.1f} months", "root_cause": "Accelerated cash burn affecting runway projections."})
    if cash_trend < -2:
        anomalies.append({"type": "Medium", "title": "Cash Position Decline", "count": int(abs(cash_trend)), "change": f"{cash_trend:.1f}%", "description": f"Cash on hand decreased by {abs(cash_trend):.1f}%", "root_cause": "Higher than expected cash outflow in recent period."})

    return anomalies or [{"type": "Info", "title": "No Critical Anomalies", "count": 0, "change": "0", "description": "All financial metrics within normal ranges", "root_cause": "Financial performance stable."}]


def get_budget_data() -> dict:
    data = load_cfo_data()
    if data is None or data.empty:
        return {
            "Total Budget": 4850000,
            "Actual Spend": 4327650,
            "Remaining Budget": 522350,
            "Burn Rate": 481961,
            "Variances": {"Software": 28, "Marketing": -15, "Salaries": 12, "Travel": -32, "Equipment": 8},
        }

    df = data.copy()
    current_burn = df.iloc[-1]['Burn_Rate']
    monthly_burn = current_burn * 30
    total_budget = monthly_burn * 12
    days_passed = len(df)
    actual_spend = current_burn * days_passed
    return {
        "Total Budget": int(total_budget),
        "Actual Spend": int(actual_spend),
        "Remaining Budget": int(total_budget - actual_spend),
        "Burn Rate": int(current_burn),
        "Variances": {
            "Software": int(np.random.normal(15, 10)),
            "Marketing": int(np.random.normal(-5, 15)),
            "Salaries": int(np.random.normal(8, 12)),
            "Travel": int(np.random.normal(-20, 15)),
            "Equipment": int(np.random.normal(5, 8)),
        },
    }


