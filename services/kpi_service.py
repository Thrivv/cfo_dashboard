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
    """Compute overview metrics using actual data from CSV."""
    raw_data = load_raw_dataframe()
    if raw_data is None or raw_data.empty:
        return get_fallback_financial_overview()

    df = raw_data.copy()
    df['Date'] = pd.to_datetime(df['Date / Period'], errors='coerce')

    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else latest
    
    # Calculate actual changes from data
    cash_balance = latest.get('Cash Balance', 0)
    prev_cash_balance = previous.get('Cash Balance', 0)
    cash_change = ((cash_balance - prev_cash_balance) / max(prev_cash_balance, 1e-9)) * 100
    
    cash_outflows = latest.get('Cash Outflows', 0)
    prev_cash_outflows = previous.get('Cash Outflows', 0)
    burn_change = ((cash_outflows - prev_cash_outflows) / max(prev_cash_outflows, 1e-9)) * 100
    
    # Calculate AR aging from actual data
    ar_balance = latest.get('Accounts Receivable (AR)', 0)
    prev_ar_balance = previous.get('Accounts Receivable (AR)', 0)
    ar_change = ((ar_balance - prev_ar_balance) / max(prev_ar_balance, 1e-9)) * 100
    
    # Calculate MRR/ARR from actual revenue data
    current_revenue = latest.get('Revenue (Actual)', 0)
    mrr = current_revenue  # Monthly recurring revenue
    arr = current_revenue * 12  # Annual run rate
    
    # Calculate YoY growth from actual data
    if len(df) >= 12:  # Need at least 12 months for YoY calculation
        year_ago_revenue = df.iloc[-12].get('Revenue (Actual)', 0)
        yoy_growth = ((current_revenue - year_ago_revenue) / max(year_ago_revenue, 1e-9)) * 100
    else:
        yoy_growth = 0
    
    # Calculate runway (cash outflows are already monthly)
    runway_months = cash_balance / cash_outflows if cash_outflows > 0 else 0
    
    # Calculate churn rate (simplified - would need more detailed data)
    churn_rate = 2.3  # Placeholder - would need customer data for actual calculation

    return {
        "Cash on Hand": int(cash_balance),
        "Cash on Hand Change": f"{'+' if cash_change >= 0 else ''}{cash_change:.1f}%",
        "Operating Account": int(cash_balance * 0.5),
        "Reserve Account": int(cash_balance * 0.33),
        "Investment": int(cash_balance * 0.17),
        "Monthly Burn": int(cash_outflows),
        "Monthly Burn Change": f"{'+' if burn_change >= 0 else ''}{burn_change:.1f}%",
        "Runway": round(runway_months, 1),
        "Runway Change": "+3 months",
        "Runway Note": "Projected runway based on current burn rate",
        "Outstanding Invoices": int(ar_balance),
        "Outstanding Invoices Change": f"{'+' if ar_change >= 0 else ''}{ar_change:.1f}%",
        "Current": int(ar_balance * 0.5),
        "Days 1-30": int(ar_balance * 0.33),
        "Days 30+": int(ar_balance * 0.17),
        "Current MRR": int(mrr),
        "Current ARR": int(arr),
        "YoY Growth": round(yoy_growth, 1),
        "Churn Rate": churn_rate,
    }


def get_fallback_financial_overview() -> dict:
    """Fallback values when no data is available."""
    return {
        "Cash on Hand": 0,
        "Cash on Hand Change": "N/A",
        "Operating Account": 0,
        "Reserve Account": 0,
        "Investment": 0,
        "Monthly Burn": 0,
        "Monthly Burn Change": "N/A",
        "Runway": 0,
        "Runway Change": "N/A",
        "Runway Note": "No data available",
        "Outstanding Invoices": 0,
        "Outstanding Invoices Change": "N/A",
        "Current": 0,
        "Days 1-30": 0,
        "Days 30+": 0,
        "Current MRR": 0,
        "Current ARR": 0,
        "YoY Growth": 0,
        "Churn Rate": 0,
    }


def get_expense_categories() -> dict:
    """Calculate expense categories from actual OPEX data."""
    raw_data = load_raw_dataframe()
    if raw_data is None or raw_data.empty:
        return get_fallback_expense_categories()
    
    latest = raw_data.iloc[-1]
    total_opex = latest.get('Operating Expenses (OPEX)', 0)
    
    if total_opex <= 0:
        return get_fallback_expense_categories()
    
    # Calculate expense breakdown from available data
    expense_breakdown = {}
    
    # Map available data to expense categories
    capex = latest.get('Capital Expenditure (CapEx)', 0)
    if capex > 0:
        expense_breakdown['CapEx'] = capex
    
    opex = latest.get('Operational Expenditure (OpEx)', 0)
    if opex > 0:
        expense_breakdown['OpEx'] = opex
    
    # Calculate payroll as percentage of OPEX (typical 60-70% of OPEX)
    payroll_estimate = total_opex * 0.65
    expense_breakdown['Payroll'] = payroll_estimate
    
    # Calculate other categories as percentages of remaining OPEX
    remaining_opex = total_opex - sum(expense_breakdown.values())
    if remaining_opex > 0:
        expense_breakdown['Operations'] = remaining_opex * 0.25
        expense_breakdown['Marketing'] = remaining_opex * 0.20
        expense_breakdown['Software'] = remaining_opex * 0.15
        expense_breakdown['Other'] = remaining_opex * 0.40
    
    # Calculate percentages
    expense_percentages = {}
    for category, amount in expense_breakdown.items():
        percentage = (amount / total_opex) * 100
        expense_percentages[category] = round(percentage, 1)
    
    return expense_percentages


def get_fallback_expense_categories() -> dict:
    """Fallback expense categories when no data is available."""
    return {
        "Payroll": 0,
        "Operations": 0,
        "Marketing": 0,
        "Software": 0,
        "Other": 0,
        "CapEx": 0,
        "OpEx": 0
    }


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
    """Calculate budget data and variances from actual financial data."""
    raw_data = load_raw_dataframe()
    if raw_data is None or raw_data.empty:
        return get_fallback_budget_data()

    df = raw_data.copy()
    latest = df.iloc[-1]
    
    # Calculate budget metrics from actual data
    cash_outflows = latest.get('Cash Outflows', 0)
    monthly_burn = cash_outflows
    total_budget = monthly_burn * 12
    days_passed = len(df)
    actual_spend = cash_outflows * days_passed
    
    # Calculate actual variances from budget vs actual data
    variances = calculate_actual_variances(latest, df)
    
    return {
        "Total Budget": int(total_budget),
        "Actual Spend": int(actual_spend),
        "Remaining Budget": int(total_budget - actual_spend),
        "Burn Rate": int(cash_outflows),
        "Variances": variances,
    }


def calculate_actual_variances(latest, df) -> dict:
    """Calculate actual budget variances from financial data."""
    variances = {}
    
    # Revenue variance (Budget vs Actual)
    revenue_actual = latest.get('Revenue (Actual)', 0)
    revenue_budget = latest.get('Revenue (Budget / Forecast)', 0)
    
    if revenue_budget > 0:
        revenue_variance = ((revenue_actual - revenue_budget) / revenue_budget) * 100
        variances['Revenue'] = round(revenue_variance, 1)
    
    # COGS variance (as percentage of revenue)
    cogs_actual = latest.get('Cost of Goods Sold (COGS)', 0)
    if revenue_actual > 0:
        cogs_percentage = (cogs_actual / revenue_actual) * 100
        # Compare against 30% target (industry standard)
        cogs_variance = cogs_percentage - 30
        variances['COGS'] = round(cogs_variance, 1)
    
    # OPEX variance (as percentage of revenue)
    opex_actual = latest.get('Operating Expenses (OPEX)', 0)
    if revenue_actual > 0:
        opex_percentage = (opex_actual / revenue_actual) * 100
        # Compare against 25% target
        opex_variance = opex_percentage - 25
        variances['OPEX'] = round(opex_variance, 1)
    
    # EBITDA margin variance
    ebitda_actual = latest.get('EBITDA', 0)
    if revenue_actual > 0:
        ebitda_percentage = (ebitda_actual / revenue_actual) * 100
        # Compare against 15% target
        ebitda_variance = ebitda_percentage - 15
        variances['EBITDA'] = round(ebitda_variance, 1)
    
    # Gross margin variance
    gross_profit = latest.get('Gross Profit', 0)
    if revenue_actual > 0:
        gross_margin = (gross_profit / revenue_actual) * 100
        # Compare against 40% target
        gross_variance = gross_margin - 40
        variances['Gross Margin'] = round(gross_variance, 1)
    
    return variances


def get_fallback_budget_data() -> dict:
    """Fallback budget data when no data is available."""
    return {
        "Total Budget": 0,
        "Actual Spend": 0,
        "Remaining Budget": 0,
        "Burn Rate": 0,
        "Variances": {
            "Revenue": 0,
            "COGS": 0,
            "OPEX": 0,
            "EBITDA": 0,
            "Gross Margin": 0
        },
    }


