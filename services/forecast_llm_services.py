import requests
import time
import pandas as pd
import numpy as np
from typing import Dict
from .data_loader_service import get_data_loader

API_KEY = "rpa_KN3HAWGAIXJVZPKFL7WD5JV8XYIZW27LWYZC2RYZ1wthhi"
ENDPOINT_ID = "lkbk4plvvt0vah"
BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def run_forecast_job(prompt, sampling_params=None):
    """
    Submit a job to the Forecasting RunPod serverless endpoint.
    
    Args:
        prompt (str): Forecasting query or request
        sampling_params (dict): Optional dict for temperature, max_tokens, etc.
    """
    data = {
        "input": {
            "prompt": prompt,
            "application": "Forecasting"
        }
    }

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
            print("Job failed:", status_json)
            return None
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
            ap = latest.get('Accounts Payable (AP)', 0)
            ar = latest.get('Accounts Receivable (AR)', 0)
            
            # Simple trend calculation
            if len(raw_df) > 1:
                prev = raw_df.iloc[-2]
                ap_trend = ((ap - prev.get('Accounts Payable (AP)', 0)) / max(prev.get('Accounts Payable (AP)', 1), 1)) * 100
                ar_trend = ((ar - prev.get('Accounts Receivable (AR)', 0)) / max(prev.get('Accounts Receivable (AR)', 1), 1)) * 100
            else:
                ap_trend = 0
                ar_trend = 0
            
            return {
                "payables": ap,
                "receivables": ar,
                "payables_trend": ap_trend,
                "receivables_trend": ar_trend,
                "net_position": ar - ap
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
            
            # Get recent revenue data
            revenue_data = raw_df['Revenue (Actual)'].tail(6).values
            
            if len(revenue_data) < 2:
                return {"error": "Insufficient data"}
            
            # Simple linear trend forecast
            x = np.arange(len(revenue_data))
            coeffs = np.polyfit(x, revenue_data, 1)
            
            # Forecast next 3 months
            next_months = np.arange(len(revenue_data), len(revenue_data) + 3)
            forecast = np.polyval(coeffs, next_months)
            
            current_revenue = revenue_data[-1]
            next_month_revenue = forecast[0]
            growth_rate = ((next_month_revenue - current_revenue) / current_revenue) * 100
            
            return {
                "current_revenue": current_revenue,
                "next_month_forecast": next_month_revenue,
                "growth_rate": growth_rate,
                "forecast_months": forecast.tolist()
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
            
            # Get recent cash flow data
            cash_balance = raw_df['Cash Balance'].tail(6).values
            cash_outflows = raw_df['Cash Outflows'].tail(6).values
            
            if len(cash_balance) < 2:
                return {"error": "Insufficient data"}
            
            # Calculate burn rate
            avg_monthly_burn = np.mean(cash_outflows) * 30
            current_cash = cash_balance[-1]
            runway_months = current_cash / avg_monthly_burn if avg_monthly_burn > 0 else 0
            
            # Simple forecast
            next_month_cash = current_cash - avg_monthly_burn
            
            return {
                "current_cash": current_cash,
                "monthly_burn": avg_monthly_burn,
                "runway_months": runway_months,
                "next_month_forecast": next_month_cash
            }
        except Exception as e:
            return {"error": str(e)}
