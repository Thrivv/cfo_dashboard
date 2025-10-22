"""Budgeting and Forecasting page with revenue forecasting capabilities."""

from datetime import datetime, date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from services.forecast_services import (
    create_forecast_chart_with_plotly,
    run_forecast_job,
)
from utils import get_data_loader


def _apply_plot_theme(
    fig: go.Figure, height: int = 400, title: str | None = None
) -> go.Figure:
    """Apply consistent theme to plots."""
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=50 if title else 20, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        title=dict(text=title) if title else None,
    )
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.08)",
        tickformat="%b %d, %Y",
        tickangle=45,
        nticks=8,
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    return fig


def render():
    """Redesigned Forecasting page with 2-column layout for better visualization."""
    st.markdown(
        """
    <style>
      .app-surface {background: radial-gradient(1200px 600px at 10% 0%, #0a0a12 0%, #05050a 45%, #04040a 100%);}
      .panel {background: linear-gradient(180deg, rgba(13,13,23,0.92), rgba(6,6,12,0.98)); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 14px 16px; margin-bottom: 16px;}
      .section-title {color: #e6e9ef; font-size: 1.05rem; font-weight: 700; margin: 0 0 8px;}
      .kpi-grid {display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;}
      .kpi {background: linear-gradient(180deg, rgba(18,18,30,0.95), rgba(12,12,22,0.98)); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 14px;}
      .kpi .label {color: #9aa3ab; font-size: .85rem;}
      .kpi .value {color: #e9ecef; font-size: 1.25rem; font-weight: 700; margin-top: 2px;}
      .chart-container {background: linear-gradient(180deg, rgba(18,18,30,0.95), rgba(12,12,22,0.98)); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 16px; margin-bottom: 16px;}
    </style>
    <script>
      const root = window.parent?.document?.querySelector('section.main');
      if (root) { root.classList.add('app-surface'); }
    </script>
    """,
        unsafe_allow_html=True,
    )

    # Initialize forecast service
    if "forecast_service_initialized" not in st.session_state:
        st.session_state.forecast_service_initialized = True

    # Get data
    data_loader = get_data_loader()
    raw_df = data_loader.get_raw_data()

    if raw_df is not None and not raw_df.empty:
        # Page Header
        st.markdown(
            '<div class="panel"><div class="section-title">Revenue Forecasting</div>',
            unsafe_allow_html=True,
        )

        #Department selection for all charts
        departments = [
            "Finance",
            "Sales",
            "Marketing",
            "IT",
            "HR",
            "Operations",
            "All Departments",
        ]
        selected_dept = st.selectbox(
            "Select Department for Analysis", departments, key="main_dept_selector"
        )

        st.markdown("</div>", unsafe_allow_html=True)

       # Two Column Layout for Charts
        col1, col2 = st.columns(2)

        with col1:
            # Department Spend Analysis - Text and Metrics
            st.markdown(
                '<div class="chart-container"><div class="section-title">Department Spend Analysis</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                "**Purpose:** Track department spending patterns and forecast future expenses using 2 years historical data.<br/>**Insight:** Compare spending trends across departments and predict budget requirements for better resource allocation.",
                unsafe_allow_html=True,
            )

            if selected_dept != "All Departments":
                dept_data = raw_df[
                    raw_df["Business Unit / Department"] == selected_dept
                ]
                if not dept_data.empty:
                    # Calculate department spend metrics
                    latest = dept_data.iloc[-1]
                    opex = latest.get("Operating Expenses (OPEX)", 0)
                    cogs = latest.get("Cost of Goods Sold (COGS)", 0)
                    total_spend = opex + cogs

                    # Simple trend calculation
                    if len(dept_data) > 1:
                        prev = dept_data.iloc[-2]
                        prev_spend = prev.get(
                            "Operating Expenses (OPEX)", 0
                        ) + prev.get("Cost of Goods Sold (COGS)", 0)
                        spend_trend = (
                            (total_spend - prev_spend) / max(prev_spend, 1)
                        ) * 100
                    else:
                        spend_trend = 0

                    # Display metrics in compact format
                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric(
                            "Total Spend",
                            f"${total_spend:,.0f}",
                            f"{spend_trend:+.1f}%",
                        )
                    with metric_col2:
                        st.metric("OPEX", f"${opex:,.0f}")
                else:
                    st.warning(f"No data available for {selected_dept} department.")
            else:
                # All departments analysis
                dept_spend = (
                    raw_df.groupby("Business Unit / Department")
                    .agg(
                        {
                            "Operating Expenses (OPEX)": "sum",
                            "Cost of Goods Sold (COGS)": "sum",
                        }
                    )
                    .reset_index()
                )

                dept_spend["Total Spend"] = (
                    dept_spend["Operating Expenses (OPEX)"]
                    + dept_spend["Cost of Goods Sold (COGS)"]
                )

                # Display summary metrics
                total_all_spend = dept_spend["Total Spend"].sum()
                st.metric("Total Company Spend", f"${total_all_spend:,.0f}")
                st.metric("Departments", f"{len(dept_spend)}")

            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            # Department Spend Analysis - Chart
            if selected_dept != "All Departments":
                dept_data = raw_df[
                    raw_df["Business Unit / Department"] == selected_dept
                ]
                if not dept_data.empty and len(dept_data) >= 3:
                    spend_history = (
                        dept_data["Operating Expenses (OPEX)"].tail(12).values
                    )
                    dates = pd.date_range(
                        end=datetime.now(), periods=len(spend_history), freq="ME"
                    )

                    # Simple linear forecast
                    import numpy as np

                    x = np.arange(len(spend_history))
                    coeffs = np.polyfit(x, spend_history, 1)
                    forecast_periods = np.arange(
                        len(spend_history), len(spend_history) + 3
                    )
                    forecast_values = np.polyval(coeffs, forecast_periods)

                    # Create chart
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=dates,
                            y=spend_history,
                            mode="lines+markers",
                            name="Historical",
                            line=dict(color="#3498db"),
                        )
                    )

                    forecast_dates = pd.date_range(
                        start=dates[-1] + timedelta(days=30), periods=3, freq="ME"
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=forecast_dates,
                            y=forecast_values,
                            mode="lines+markers",
                            name="Forecast",
                            line=dict(color="#e74c3c", dash="dash"),
                        )
                    )

                    fig = _apply_plot_theme(
                        fig, height=300, title=f"{selected_dept} Spend Forecast"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                # All departments analysis chart
                dept_spend = (
                    raw_df.groupby("Business Unit / Department")
                    .agg(
                        {
                            "Operating Expenses (OPEX)": "sum",
                            "Cost of Goods Sold (COGS)": "sum",
                        }
                    )
                    .reset_index()
                )

                dept_spend["Total Spend"] = (
                    dept_spend["Operating Expenses (OPEX)"]
                    + dept_spend["Cost of Goods Sold (COGS)"]
                )

                # Department spend comparison chart
                fig = px.bar(
                    dept_spend,
                    x="Business Unit / Department",
                    y="Total Spend",
                    title="Total Spend by Department",
                    color="Total Spend",
                    color_continuous_scale="Viridis",
                )
                fig = _apply_plot_theme(
                    fig, height=300, title="Department Spend Comparison"
                )
                st.plotly_chart(fig, use_container_width=True)

        # AI Forecasting Section - Full Width
        st.markdown(
            '<div class="panel"><div class="section-title">Revenue Forecasting with LagLlama</div>',
            unsafe_allow_html=True,
        )

        # AI Controls
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            # AI-specific department selector
            ai_departments = ["Finance","Sales", "Marketing", "IT", "HR", "Operations"]
            ai_selected_dept = st.selectbox(
                "Department", ai_departments, key="ai_dept_selector"
            )

        with col2:
            display_start_date = st.date_input(
                "Start Date",
                value=pd.to_datetime(date.today()),
                min_value=pd.to_datetime(date.today()),
                max_value=pd.to_datetime(datetime.today() + timedelta(days=30 * 13)),
                key="forecast_display_start_date",
            )

        with col3:
            display_end_date = st.date_input(
                "End Date",
                value=pd.to_datetime(datetime.today() + timedelta(days=30)),
                min_value=pd.to_datetime(date.today()),
                max_value=pd.to_datetime(datetime.today() + timedelta(days=30 * 13)),
                key="forecast_display_end_date",
            )

        with col4:
            st.write("")  # V-align
            st.write("")
            generate_button = st.button("Forecast", type="primary", key="ai_generate")

        spinner_placeholder = st.empty()

        if generate_button:
            with spinner_placeholder.container():
                st.markdown(
                    "<img src='https://i.gifer.com/origin/34/34338d26023e5515f6cc8969aa027bca.gif' width='50'> *Generating forecast...*",
                    unsafe_allow_html=True,
                )

            prompt = f"Generate revenue forecast for {ai_selected_dept} department for 13 months"
            result = run_forecast_job(prompt)
            if result:
                st.session_state.forecast_result = result
                st.rerun()

        # Ensure display_end_date is not before display_start_date
        if display_start_date > display_end_date:
            st.error("Error: Forecast end date cannot be before the start date.")
            display_start_date = datetime(2024, 12, 31).date()
            display_end_date = datetime(2025, 12, 26).date()

        # Display AI Results
        if "forecast_result" in st.session_state:
            st.markdown("### Revenue Forecast Results")

            # Extract forecast data from response
            forecast_data = st.session_state.forecast_result
            if isinstance(forecast_data, dict) and "forecast_data" in forecast_data:
                forecast_text = forecast_data["forecast_data"]
            else:
                forecast_text = str(forecast_data)

            # Show forecast insights
            from services.forecast_services import generate_llm_forecast_insights

            insights = generate_llm_forecast_insights(
                forecast_text,
                ai_selected_dept,
                pd.Timestamp(display_start_date),
                pd.Timestamp(display_end_date),
            )
            # st.markdown("#### Forecast Insights")
            st.markdown(insights, unsafe_allow_html=True)

            # Show forecast chart
            st.markdown("#### Forecast Chart")
            fig = create_forecast_chart_with_plotly(
                forecast_text,
                ai_selected_dept,
                chart_height=400,
                start_date=pd.Timestamp(
                    display_start_date
                ),  # Convert to Timestamp for graph_services
                end_date=pd.Timestamp(
                    display_end_date
                ),  # Convert to Timestamp for graph_services
            )
            if fig:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(
                    "No chartable forecast data found for the selected display range."
                )

            # Show raw output (minimal)
            with st.expander("Raw Forecast Data", expanded=False):
                st.text(forecast_text)

            if st.button("Clear Results", key="clear_results"):
                if "forecast_result" in st.session_state:
                    del st.session_state.forecast_result
                st.rerun()

        else:
            st.info(
                "Select a department, desired date range and click 'Forecast' to generate revenue forecast."
            )

        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning("No financial data available. Please ensure data is loaded.")