from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

# kpi_service import removed - functions were unused


def generate_insights(
    df: pd.DataFrame, raw_df: pd.DataFrame | None = None
) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    insights: List[Dict[str, Any]] = []
    latest = df.iloc[-1]
    current_burn = latest["Burn_Rate"]
    avg_burn = df["Burn_Rate"].tail(30).mean()
    if current_burn > avg_burn * 1.2:
        insights.append(
            {
                "title": "Elevated Cash Burn",
                "description": f"Current burn rate (${current_burn:,.0f}) is 20% above the 30-day average",
                "impact": "high",
                "recommendation": "Review operational expenses and identify cost reduction opportunities",
                "category": "cash_flow",
            }
        )
    runway = latest["Runway_Months"]
    if runway < 12:
        insights.append(
            {
                "title": "Limited Cash Runway",
                "description": f"Current runway of {runway:.1f} months requires immediate attention",
                "impact": "critical",
                "recommendation": "Consider fundraising or aggressive cost reduction measures",
                "category": "runway",
            }
        )
    if len(df) >= 30:
        cash_trend = df["Cash_on_Hand"].tail(30).pct_change().mean()
        if cash_trend < -0.02:
            insights.append(
                {
                    "title": "Declining Cash Position",
                    "description": "Cash balance has been consistently declining over the past month",
                    "impact": "medium",
                    "recommendation": "Monitor cash flow closely and prepare contingency plans",
                    "category": "trend",
                }
            )
        invoice_trend = df["Outstanding_Invoices"].tail(30).pct_change().mean()
        if invoice_trend > 0.05:
            insights.append(
                {
                    "title": "Growing Receivables",
                    "description": "Outstanding invoices have been increasing, impacting cash flow",
                    "impact": "medium",
                    "recommendation": "Review collection processes and customer payment terms",
                    "category": "receivables",
                }
            )
    return insights[:5]


def check_alerts(overview: Dict[str, Any]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    cash = overview.get("Cash on Hand", 0)
    if cash < 1_000_000:
        alerts.append(
            {
                "type": "Critical",
                "title": "Critical Cash Position",
                "message": f"Cash on hand (${cash:,}) is below critical threshold",
                "severity": "critical",
            }
        )
    elif cash < 2_000_000:
        alerts.append(
            {
                "type": "High",
                "title": "Low Cash Position",
                "message": f"Cash on hand (${cash:,}) is below high threshold",
                "severity": "high",
            }
        )
    elif cash < 5_000_000:
        alerts.append(
            {
                "type": "Medium",
                "title": "Moderate Cash Position",
                "message": f"Cash on hand (${cash:,}) is below medium threshold",
                "severity": "medium",
            }
        )
    burn = overview.get("Monthly Burn", 0)
    ratio = burn / max(cash, 1)
    if ratio > 0.15:
        alerts.append(
            {
                "type": "Critical",
                "title": "Critical Burn Rate",
                "message": f"Monthly burn (${burn:,}) is {ratio:.1%} of cash on hand",
                "severity": "critical",
            }
        )
    elif ratio > 0.10:
        alerts.append(
            {
                "type": "High",
                "title": "High Burn Rate",
                "message": f"Monthly burn (${burn:,}) is {ratio:.1%} of cash on hand",
                "severity": "high",
            }
        )
    elif ratio > 0.05:
        alerts.append(
            {
                "type": "Medium",
                "title": "Moderate Burn Rate",
                "message": f"Monthly burn (${burn:,}) is {ratio:.1%} of cash on hand",
                "severity": "medium",
            }
        )
    runway = overview.get("Runway", 0)
    if runway < 3:
        alerts.append(
            {
                "type": "Critical",
                "title": "Critical Runway",
                "message": f"Runway ({runway} months) below critical threshold",
                "severity": "critical",
            }
        )
    elif runway < 6:
        alerts.append(
            {
                "type": "High",
                "title": "Low Runway",
                "message": f"Runway ({runway} months) below high threshold",
                "severity": "high",
            }
        )
    elif runway < 12:
        alerts.append(
            {
                "type": "Medium",
                "title": "Moderate Runway",
                "message": f"Runway ({runway} months) below medium threshold",
                "severity": "medium",
            }
        )
    return alerts


def ai_insights(df: pd.DataFrame) -> List[str]:
    """Return simple AI-style insights derived from the latest row."""
    if df is None or df.empty:
        return ["No data available for insights"]
    latest = df.iloc[-1]
    insights: List[str] = [
        f"Current cash position: ${latest['Cash_on_Hand']:,.0f}",
        f"Monthly burn rate: ${latest['Burn_Rate']:,.0f}",
        f"Runway remaining: {latest['Runway_Months']:.1f} months",
    ]
    if latest["Runway_Months"] < 6:
        insights.append("WARNING: Cash runway is below 6 months - consider fundraising")
    return insights


def trend_analysis(df: pd.DataFrame) -> List[str]:
    """Return trend analysis statements from recent data."""
    if df is None or df.empty:
        return ["No data available for trend analysis"]
    trends: List[str] = []
    if len(df) > 7:
        cash_trend = df["Cash_on_Hand"].tail(7).pct_change().mean()
        if cash_trend > 0.01:
            trends.append("Cash position trending upward")
        elif cash_trend < -0.01:
            trends.append("Cash position trending downward")
        else:
            trends.append("Cash position relatively stable")
    return trends


def explain_kpi(kpi: str, change_value: float, df: pd.DataFrame) -> List[str]:
    """Return short explanations for a KPI change."""
    explanations: List[str] = []
    if abs(change_value) > 10:
        explanations.append(f"Significant {kpi} change detected")
    explanations.append(
        f"Trend analysis shows {'positive' if change_value > 0 else 'negative'} movement"
    )
    return explanations


# overview_and_alerts function removed - was unused and depended on deleted kpi_service functions
