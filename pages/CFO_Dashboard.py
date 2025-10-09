import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime
from utils import get_data_loader
from components.alert_card import render_cfo_alerts_section
from components.data_filter import apply_filters, get_filter_summary, validate_filters
from services.forecast_services import ForecastPreviewService


def _clear_cache():
    """Clear cached data when filters change."""
    cache_keys = [
        key
        for key in st.session_state.keys()
        if key.startswith(
            ("filtered_data_", "profit_trend_", "inventory_trend_", "capex_trend_")
        )
    ]
    for key in cache_keys:
        del st.session_state[key]


def _apply_plot_theme(
    fig: go.Figure, height: int = 340, title: str | None = None
) -> go.Figure:
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
        tickformat="%b %d, %Y",  # Format dates as "Jan 15, 2024"
        tickangle=45,  # Rotate date labels for better readability
        nticks=8,  # Limit number of ticks for cleaner display
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    return fig


def render():
    """Render CFO Dashboard with integrated Home page content."""

    st.markdown(
        """
    <style>
      .app-surface {background: radial-gradient(1200px 600px at 10% 0%, #0a0a12 0%, #05050a 45%, #04040a 100%);}    
      .panel {background: linear-gradient(180deg, rgba(13,13,23,0.92), rgba(6,6,12,0.98)); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 14px 16px;}
      .section-title {color: #e6e9ef; font-size: 1.05rem; font-weight: 700; margin: 0 0 8px;}
      .kpi-grid {display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;}
      .kpi-grid.cols-3 {grid-template-columns: repeat(3, 1fr);} 
      .kpi-grid.cols-4 {grid-template-columns: repeat(4, 1fr);} 
      .kpi-grid.cols-5 {grid-template-columns: repeat(5, 1fr);} 
      .kpi-grid.cols-6 {grid-template-columns: repeat(6, 1fr);} 
      .kpi {background: linear-gradient(180deg, rgba(18,18,30,0.95), rgba(12,12,22,0.98)); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 14px;}
      .kpi .label {color: #9aa3ab; font-size: .85rem;}
      .kpi .value {color: #e9ecef; font-size: 1.25rem; font-weight: 700; margin-top: 2px;}
      .footer { background: #06060d; padding: 1rem; border-radius: 10px; text-align: center; margin-top: 1.5rem; color: #889096; border: 1px solid rgba(255,255,255,0.06); }
      
    </style>
    <script>
      const root = window.parent?.document?.querySelector('section.main');
      if (root) { root.classList.add('app-surface'); }
    </script>
    """,
        unsafe_allow_html=True,
    )

    # Add loading state
    with st.spinner("Loading CFO Dashboard..."):
        try:
            # Use centralized data loader for consistent data processing
            data_loader = get_data_loader()
            processed_df = data_loader.get_processed_data()
            raw_df = data_loader.get_raw_data()

            if (
                processed_df is not None
                and not processed_df.empty
                and raw_df is not None
            ):
                business_units = (
                    raw_df["Business Unit / Department"].unique().tolist()
                    if raw_df is not None
                    else []
                )

                if "cfo_filters" not in st.session_state:
                    st.session_state.cfo_filters = validate_filters({})

                # Header Section (Filters & Controls)
                f1, f2, f3, f4, f5 = st.columns([1, 1, 1, 1, 0.8])

                with f1:
                    selected_unit = st.selectbox(
                        "Business Unit",
                        ["All"] + business_units,
                        index=(["All"] + business_units).index(
                            st.session_state.cfo_filters["unit"]
                        ),
                        key="unit_filter",
                    )
                    if selected_unit != st.session_state.cfo_filters["unit"]:
                        # Clear cache when unit changes
                        _clear_cache()
                        st.session_state.cfo_filters["unit"] = selected_unit

                with f2:
                    # Date range filter with automatic end date opening
                    if "start_date" not in st.session_state.cfo_filters:
                        st.session_state.cfo_filters["start_date"] = None
                    if "end_date" not in st.session_state.cfo_filters:
                        st.session_state.cfo_filters["end_date"] = None

                    # Start date selection
                    start_date = st.date_input(
                        "Start Date",
                        value=st.session_state.cfo_filters.get("start_date"),
                        help="Select start date for analysis",
                        key="start_date_filter",
                    )

                    # If start date is selected, automatically show end date input
                    if start_date:
                        end_date = st.date_input(
                            "End Date",
                            value=st.session_state.cfo_filters.get("end_date"),
                            help="Select end date for analysis",
                            key="end_date_filter",
                        )
                    else:
                        end_date = None

                    # Update session state and clear cache if dates changed
                    if start_date != st.session_state.cfo_filters.get(
                        "start_date"
                    ) or end_date != st.session_state.cfo_filters.get("end_date"):

                        # Clear cache when dates change
                        _clear_cache()

                        st.session_state.cfo_filters["start_date"] = start_date
                        st.session_state.cfo_filters["end_date"] = end_date

                        # Convert to date_range format for compatibility
                        if start_date and end_date:
                            st.session_state.cfo_filters["date_range"] = [
                                start_date,
                                end_date,
                            ]
                        elif start_date:
                            st.session_state.cfo_filters["date_range"] = [
                                start_date,
                                start_date,
                            ]
                        else:
                            st.session_state.cfo_filters["date_range"] = None

                with f3:
                    # Period aggregation filter
                    period_options = ["Monthly", "Quarterly", "Yearly"]
                    current_period = st.session_state.cfo_filters.get(
                        "period", "Yearly"
                    )

                    selected_period = st.selectbox(
                        "Period",
                        period_options,
                        index=period_options.index(current_period),
                        help="Aggregate data by time period",
                        key="period_filter",
                    )

                    if selected_period != st.session_state.cfo_filters.get("period"):
                        # Clear cache when period changes
                        _clear_cache()
                        st.session_state.cfo_filters["period"] = selected_period

                with f4:
                    st.markdown(
                        "<div style='height:28px'></div>", unsafe_allow_html=True
                    )  # Spacing
                    if st.button(
                        "Clear Filter",
                        type="secondary",
                        use_container_width=True,
                        help="Reset all filters to default values",
                    ):
                        # Clear all cache when resetting filters
                        _clear_cache()
                        # Reset filters to defaults
                        st.session_state.cfo_filters = validate_filters({})
                        # Clear any UI-specific session state
                        if "unit_filter" in st.session_state:
                            del st.session_state["unit_filter"]
                        if "start_date_filter" in st.session_state:
                            del st.session_state["start_date_filter"]
                        if "end_date_filter" in st.session_state:
                            del st.session_state["end_date_filter"]
                        if "period_filter" in st.session_state:
                            del st.session_state["period_filter"]
                        st.rerun()

                with f5:
                    st.markdown(
                        "<div style='height:28px'></div>", unsafe_allow_html=True
                    )  # Spacing
                    if st.button("Alerts", type="primary", use_container_width=True):
                        st.session_state.show_alerts_only = True
                        st.rerun()

                if st.session_state.get("show_alerts_only", False):
                    # Apply filters for alerts view using processed data
                    filtered_df_for_alerts = apply_filters(
                        processed_df, st.session_state.cfo_filters
                    )
                    latest_raw_for_alerts = filtered_df_for_alerts.iloc[-1]

                    render_cfo_alerts_section(
                        latest_raw_for_alerts, filtered_df_for_alerts
                    )

                    if st.button(
                        "Back to Dashboard", type="secondary", use_container_width=True
                    ):
                        st.session_state.show_alerts_only = False
                        st.rerun()

                    return

                # Apply filtering system with caching (use processed data for better performance)
                filter_key = f"filtered_data_{hash(str(st.session_state.cfo_filters))}"
                if filter_key not in st.session_state:
                    filtered_df_result = apply_filters(
                        processed_df, st.session_state.cfo_filters
                    )
                    st.session_state[filter_key] = filtered_df_result
                filtered_df = st.session_state[filter_key]

                # Use filtered data for calculations
                latest_raw = filtered_df.iloc[-1]

                # Get alert metrics from filtered data
                cash_balance = latest_raw.get("Cash Balance", 0)
                debt_equity_ratio = latest_raw.get("Debt-to-Equity Ratio", 0)
                net_income = latest_raw.get("Net Income", 0)
                current_ratio = latest_raw.get("Current Ratio", 0)
                dso = latest_raw.get("Days Sales Outstanding (DSO)", 0)

                # Show filter summary
                filter_summary = get_filter_summary(
                    filtered_df, st.session_state.cfo_filters
                )
                if filter_summary["active_filters"]:
                    st.info(
                        f"Active Filters: {' | '.join(filter_summary['active_filters'])} | Showing {filter_summary['record_count']} records"
                    )

                # Show detailed sections by default (since we removed view filter)

                # Financial Performance Overview
                st.markdown(
                    '<div class="panel"><div class="section-title">Financial Performance Overview</div>',
                    unsafe_allow_html=True,
                )

                # Calculate aggregated values from filtered data
                revenue_actual = filtered_df["Revenue (Actual)"].sum()
                revenue_budget = filtered_df["Revenue (Budget / Forecast)"].sum()
                variance = (
                    ((revenue_actual - revenue_budget) / revenue_budget * 100)
                    if revenue_budget > 0
                    else 0
                )
                gross_profit = filtered_df["Gross Profit"].sum()
                net_income = filtered_df["Net Income"].sum()
                ebitda = filtered_df["EBITDA"].sum()
                st.markdown(
                    f"""
                    <div class="kpi-grid">
                      <div class="kpi"><div class="label">Revenue (Actual)</div><div class="value">${revenue_actual:,.0f}</div></div>
                      <div class="kpi"><div class="label">Revenue (Budget)</div><div class="value">${revenue_budget:,.0f} ({variance:+.1f}%)</div></div>
                      <div class="kpi"><div class="label">Gross Profit</div><div class="value">${gross_profit:,.0f} ({(gross_profit/revenue_actual*100) if revenue_actual > 0 else 0:.1f}%)</div></div>
                      <div class="kpi"><div class="label">Net Income</div><div class="value">${net_income:,.0f} ({(net_income/filtered_df['Equity'].sum()*100) if filtered_df['Equity'].sum() > 0 else 0:+.1f}%)</div></div>
                      <div class="kpi"><div class="label">EBITDA</div><div class="value">${ebitda:,.0f} ({(ebitda/revenue_actual*100) if revenue_actual > 0 else 0:.1f}%)</div></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

                # Forecast Previews Section
                st.markdown(
                    '<div class="panel"><div class="section-title">Forecast Previews</div>',
                    unsafe_allow_html=True,
                )

                # Initialize forecast service
                forecast_service = ForecastPreviewService()

                # Get forecast data
                payables_receivables = (
                    forecast_service.get_monthly_payables_vs_receivables()
                )
                revenue_forecast = forecast_service.get_revenue_forecast_preview()
                cash_flow_forecast = forecast_service.get_cash_flow_forecast_preview()

                # Display forecast previews
                col1, col2, col3 = st.columns(3)

                with col1:
                    if "error" not in payables_receivables:
                        ap = payables_receivables["payables"]
                        ar = payables_receivables["receivables"]
                        net_pos = payables_receivables["net_position"]
                        ap_trend = payables_receivables["payables_trend"]
                        ar_trend = payables_receivables["receivables_trend"]
                        ap_strength = payables_receivables.get("ap_trend_strength", 50)
                        ar_strength = payables_receivables.get("ar_trend_strength", 50)

                        st.markdown(
                            f"""
                        <div class="kpi">
                            <div class="label">Monthly Payables vs Receivables</div>
                            <div class="value">${net_pos:,.0f}</div>
                            <div style="font-size: 0.8rem; color: #9aa3ab; margin-top: 4px;">
                                AP: ${ap:,.0f} ({ap_trend:+.1f}%) [{ap_strength:.0f}/100]<br/>
                                AR: ${ar:,.0f} ({ar_trend:+.1f}%) [{ar_strength:.0f}/100]
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<div class="kpi"><div class="label">Payables vs Receivables</div><div class="value">N/A</div></div>',
                            unsafe_allow_html=True,
                        )

                with col2:
                    if "error" not in revenue_forecast:
                        current_rev = revenue_forecast["current_revenue"]
                        next_rev = revenue_forecast["next_month_forecast"]
                        growth = revenue_forecast["growth_rate"]
                        trend_strength = revenue_forecast.get("trend_strength", 50)
                        r_squared = revenue_forecast.get("r_squared", 0)

                        st.markdown(
                            f"""
                        <div class="kpi">
                            <div class="label">Revenue Forecast</div>
                            <div class="value">${next_rev:,.0f}</div>
                            <div style="font-size: 0.8rem; color: #9aa3ab; margin-top: 4px;">
                                Current: ${current_rev:,.0f}<br/>
                                Growth: {growth:+.1f}% [{trend_strength:.0f}/100]<br/>
                                R²: {r_squared:.2f}
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<div class="kpi"><div class="label">Revenue Forecast</div><div class="value">N/A</div></div>',
                            unsafe_allow_html=True,
                        )

                with col3:
                    if "error" not in cash_flow_forecast:
                        current_cash = cash_flow_forecast["current_cash"]
                        next_cash = cash_flow_forecast["next_month_forecast"]
                        runway = cash_flow_forecast["runway_months"]
                        best_runway = cash_flow_forecast.get("best_case_runway", runway)
                        worst_runway = cash_flow_forecast.get(
                            "worst_case_runway", runway
                        )
                        burn_trend = cash_flow_forecast.get("burn_trend", 0)

                        st.markdown(
                            f"""
                        <div class="kpi">
                            <div class="label">Cash Flow Forecast</div>
                            <div class="value">${next_cash:,.0f}</div>
                            <div style="font-size: 0.8rem; color: #9aa3ab; margin-top: 4px;">
                                Current: ${current_cash:,.0f}<br/>
                                Runway: {runway:.1f}m (Best: {best_runway:.1f}m)<br/>
                                Burn: {burn_trend:+.1f}%
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<div class="kpi"><div class="label">Cash Flow Forecast</div><div class="value">N/A</div></div>',
                            unsafe_allow_html=True,
                        )

                st.markdown("</div>", unsafe_allow_html=True)

                # Charts for Financial Performance with caching
                # Profitability Trend Chart (Revenue vs Forecast moved to Forecasting page)
                chart_key = f"profit_trend_{hash(str(st.session_state.cfo_filters))}"
                if chart_key not in st.session_state:
                    # Use processed data - Date column already exists and is properly formatted
                    profit_trend = filtered_df[
                        ["Date", "Gross Profit", "EBITDA", "Net Income"]
                    ].copy()

                    # If we have too many data points, sample them for better visualization
                    if len(profit_trend) > 50:
                        # Sample every nth record to get a reasonable number of points
                        step = len(profit_trend) // 50
                        profit_trend = profit_trend.iloc[::step]

                    st.session_state[chart_key] = profit_trend
                else:
                    profit_trend = st.session_state[chart_key]

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=profit_trend["Date"],
                        y=profit_trend["Gross Profit"],
                        mode="lines",
                        name="Gross Profit",
                        line=dict(color="#2ecc71"),
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=profit_trend["Date"],
                        y=profit_trend["EBITDA"],
                        mode="lines",
                        name="EBITDA",
                        line=dict(color="#3498db"),
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=profit_trend["Date"],
                        y=profit_trend["Net Income"],
                        mode="lines",
                        name="Net Income",
                        line=dict(color="#e74c3c"),
                    )
                )
                fig = _apply_plot_theme(fig, height=360, title="Profitability Trend")
                st.plotly_chart(fig, use_container_width=True)

                # Cash Flow & Liquidity
                st.markdown(
                    '<div class="panel"><div class="section-title">Cash Flow & Liquidity</div>',
                    unsafe_allow_html=True,
                )

                # Cash Flow Metrics - inside panel as KPI cards
                cash_inflows = filtered_df["Cash Inflows"].sum()
                cash_outflows = filtered_df["Cash Outflows"].sum()
                net_cash_flow = filtered_df["Net Cash Flow"].sum()
                cash_balance = filtered_df["Cash Balance"].iloc[-1]  # Latest balance

                st.markdown(
                    f"""
                    <div class=\"kpi-grid\">
                      <div class=\"kpi\"><div class=\"label\">Cash Inflows</div><div class=\"value\">${cash_inflows:,.0f}</div></div>
                      <div class=\"kpi\"><div class=\"label\">Cash Outflows</div><div class=\"value\">${cash_outflows:,.0f}</div></div>
                      <div class=\"kpi\"><div class=\"label\">Net Cash Flow</div><div class=\"value\">${net_cash_flow:,.0f}</div></div>
                      <div class=\"kpi\"><div class=\"label\">Cash Balance</div><div class=\"value\">${cash_balance:,.0f}</div></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Cash Flow Charts - Separate AR and AP Analysis
                col1, col2, col3 = st.columns(3)

                with col1:
                    # AR Analysis - Real Data
                    ar = latest_raw.get("Accounts Receivable (AR)", 0)
                    dso = latest_raw.get("Days Sales Outstanding (DSO)", 0)

                    # Create AR trend chart using filtered data
                    ar_trend_data = filtered_df[
                        [
                            "Date",
                            "Accounts Receivable (AR)",
                            "Days Sales Outstanding (DSO)",
                        ]
                    ].copy()

                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=ar_trend_data["Date"],
                            y=ar_trend_data["Accounts Receivable (AR)"],
                            mode="lines",
                            name="AR Balance",
                            line=dict(color="#3498db"),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=ar_trend_data["Date"],
                            y=ar_trend_data["Days Sales Outstanding (DSO)"],
                            mode="lines",
                            name="DSO (days)",
                            yaxis="y2",
                            line=dict(color="#e74c3c"),
                        )
                    )
                    fig.update_layout(yaxis2=dict(overlaying="y", side="right"))
                    fig = _apply_plot_theme(
                        fig,
                        height=300,
                        title=f"AR Trend & DSO (Current: {dso:.0f} days)",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    # AP Analysis - Real Data
                    ap = latest_raw.get("Accounts Payable (AP)", 0)
                    dpo = latest_raw.get("Days Payable Outstanding (DPO)", 0)

                    # Create AP trend chart using filtered data
                    ap_trend_data = filtered_df[
                        [
                            "Date",
                            "Accounts Payable (AP)",
                            "Days Payable Outstanding (DPO)",
                        ]
                    ].copy()

                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=ap_trend_data["Date"],
                            y=ap_trend_data["Accounts Payable (AP)"],
                            mode="lines",
                            name="AP Balance",
                            line=dict(color="#e74c3c"),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=ap_trend_data["Date"],
                            y=ap_trend_data["Days Payable Outstanding (DPO)"],
                            mode="lines",
                            name="DPO (days)",
                            yaxis="y2",
                            line=dict(color="#f39c12"),
                        )
                    )
                    fig.update_layout(yaxis2=dict(overlaying="y", side="right"))
                    fig = _apply_plot_theme(
                        fig,
                        height=300,
                        title=f"AP Trend & DPO (Current: {dpo:.0f} days)",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col3:
                    # Net Cash Flow by Business Unit
                    cash_by_unit = (
                        filtered_df.groupby("Business Unit / Department")[
                            "Net Cash Flow"
                        ]
                        .sum()
                        .reset_index()
                    )

                    fig = px.bar(
                        cash_by_unit,
                        x="Business Unit / Department",
                        y="Net Cash Flow",
                        title="Net Cash Flow by Business Unit",
                        color="Net Cash Flow",
                        color_continuous_scale=["red", "yellow", "green"],
                    )
                    fig = _apply_plot_theme(
                        fig, height=300, title="Net Cash Flow by Business Unit"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                # Balance Sheet Overview
                st.markdown(
                    '<div class="panel"><div class="section-title">Balance Sheet Overview</div>',
                    unsafe_allow_html=True,
                )

                # Balance Sheet Metrics as KPI cards
                total_assets = filtered_df["Total Assets"].sum()
                total_liabilities = filtered_df["Total Liabilities"].sum()
                equity = filtered_df["Equity"].sum()
                debt_outstanding = filtered_df["Debt Outstanding"].sum()
                debt_to_equity = (debt_outstanding / equity) if equity > 0 else 0
                current_ratio = filtered_df["Current Ratio"].mean()  # Average ratio

                st.markdown(
                    f"""
                    <div class="kpi-grid cols-6">
                      <div class="kpi"><div class="label">Total Assets</div><div class="value">${total_assets:,.0f}</div></div>
                      <div class="kpi"><div class="label">Total Liabilities</div><div class="value">${total_liabilities:,.0f}</div></div>
                      <div class="kpi"><div class="label">Equity</div><div class="value">${equity:,.0f}</div></div>
                      <div class="kpi"><div class="label">Debt Outstanding</div><div class="value">${debt_outstanding:,.0f}</div></div>
                      <div class="kpi"><div class="label">Debt-to-Equity</div><div class="value">{debt_to_equity:.2f}</div></div>
                      <div class="kpi"><div class="label">Current Ratio</div><div class="value">{current_ratio:.2f}</div></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                # Operational Efficiency & Resource Management
                st.markdown(
                    '<div class="panel"><div class="section-title">Operational Efficiency & Resource Management</div>',
                    unsafe_allow_html=True,
                )

                # Essential Operational Efficiency Metrics
                inventory_turnover = filtered_df[
                    "Inventory Turnover"
                ].mean()  # Average turnover
                cost_per_employee = filtered_df[
                    "Cost per Employee"
                ].mean()  # Average cost per employee
                capex_total = filtered_df[
                    "Capital Expenditure (CapEx)"
                ].sum()  # Total CapEx

                st.markdown(
                    f"""
                    <div class="kpi-grid cols-3">
                      <div class="kpi"><div class="label">Inventory Turnover</div><div class="value">{inventory_turnover:.1f}x</div></div>
                      <div class="kpi"><div class="label">Cost/Employee</div><div class="value">${cost_per_employee:,.0f}</div></div>
                      <div class="kpi"><div class="label">CapEx</div><div class="value">${capex_total:,.0f}</div></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Operational Charts (removed Order Backlog by Department)
                col1, col2, col3 = st.columns(3)

                with col1:
                    # Inventory vs Sales Pipeline with caching
                    inventory_key = (
                        f"inventory_trend_{hash(str(st.session_state.cfo_filters))}"
                    )
                    if inventory_key not in st.session_state:
                        # Use processed data - Date column already exists and is properly formatted
                        inventory_trend = filtered_df[
                            ["Date", "Inventory Value", "Sales Pipeline Value"]
                        ].copy()

                        # If we have too many data points, sample them for better visualization
                        if len(inventory_trend) > 50:
                            step = len(inventory_trend) // 50
                            inventory_trend = inventory_trend.iloc[::step]

                        st.session_state[inventory_key] = inventory_trend
                    else:
                        inventory_trend = st.session_state[inventory_key]

                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=inventory_trend["Date"],
                            y=inventory_trend["Inventory Value"],
                            mode="lines",
                            name="Inventory",
                            yaxis="y",
                            line=dict(color="#3498db"),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=inventory_trend["Date"],
                            y=inventory_trend["Sales Pipeline Value"],
                            mode="lines",
                            name="Pipeline",
                            yaxis="y2",
                            line=dict(color="#2ecc71"),
                        )
                    )
                    fig.update_layout(yaxis2=dict(overlaying="y", side="right"))
                    fig = _apply_plot_theme(
                        fig, height=300, title="Inventory vs Sales Pipeline"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    # CapEx vs OpEx Trend with caching
                    capex_key = f"capex_trend_{hash(str(st.session_state.cfo_filters))}"
                    if capex_key not in st.session_state:
                        # Use processed data - Date column already exists and is properly formatted
                        capex_opex_trend = filtered_df[
                            [
                                "Date",
                                "Capital Expenditure (CapEx)",
                                "Operational Expenditure (OpEx)",
                            ]
                        ].copy()

                        # If we have too many data points, sample them for better visualization
                        if len(capex_opex_trend) > 50:
                            step = len(capex_opex_trend) // 50
                            capex_opex_trend = capex_opex_trend.iloc[::step]

                        st.session_state[capex_key] = capex_opex_trend
                    else:
                        capex_opex_trend = st.session_state[capex_key]

                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=capex_opex_trend["Date"],
                            y=capex_opex_trend["Capital Expenditure (CapEx)"],
                            mode="lines",
                            name="CapEx",
                            line=dict(color="#e74c3c"),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=capex_opex_trend["Date"],
                            y=capex_opex_trend["Operational Expenditure (OpEx)"],
                            mode="lines",
                            name="OpEx",
                            line=dict(color="#3498db"),
                        )
                    )
                    fig = _apply_plot_theme(
                        fig, height=300, title="CapEx vs OpEx Trend"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col3:
                    # Headcount vs Cost per Employee
                    headcount_cost = filtered_df[
                        ["Headcount", "Cost per Employee", "Business Unit / Department"]
                    ].copy()

                    # If we have too many data points, sample them for better visualization
                    if len(headcount_cost) > 50:
                        step = len(headcount_cost) // 50
                        headcount_cost = headcount_cost.iloc[::step]

                    fig = px.scatter(
                        headcount_cost,
                        x="Headcount",
                        y="Cost per Employee",
                        color="Business Unit / Department",
                        title="Headcount vs Cost/Employee",
                        size_max=15,
                    )
                    fig = _apply_plot_theme(
                        fig, height=300, title="Headcount vs Cost/Employee"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown(
                        "<div style='height:8px'></div>", unsafe_allow_html=True
                    )

                # Departmental P&L Section
                st.markdown(
                    '<div class="panel"><div class="section-title">Departmental P&L</div>',
                    unsafe_allow_html=True,
                )

                # Departmental P&L with proper filtering
                if (
                    not filtered_df.empty
                    and "Business Unit / Department" in filtered_df.columns
                ):
                    dept_pnl = (
                        filtered_df.groupby("Business Unit / Department")
                        .agg(
                            {
                                "Revenue (Actual)": "sum",
                                "Cost of Goods Sold (COGS)": "sum",
                                "Operating Expenses (OPEX)": "sum",
                                "EBITDA": "sum",
                            }
                        )
                        .reset_index()
                    )

                    # Add calculated fields
                    dept_pnl["Gross Profit"] = (
                        dept_pnl["Revenue (Actual)"]
                        - dept_pnl["Cost of Goods Sold (COGS)"]
                    )
                    dept_pnl["Operating Income"] = (
                        dept_pnl["Gross Profit"] - dept_pnl["Operating Expenses (OPEX)"]
                    )
                    dept_pnl["Gross Margin %"] = (
                        dept_pnl["Gross Profit"] / dept_pnl["Revenue (Actual)"] * 100
                    ).round(1)
                    dept_pnl["Operating Margin %"] = (
                        dept_pnl["Operating Income"]
                        / dept_pnl["Revenue (Actual)"]
                        * 100
                    ).round(1)

                    # Format the dataframe for better display
                    display_columns = [
                        "Business Unit / Department",
                        "Revenue (Actual)",
                        "Cost of Goods Sold (COGS)",
                        "Gross Profit",
                        "Gross Margin %",
                        "Operating Expenses (OPEX)",
                        "Operating Income",
                        "Operating Margin %",
                        "EBITDA",
                    ]

                    dept_pnl_display = dept_pnl[display_columns].copy()

                    # Format currency columns
                    currency_columns = [
                        "Revenue (Actual)",
                        "Cost of Goods Sold (COGS)",
                        "Gross Profit",
                        "Operating Expenses (OPEX)",
                        "Operating Income",
                        "EBITDA",
                    ]
                    for col in currency_columns:
                        if col in dept_pnl_display.columns:
                            dept_pnl_display[col] = dept_pnl_display[col].apply(
                                lambda x: f"${x:,.0f}"
                            )

                    st.dataframe(dept_pnl_display, use_container_width=True)
                else:
                    st.warning(
                        "No data available for Departmental P&L analysis with current filters."
                    )

                st.markdown("</div>", unsafe_allow_html=True)

                # Footer / Alerts

                render_cfo_alerts_section(latest_raw, raw_df)

                # Footer from Home page
                st.markdown(
                    f"""
                <div class="footer">
                    <p><strong>ThrivvAI CFO Console</strong></p>
                    <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Data: realtime · <a href="mailto:support@thrivvai.com">Support</a></p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            else:
                st.warning(
                    "No financial data available. Please upload data using the sidebar."
                )

        except Exception as e:
            st.error(f"Error loading CFO dashboard: {str(e)}")
            st.info("Please check the backend services and data file.")
