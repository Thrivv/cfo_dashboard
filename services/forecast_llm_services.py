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
        """Get monthly payables vs receivables forecast with enhanced trend analysis."""
        try:
            data_loader = get_data_loader()
            raw_df = data_loader.get_raw_data()
            
            if raw_df is None or raw_df.empty:
                return {"error": "No data available"}
            
            # Get latest data
            latest = raw_df.iloc[-1]
            ap = latest.get('Accounts Payable (AP)', 0)
            ar = latest.get('Accounts Receivable (AR)', 0)
            
            # Enhanced trend calculation with confidence
            if len(raw_df) >= 3:
                # 3-month rolling trends
                ap_data = raw_df['Accounts Payable (AP)'].tail(3).values
                ar_data = raw_df['Accounts Receivable (AR)'].tail(3).values
                
                # Calculate trends and confidence
                ap_trend = ((ap_data[-1] - ap_data[0]) / max(ap_data[0], 1)) * 100
                ar_trend = ((ar_data[-1] - ar_data[0]) / max(ar_data[0], 1)) * 100
                
                # Calculate volatility (confidence indicator)
                ap_volatility = np.std(ap_data) / np.mean(ap_data) * 100
                ar_volatility = np.std(ar_data) / np.mean(ar_data) * 100
                
                # Trend strength (0-100)
                ap_trend_strength = max(0, 100 - ap_volatility)
                ar_trend_strength = max(0, 100 - ar_volatility)
            else:
                ap_trend = ar_trend = 0
                ap_trend_strength = ar_trend_strength = 50
            
            return {
                "payables": ap,
                "receivables": ar,
                "payables_trend": ap_trend,
                "receivables_trend": ar_trend,
                "net_position": ar - ap,
                "ap_trend_strength": ap_trend_strength,
                "ar_trend_strength": ar_trend_strength
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_revenue_forecast_preview(self) -> Dict:
        """Get revenue forecast preview with confidence intervals and multiple trends."""
        try:
            data_loader = get_data_loader()
            raw_df = data_loader.get_raw_data()
            
            if raw_df is None or raw_df.empty:
                return {"error": "No data available"}
            
            # Get recent revenue data
            revenue_data = raw_df['Revenue (Actual)'].tail(6).values
            
            if len(revenue_data) < 3:
                return {"error": "Insufficient data"}
            
            # Enhanced forecasting with confidence intervals
            x = np.arange(len(revenue_data))
            
            # Linear trend with confidence intervals
            coeffs = np.polyfit(x, revenue_data, 1)
            y_pred = np.polyval(coeffs, x)
            residuals = revenue_data - y_pred
            mse = np.mean(residuals**2)
            std_error = np.sqrt(mse)
            
            # Calculate R-squared
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((revenue_data - np.mean(revenue_data))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # Forecast next 3 months with confidence intervals
            next_months = np.arange(len(revenue_data), len(revenue_data) + 3)
            forecast = np.polyval(coeffs, next_months)
            
            # Confidence intervals (95%)
            confidence_interval = 1.96 * std_error
            forecast_upper = forecast + confidence_interval
            forecast_lower = forecast - confidence_interval
            
            current_revenue = revenue_data[-1]
            next_month_revenue = forecast[0]
            growth_rate = ((next_month_revenue - current_revenue) / current_revenue) * 100
            
            # Trend strength based on R-squared
            trend_strength = min(100, max(0, r_squared * 100))
            
            return {
                "current_revenue": current_revenue,
                "next_month_forecast": next_month_revenue,
                "growth_rate": growth_rate,
                "forecast_months": forecast.tolist(),
                "confidence_upper": forecast_upper.tolist(),
                "confidence_lower": forecast_lower.tolist(),
                "r_squared": r_squared,
                "trend_strength": trend_strength
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_cash_flow_forecast_preview(self) -> Dict:
        """Get cash flow forecast preview with scenario analysis and confidence intervals."""
        try:
            data_loader = get_data_loader()
            raw_df = data_loader.get_raw_data()
            
            if raw_df is None or raw_df.empty:
                return {"error": "No data available"}
            
            # Get recent cash flow data
            cash_balance = raw_df['Cash Balance'].tail(6).values
            cash_outflows = raw_df['Cash Outflows'].tail(6).values
            
            if len(cash_balance) < 3:
                return {"error": "Insufficient data"}
            
            # Enhanced burn rate analysis with confidence
            avg_monthly_burn = np.mean(cash_outflows)
            burn_std = np.std(cash_outflows)
            current_cash = cash_balance[-1]
            
            # Calculate runway with confidence intervals
            runway_months = current_cash / avg_monthly_burn if avg_monthly_burn > 0 else 0
            
            # Scenario analysis
            best_case_burn = avg_monthly_burn - burn_std  # Lower burn
            worst_case_burn = avg_monthly_burn + burn_std  # Higher burn
            
            best_case_runway = current_cash / best_case_burn if best_case_burn > 0 else 0
            worst_case_runway = current_cash / worst_case_burn if worst_case_burn > 0 else 0
            
            # Forecasts
            next_month_cash = current_cash - avg_monthly_burn
            best_case_cash = current_cash - best_case_burn
            worst_case_cash = current_cash - worst_case_burn
            
            # Burn rate trend
            burn_trend = ((cash_outflows[-1] - cash_outflows[0]) / max(cash_outflows[0], 1)) * 100
            
            return {
                "current_cash": current_cash,
                "monthly_burn": avg_monthly_burn,
                "runway_months": runway_months,
                "next_month_forecast": next_month_cash,
                "best_case_runway": best_case_runway,
                "worst_case_runway": worst_case_runway,
                "best_case_cash": best_case_cash,
                "worst_case_cash": worst_case_cash,
                "burn_trend": burn_trend,
                "burn_volatility": (burn_std / avg_monthly_burn) * 100 if avg_monthly_burn > 0 else 0
            }
        except Exception as e:
            return {"error": str(e)}
