import streamlit as st
import pandas as pd
import re
from typing import Optional

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
        lines = forecast_text.strip().split('\n')
        csv_lines = []
        
        for line in lines:
            # Skip header lines that don't contain date-value pairs
            if ',' in line and re.match(r'\d{4}-\d{2}-\d{2}', line):
                csv_lines.append(line)
        
        if csv_lines:
            # Parse CSV format
            df = pd.read_csv(pd.io.common.StringIO('\n'.join(csv_lines)), names=['Date', 'Value'])
            df['Date'] = pd.to_datetime(df['Date'])
            df['Value'] = df['Value'].astype(float)
            return df
        
        # Fallback to regex pattern for space-separated format (old format)
        forecast_pattern = r'(\d{4}-\d{2}-\d{2})\s+(\d+\.\d+)'
        matches = re.findall(forecast_pattern, forecast_text)
        
        if matches:
            # Create DataFrame
            df = pd.DataFrame(matches, columns=['Date', 'Value'])
            df['Date'] = pd.to_datetime(df['Date'])
            df['Value'] = df['Value'].astype(float)
            return df
        return None
    except Exception as e:
        print(f"Error parsing forecast data: {e}")
        return None

def create_forecast_chart(forecast_data: str, department: str, chart_height: int = 200) -> bool:
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
                df.set_index('Date')['Value'],
                use_container_width=True,
                height=chart_height
            )
            
            # Dynamic time range based on actual forecast data
            start_date = df['Date'].min().strftime('%b %d, %Y')
            end_date = df['Date'].max().strftime('%b %d, %Y')
            st.caption(f"Forecast for {department} Department - {start_date} to {end_date}")
            return True
        return False
    except Exception as e:
        st.error(f"Error creating chart: {e}")
        return False





def create_forecast_chart_with_plotly(forecast_data: str, department: str, chart_height: int = 400, start_date: Optional[pd.Timestamp] = None, end_date: Optional[pd.Timestamp] = None):
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
                df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
            
            if df.empty:
                st.warning("No forecast data available for the selected date range.")
                return None

            # Create Plotly line chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['Date'],
                y=df['Value'],
                mode='lines+markers',
                name='Forecast',
                line=dict(color='#e74c3c', width=3),
                marker=dict(size=6)
            ))
            
            # Dynamic time range for title
            chart_start_date = df['Date'].min().strftime('%b %d, %Y')
            chart_end_date = df['Date'].max().strftime('%b %d, %Y')
            
            # Apply consistent theme
            fig.update_layout(
                template='plotly_dark',
                height=chart_height,
                title=f'Revenue Forecast: {department} Department ({chart_start_date} to {chart_end_date})',
                xaxis_title='Date',
                yaxis_title='Revenue ($)',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=40, r=20, t=50, b=40),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            
            fig.update_xaxes(
                gridcolor='rgba(255,255,255,0.08)',
                tickformat='%b %d, %Y',
                tickangle=45,
                nticks=8
            )
            fig.update_yaxes(gridcolor='rgba(255,255,255,0.08)')
            
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

def generate_llm_forecast_insights(forecast_data: str, department: str, start_date: Optional[pd.Timestamp] = None, end_date: Optional[pd.Timestamp] = None, max_retries: int = 3) -> str:
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
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        
        if df.empty:
            return "No forecast data available for the selected date range to generate insights."

        forecast_values = df['Value'].values
        min_value, max_value, avg_value = forecast_values.min(), forecast_values.max(), forecast_values.mean()
        trend = (forecast_values[-1] - forecast_values[0]) / forecast_values[0] * 100 if forecast_values[0] > 0 else 0
        volatility = forecast_values.std()
        volatility_pct = (volatility / avg_value * 100) if avg_value > 0 else 0
        
        peak_idx, trough_idx = forecast_values.argmax(), forecast_values.argmin()
        peak_date, trough_date = df.iloc[peak_idx]['Date'], df.iloc[trough_idx]['Date']
        
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

        prompt = f"""Analyze this forecast data and provide concise business insights for the {department} department.

{data_summary}

Provide insights in this format:
Key Findings:
👉 [Insight 1 with specific values]
👉 [Insight 2 with specific values]

Conclusion:
[1-2 sentence summary of the key findings and their implications.]

RULES:
• Use exact values from the data.
• CRITICAL: NO MARKDOWN FORMATTING - No asterisks (*), underscores (_), backticks (`), or any special characters for formatting.
• NO BOLD, ITALICS, OR SPECIAL FORMATTING - Use plain text only.
• MAXIMUM 50 WORDS for Key Findings - count and stop at 50.
• Use arrows (👉) for Key Findings.
• Each arrow item must be on a separate line.
• EXACTLY 2 insights in Key Findings.
• Be extremely brief and direct.
• Focus on key trends only.
• Output must be plain text only — no Markdown, no LaTeX, no styled fonts, no special characters.
• The Conclusion must be a concise summary (1-2 sentences).
• IMPORTANT: If you use any formatting characters, the response will be rejected."""

        for attempt in range(max_retries):
            llm_response = run_chatbot_job(prompt)
            
            if isinstance(llm_response, dict) and 'generated_text' in llm_response:
                insights = llm_response['generated_text']
            else:
                insights = str(llm_response)
            
            if _validate_llm_output(insights):
                # Remove all markdown formatting
                insights = re.sub(r'\*\*([^*]+)\*\*', r'\1', insights)  # Remove bold
                insights = re.sub(r'\*([^*]+)\*', r'\1', insights)      # Remove italics
                insights = re.sub(r'_([^_]+)_', r'\1', insights)        # Remove italics
                insights = re.sub(r'`([^`]+)`', r'\1', insights)        # Remove code
                insights = re.sub(r'#+\s*', '', insights)               # Remove headers
                insights = re.sub(r'<[^>]*>', '', insights)             # Remove HTML tags
                insights = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', insights)  # Remove links
                insights = re.sub(r'[`*_#]', '', insights)              # Remove any remaining formatting chars

                formatted_insights = f"<div style=\"font-family: sans-serif; font-size: 1rem; line-height: 1.5;\">"
                formatted_insights += f"<h4 style=\"color: #e6e9ef;\">Forecast Insights for {department} Department:</h4>"
                
                lines = insights.split('\n')
                key_findings_section, conclusion_section = [], []
                in_key_findings, in_conclusion = False, False

                for line in lines:
                    line = line.strip()
                    if line.startswith("Key Findings:"):
                        in_key_findings, in_conclusion = True, False
                        key_findings_section.append(f"<p style=\"font-weight: bold;\">{line}</p>")
                    elif line.startswith("Conclusion:"):
                        in_key_findings, in_conclusion = False, True
                        conclusion_section.append(f"<p style=\"font-weight: bold; margin-top: 10px;\">{line}</p>")
                    elif in_key_findings and line.startswith("👉"):
                        key_findings_section.append(f"<p style=\"margin-left: 20px;\">{line}</p>")
                    elif in_conclusion and line:
                        conclusion_section.append(f"<p>{line}</p>")
                
                formatted_insights += "".join(key_findings_section)
                formatted_insights += "".join(conclusion_section)
                formatted_insights += "</div>"
                
                return formatted_insights
        
        return "Error: Unable to generate valid insights after multiple attempts."
        
    except Exception as e:
        return f"Error generating LLM insights: {str(e)}"


def generate_forecast_insights(forecast_data: str, department: str, start_date: Optional[pd.Timestamp] = None, end_date: Optional[pd.Timestamp] = None) -> str:
    """
    Generate insights about the forecast data using LLM with retries.
    
    Args:
        forecast_data (str): Raw forecast text containing date-value pairs.
        department (str): Department name for the insights.
        start_date (Optional[pd.Timestamp]): Start date for filtering forecast data.
        end_date (Optional[pd.Timestamp]): End date for filtering forecast data.
        
    Returns:
        str: LLM-generated insights about the forecast.
    """
    return generate_llm_forecast_insights(forecast_data, department, start_date, end_date, max_retries=3)


def display_forecast_chart(forecast_data: str, department: str, chart_type: str = "streamlit", chart_height: int = 200, start_date: Optional[pd.Timestamp] = None, end_date: Optional[pd.Timestamp] = None) -> bool:
    """Display forecast chart based on the specified chart type."""
    if chart_type == "streamlit":
        return create_forecast_chart(forecast_data, department, chart_height)
    elif chart_type == "plotly":
        fig = create_forecast_chart_with_plotly(forecast_data, department, chart_height, start_date, end_date)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            return True
        return False
    else:
        st.error(f"Unknown chart type: {chart_type}")
        return False