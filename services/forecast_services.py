import os
from dotenv import load_dotenv
import requests
import time
import pandas as pd
import numpy as np
from typing import Dict, Optional
import streamlit as st
import re
from utils import get_data_loader


load_dotenv()
API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def run_forecast_job(prompt, sampling_params=None):
    """
    Submit a job to the Forecasting RunPod serverless endpoint.

    Args:
        prompt (str): Forecasting query or request
        sampling_params (dict): Optional dict for temperature, max_tokens, etc.
    """
    data = {"input": {"prompt": prompt, "application": "Forecasting"}}

    if sampling_params:
        data["input"]["sampling_params"] = sampling_params

    # Step 1: Submit the job
    response = requests.post(f"{BASE_URL}/run", headers=headers, json=data)
    job = response.json()
    job_id = job["id"]

    # Step 2: Poll for the result
    while True:
        status_response = requests.get(f"{BASE_URL}/status/{job_id}", headers=headers)
        status_json = status_response.json()

        if status_json["status"] == "COMPLETED":
            print(f"=== Forecasting Result ===")
            print(status_json["output"])
            return status_json["output"]
        elif status_json["status"] == "FAILED":
            raise RuntimeError(f"Forecast job failed: {status_json}")
        else:
            time.sleep(1)


class ForecastPreviewService:
    """Service for generating forecast previews for homepage."""

    def get_monthly_payables_vs_receivables(self) -> Dict:
        """Get monthly payables vs receivables forecast."""
        try:
            data_loader = get_data_loader()
            raw_df = data_loader.get_raw_data()

            if raw_df is None or raw_df.empty:
                return {"error": "No data available"}

            # Get latest data
            latest = raw_df.iloc[-1]
            ap = latest.get("Accounts Payable (AP)", 0)
            ar = latest.get("Accounts Receivable (AR)", 0)

            # Simple trend calculation
            if len(raw_df) > 1:
                prev = raw_df.iloc[-2]
                ap_trend = (
                    (ap - prev.get("Accounts Payable (AP)", 0))
                    / max(prev.get("Accounts Payable (AP)", 1), 1)
                ) * 100
                ar_trend = (
                    (ar - prev.get("Accounts Receivable (AR)", 0))
                    / max(prev.get("Accounts Receivable (AR)", 1), 1)
                ) * 100
            else:
                ap_trend = 0
                ar_trend = 0

            return {
                "payables": ap,
                "receivables": ar,
                "payables_trend": ap_trend,
                "receivables_trend": ar_trend,
                "net_position": ar - ap,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_revenue_forecast_preview(self) -> Dict:
        """Get revenue forecast preview for next 3 months."""
        try:
            data_loader = get_data_loader()
            raw_df = data_loader.get_raw_data()

            if raw_df is None or raw_df.empty:
                return {"error": "No data available"}

            # Sort data by date to get proper chronological order
            raw_df["Date"] = pd.to_datetime(raw_df["Date / Period"], errors="coerce")
            raw_df_sorted = raw_df.sort_values("Date")

            # Get recent revenue data (last 6 months chronologically)
            revenue_data = raw_df_sorted["Revenue (Actual)"].tail(6).values

            if len(revenue_data) < 2:
                return {"error": "Insufficient data"}

            # Simple linear trend forecast
            x = np.arange(len(revenue_data))
            coeffs = np.polyfit(x, revenue_data, 1)
            y_pred = np.polyval(coeffs, x)

            # Calculate R-squared
            ss_res = np.sum((revenue_data - y_pred) ** 2)
            ss_tot = np.sum((revenue_data - np.mean(revenue_data)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            # Calculate trend strength (0-100)
            trend_strength = min(100, max(0, r_squared * 100))

            # Forecast next 3 months
            next_months = np.arange(len(revenue_data), len(revenue_data) + 3)
            forecast = np.polyval(coeffs, next_months)

            current_revenue = revenue_data[-1]
            next_month_revenue = forecast[0]
            growth_rate = (
                (next_month_revenue - current_revenue) / current_revenue
            ) * 100

            return {
                "current_revenue": current_revenue,
                "next_month_forecast": next_month_revenue,
                "growth_rate": growth_rate,
                "forecast_months": forecast.tolist(),
                "r_squared": r_squared,
                "trend_strength": trend_strength,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_cash_flow_forecast_preview(self) -> Dict:
        """Get cash flow forecast preview."""
        try:
            data_loader = get_data_loader()
            raw_df = data_loader.get_raw_data()

            if raw_df is None or raw_df.empty:
                return {"error": "No data available"}

            # Sort data by date to get proper chronological order
            raw_df["Date"] = pd.to_datetime(raw_df["Date / Period"], errors="coerce")
            raw_df_sorted = raw_df.sort_values("Date")

            # Get recent cash flow data (last 6 months chronologically)
            cash_balance = raw_df_sorted["Cash Balance"].tail(6).values
            cash_outflows = raw_df_sorted["Cash Outflows"].tail(6).values

            if len(cash_balance) < 2:
                return {"error": "Insufficient data"}

            # Calculate burn rate
            avg_monthly_burn = np.mean(cash_outflows)
            current_cash = cash_balance[-1]
            runway_months = (
                current_cash / avg_monthly_burn if avg_monthly_burn > 0 else 0
            )

            # Calculate burn trend
            if len(cash_outflows) >= 2:
                burn_trend = (
                    (cash_outflows[-1] - cash_outflows[0]) / max(cash_outflows[0], 1)
                ) * 100
            else:
                burn_trend = 0

            # Simple forecast
            next_month_cash = current_cash - avg_monthly_burn

            return {
                "current_cash": current_cash,
                "monthly_burn": avg_monthly_burn,
                "runway_months": runway_months,
                "next_month_forecast": next_month_cash,
                "burn_trend": burn_trend,
            }
        except Exception as e:
            return {"error": str(e)}


def parse_forecast_data(forecast_text: str) -> Optional[pd.DataFrame]:
    """
    Parse forecast data from text and return DataFrame for charting.

    Args:
        forecast_text (str): Raw forecast text containing date-value pairs

    Returns:
        Optional[pd.DataFrame]: DataFrame with 'Date' and 'Value' columns, or None if parsing fails
    """
    try:
        # First try to parse as CSV format (new format)
        lines = forecast_text.strip().split("\n")
        csv_lines = []

        for line in lines:
            # Skip header lines that don't contain date-value pairs
            if "," in line and re.match(r"\d{4}-\d{2}-\d{2}", line):
                csv_lines.append(line)

        if csv_lines:
            # Parse CSV format
            df = pd.read_csv(
                pd.io.common.StringIO("\n".join(csv_lines)), names=["Date", "Value"]
            )
            df["Date"] = pd.to_datetime(df["Date"])
            df["Value"] = df["Value"].astype(float)
            return df

        # Fallback to regex pattern for space-separated format (old format)
        forecast_pattern = r"(\d{4}-\d{2}-\d{2})\s+(\d+\.\d+)"
        matches = re.findall(forecast_pattern, forecast_text)

        if matches:
            # Create DataFrame
            df = pd.DataFrame(matches, columns=["Date", "Value"])
            df["Date"] = pd.to_datetime(df["Date"])
            df["Value"] = df["Value"].astype(float)
            return df
        return None
    except Exception as e:
        print(f"Error parsing forecast data: {e}")
        return None


# for Streamlit chart (Homepage)
def create_forecast_chart(
    forecast_data: str, department: str, chart_height: int = 200
) -> bool:
    """
    Create a line chart for forecast data using Streamlit.

    Args:
        forecast_data (str): Raw forecast text containing date-value pairs
        department (str): Department name for the chart caption
        chart_height (int): Height of the chart in pixels

    Returns:
        bool: True if chart was created successfully, False otherwise
    """
    try:
        df = parse_forecast_data(forecast_data)
        if df is not None and not df.empty:
            st.line_chart(
                df.set_index("Date")["Value"],
                use_container_width=True,
                height=chart_height,
            )

            # Dynamic time range based on actual forecast data
            start_date = df["Date"].min().strftime("%b %d, %Y")
            end_date = df["Date"].max().strftime("%b %d, %Y")
            st.caption(
                f"Forecast for {department} Department - {start_date} to {end_date}"
            )
            return True
        return False
    except Exception as e:
        st.error(f"Error creating chart: {e}")
        return False


# for Plotly chart (Budgeting_Forecasting page)
def create_forecast_chart_with_plotly(
    forecast_data: str,
    department: str,
    chart_height: int = 400,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
):
    """
    Create a line chart for forecast data using Plotly (for Budgeting_Forecasting page).

    Args:
        forecast_data (str): Raw forecast text containing date-value pairs
        department (str): Department name for the chart title
        chart_height (int): Height of the chart in pixels
        start_date (Optional[pd.Timestamp]): Start date for filtering the forecast data.
        end_date (Optional[pd.Timestamp]): End date for filtering the forecast data.

    Returns:
        Optional[object]: Plotly figure object, or None if creation fails
    """
    try:
        import plotly.graph_objects as go

        df = parse_forecast_data(forecast_data)
        if df is not None and not df.empty:
            # Filter data based on date range if provided
            if start_date and end_date:
                df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

            if df.empty:
                st.warning("No forecast data available for the selected date range.")
                return None

            # Create Plotly line chart
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["Value"],
                    mode="lines+markers",
                    name="Forecast",
                    line=dict(color="#e74c3c", width=3),
                    marker=dict(size=6),
                )
            )

            # Dynamic time range for title
            chart_start_date = df["Date"].min().strftime("%b %d, %Y")
            chart_end_date = df["Date"].max().strftime("%b %d, %Y")

            # Apply consistent theme
            fig.update_layout(
                template="plotly_dark",
                height=chart_height,
                title=f"Revenue Forecast: {department} Department ({chart_start_date} to {chart_end_date})",
                xaxis_title="Date",
                yaxis_title="Revenue ($)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=20, t=50, b=40),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
            )

            fig.update_xaxes(
                gridcolor="rgba(255,255,255,0.08)",
                tickformat="%b %d, %Y",
                tickangle=45,
                nticks=8,
            )
            fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")

            return fig
        return None
    except Exception as e:
        print(f"Error creating Plotly chart: {e}")
        return None


def _validate_llm_output(insights: str) -> bool:
    """
    Validate the LLM output to ensure it contains the required sections.

    Args:
        insights (str): The LLM-generated insights text.

    Returns:
        bool: True if the output is valid, False otherwise.
    """
    return "Key Findings:" in insights and "Conclusion:" in insights


def _get_historical_data(
    department: str, forecast_start_date: pd.Timestamp
) -> pd.DataFrame:
    """Load and prepare historical data for a given department."""
    data_path = os.getenv("FORECAST_HIST_DATA_PATH")
    if not data_path:
        return pd.DataFrame()

    historical_data_path = os.path.join(data_path, "cfo_dash_2023_2024.csv")
    try:
        historical_df = pd.read_csv(historical_data_path)
        historical_df.columns = historical_df.columns.str.strip()
        historical_df["Date / Period"] = pd.to_datetime(historical_df["Date / Period"])

        historical_df_dep = historical_df[
            historical_df["Business Unit / Department"] == department
        ].copy()
        if historical_df_dep.empty:
            return pd.DataFrame()

        historical_df_dep = historical_df_dep.set_index("Date / Period")
        hist_end_date = forecast_start_date
        hist_start_date = hist_end_date - pd.DateOffset(years=2)

        relevant_historical = historical_df_dep[
            (historical_df_dep.index >= hist_start_date)
            & (historical_df_dep.index < hist_end_date)
        ]
        return relevant_historical
    except FileNotFoundError:
        return pd.DataFrame()


def _prepare_llm_prompt(
    department: str, df: pd.DataFrame, historical_df_dep: pd.DataFrame
) -> str:
    """Prepare the prompt for the LLM with forecast and historical data."""
    forecast_values = df["Value"].values
    min_value, max_value, avg_value = (
        forecast_values.min(),
        forecast_values.max(),
        forecast_values.mean(),
    )
    trend = (
        (forecast_values[-1] - forecast_values[0]) / forecast_values[0] * 100
        if forecast_values[0] > 0
        else 0
    )
    volatility = forecast_values.std()
    volatility_pct = (volatility / avg_value * 100) if avg_value > 0 else 0

    peak_idx, trough_idx = forecast_values.argmax(), forecast_values.argmin()
    peak_date, trough_date = df.iloc[peak_idx]["Date"], df.iloc[trough_idx]["Date"]

    data_summary = f"""FORECAST DATA FOR {department.upper()} DEPARTMENT:
Forecast Period: {len(df)} days
Average Value: ${avg_value:,.0f}
Range: ${min_value:,.0f} - ${max_value:,.0f}
Trend: {trend:+.1f}% change
Volatility: {volatility_pct:.1f}%
Peak: ${max_value:,.0f} on {peak_date.strftime('%Y-%m-%d')}
Lowest: ${min_value:,.0f} on {trough_date.strftime('%Y-%m-%d')}

Sample Forecast Values:
{df.head(10).to_string(index=False)}

Recent Values:
{df.tail(5).to_string(index=False)}"""

    historical_summary = ""
    if not historical_df_dep.empty:
        hist_avg = historical_df_dep["Revenue (Actual)"].mean()
        hist_min = historical_df_dep["Revenue (Actual)"].min()
        hist_max = historical_df_dep["Revenue (Actual)"].max()

        historical_summary = f"""

HISTORICAL DATA SUMMARY (Past 2 Years for {department.upper()}):
Average Actual Revenue: ${hist_avg:,.0f}
Actual Revenue Range: ${hist_min:,.0f} - ${hist_max:,.0f}
"""

    prompt = f""""Analyze this forecast data and provide concise business insights for the {department} department.
    Justify the peak or unexpected trends by comparing the forecast data to the actual values of the past 2 years of historical data provided.
    If an abnormality of trend is noticed on a certain date, provide necessary information, skim through the historical context and breifly explain the factors that might justify this prediction.
    \n\n{data_summary}\n{historical_summary}\nProvide insights in this format:\nKey Findings:\n👉 [Insight 1 with specific values, justified against historical data]\n👉 [Insight 2 with specific values, justified, explained the resason of abnormality]\n\nConclusion:\n[2-3 sentence summary of the key findings and their implications based on historical context.]\n\n
    RULES:\n• Use exact values from the data.\n• MAXIMUM 90 WORDS for Key Findings - count and stop at 90.\n• Use arrows (👉) for Key Findings.\n• Each arrow item must be on a separate line.\n• EXACTLY 2 insights in Key Findings.\n• Be extremely brief and direct.\n• Focus on key trends only.\n• Output must be plain text only — no Markdown, no LaTeX, no styled fonts.\n
    • The Conclusion must be a concise summary (2-3 sentences)."""
    return prompt


def _format_llm_output(insights: str, department: str) -> str:
    """Format the LLM output as HTML."""
    insights = re.sub(r"(\\*\*|_|_|\\*)", "", insights)
    insights = re.sub(r"<[^>]*>", "", insights)

    formatted_insights = (
        f'<div style="font-family: sans-serif; font-size: 1rem; line-height: 1.5;">'
    )
    formatted_insights += f'<h4 style="color: #e6e9ef;">Forecast Insights for {department} Department:</h4>'

    lines = insights.split("\n")
    key_findings_section, conclusion_section = [], []
    in_key_findings, in_conclusion = False, False

    for line in lines:
        line = line.strip()
        if line.startswith("Key Findings:"):
            in_key_findings, in_conclusion = True, False
            key_findings_section.append(f'<p style="font-weight: bold;">{line}</p>')
        elif line.startswith("Conclusion:"):
            in_key_findings, in_conclusion = False, True
            conclusion_section.append(
                f'<p style="font-weight: bold; margin-top: 10px;">{line}</p>'
            )
        elif in_key_findings and line.startswith("👉"):
            key_findings_section.append(f'<p style="margin-left: 20px;">{line}</p>')
        elif in_conclusion and line:
            conclusion_section.append(f"<p>{line}</p>")

    formatted_insights += "".join(key_findings_section)
    formatted_insights += "".join(conclusion_section)
    formatted_insights += "</div>"

    return formatted_insights


# Generate LLM-powered insights about the forecast data in forecast tab
def generate_llm_forecast_insights(
    forecast_data: str,
    department: str,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    max_retries: int = 3,
) -> str:
    """
    Generate LLM-powered insights about the forecast data with validation and retries.

    Args:
        forecast_data (str): Raw forecast text containing date-value pairs.
        department (str): Department name for the insights.
        start_date (Optional[pd.Timestamp]): Start date for filtering forecast data.
        end_date (Optional[pd.Timestamp]): End date for filtering forecast data.
        max_retries (int): Maximum number of retries for generating valid insights.

    Returns:
        str: LLM-generated insights about the forecast.
    """
    try:
        from services.chat_services import run_chatbot_job

        df = parse_forecast_data(forecast_data)
        if df is None or df.empty:
            return "Unable to generate insights: No forecast data available."

        if start_date and end_date:
            df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

        if df.empty:
            return "No forecast data available for the selected date range to generate insights."

        historical_df_dep = _get_historical_data(department, df["Date"].min())

        prompt = _prepare_llm_prompt(department, df, historical_df_dep)

        for attempt in range(max_retries):
            llm_response = run_chatbot_job(prompt)

            if isinstance(llm_response, dict) and "generated_text" in llm_response:
                insights = llm_response["generated_text"]
            else:
                insights = str(llm_response)

            if _validate_llm_output(insights):
                return _format_llm_output(insights, department)

        return "Error: Unable to generate valid insights after multiple attempts."

    except Exception as e:
        return f"Error generating LLM insights: {str(e)}"


# generate insights for chatbot AI assistant
def generate_chatbot_forecast_insights(
    forecast_data: str, department: str, max_retries: int = 3
) -> str:
    try:
        from services.chat_services import run_chatbot_job

        df = parse_forecast_data(forecast_data)
        if df is None or df.empty:
            return "Unable to generate insights: No forecast data available."

        if df.empty:
            return "No forecast data available for the selected date range to generate insights."

        forecast_values = df["Value"].values
        min_value, max_value, avg_value = (
            forecast_values.min(),
            forecast_values.max(),
            forecast_values.mean(),
        )
        trend = (
            (forecast_values[-1] - forecast_values[0]) / forecast_values[0] * 100
            if forecast_values[0] > 0
            else 0
        )
        volatility = forecast_values.std()
        volatility_pct = (volatility / avg_value * 100) if avg_value > 0 else 0

        peak_idx, trough_idx = forecast_values.argmax(), forecast_values.argmin()
        peak_date, trough_date = df.iloc[peak_idx]["Date"], df.iloc[trough_idx]["Date"]

        data_summary = f"""FORECAST DATA FOR {department.upper()} DEPARTMENT:
Forecast Period: {len(df)} days
Average Value: ${avg_value:,.0f}
Range: ${min_value:,.0f} - ${max_value:,.0f}
Trend: {trend:+.1f}% change
Volatility: {volatility_pct:.1f}%
Peak: ${max_value:,.0f} on {peak_date.strftime('%Y-%m-%d')}
Lowest: ${min_value:,.0f} on {trough_date.strftime('%Y-%m-%d')}

Sample Forecast Values:
{df.head(10).to_string(index=False)}

Recent Values:
{df.tail(5).to_string(index=False)}"""

        prompt = f"""Analyze this forecast data and provide concise business insights for the {department} department, justify the insights as per{data_summary} provide breif explanation for the peak or unexpected trends.

Provide insights in this format:
Key Findings:
👉 [Insight 1 with specific values, provide justification]
👉 [Insight 2 with specific values, provide possible cause]

Conclusion:
[2-3 sentence summary of the key findings and their implications.]

RULES:
• Use exact values from the data.
• MAXIMUM 100 WORDS for Key Findings - count and stop at 100.
• Use arrows (👉) for Key Findings.
• Each arrow item must be on a separate line.
• EXACTLY 3 insights in Key Findings.
• Be extremely brief and direct.
• Focus on key trends only.
• Output must be plain text only — no Markdown, no LaTeX, no styled fonts.
• The Conclusion must be a concise summary (2-3 sentences)."""

        for attempt in range(max_retries):
            llm_response = run_chatbot_job(prompt)

            if isinstance(llm_response, dict) and "generated_text" in llm_response:
                insights = llm_response["generated_text"]
            else:
                insights = str(llm_response)
                # insights = _format_llm_output(insights, department)

            if _validate_llm_output(insights):
                return _format_llm_output(insights, department)

        return "Error: Unable to generate valid insights after multiple attempts."
    except Exception as e:
        return f"Error generating LLM insights: {str(e)}"
