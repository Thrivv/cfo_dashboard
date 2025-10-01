import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# Service imports
from services.kpi_service import load_cfo_data
from services.insights_service import ai_insights as get_ai_insights
from services.chatbot_llm_services import process_financial_question

# Add RAG directory to path for due tables and insights
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'RAG')))
from due_tables import generate_due_tables
from generate_insights import generate_insights


def get_ai_insights_for_insights(question):
    """Get AI insights for Insights page, bypassing forecast detection."""
    insights_question = (
        f"Please provide a detailed financial analysis: {question}. "
        f"Give me direct insights and recommendations without using any tools."
    )
    return process_financial_question(insights_question)


def render():
    """Render insights page"""
    st.title("Financial Insights")
    try:
        data = load_cfo_data()
        if data is not None and not data.empty:
            # KPI filters
            col1, col2 = st.columns(2)
            with col1:
                kpi_filter = st.selectbox("Select KPI", ["All KPIs", "Cash on Hand", "Burn Rate", "Runway"])
            with col2:
                date_range = st.selectbox("Date Range", ["Last 7 days", "Last 30 days", "All data"])

            if date_range == "Last 7 days":
                data = data.tail(7)
            elif date_range == "Last 30 days":
                data = data.tail(30)

            # KPI change analysis
            st.subheader("KPI Change Analysis")
            if kpi_filter == "All KPIs" or kpi_filter == "Cash on Hand":
                cash_change = ((data['Cash_on_Hand'].iloc[-1] - data['Cash_on_Hand'].iloc[0]) / data['Cash_on_Hand'].iloc[0]) * 100
                st.markdown(f"**Cash on Hand:** {cash_change:+.1f}% change")
                st.markdown(f"- Current value: ${data['Cash_on_Hand'].iloc[-1]:,.0f}")
                st.markdown(f"- Trend: {'Increasing' if cash_change > 0 else 'Decreasing'}")
                st.markdown("--- ")
            if kpi_filter == "All KPIs" or kpi_filter == "Burn Rate":
                burn_change = ((data['Burn_Rate'].iloc[-1] - data['Burn_Rate'].iloc[0]) / data['Burn_Rate'].iloc[0]) * 100
                st.markdown(f"**Burn Rate:** {burn_change:+.1f}% change")
                st.markdown(f"- Current value: ${data['Burn_Rate'].iloc[-1]:,.0f}/day")
                st.markdown(f"- Trend: {'Increasing' if burn_change > 0 else 'Decreasing'}")
                st.markdown("--- ")
            if kpi_filter == "All KPIs" or kpi_filter == "Runway":
                runway_change = data['Runway_Months'].iloc[-1] - data['Runway_Months'].iloc[0]
                st.markdown(f"**Runway:** {runway_change:+.1f} months change")
                st.markdown(f"- Current value: {data['Runway_Months'].iloc[-1]:.1f} months")
                st.markdown(f"- Status: {'Improving' if runway_change > 0 else 'Declining'}")
                st.markdown("--- ")

            # AI-Powered Insights
            st.subheader("🤖 AI-Powered Financial Insights")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📊 Cash Flow Analysis", key="ai_cash_flow"):
                    with st.spinner("Generating AI cash flow insights..."):
                        ai_response = get_ai_insights_for_insights(
                            "Analyze our cash flow position, burn rate, and runway. Provide insights and recommendations."
                        )
                        st.session_state.ai_insights = ai_response
                        st.session_state.insights_type = "Cash Flow Analysis"
            with col2:
                if st.button("⚠️ Risk Assessment", key="ai_risk"):
                    with st.spinner("Generating AI risk assessment..."):
                        ai_response = get_ai_insights_for_insights(
                            "Identify financial risks, anomalies, and potential issues in our current financial position."
                        )
                        st.session_state.ai_insights = ai_response
                        st.session_state.insights_type = "Risk Assessment"
            with col3:
                if st.button("📈 Performance Review", key="ai_performance"):
                    with st.spinner("Generating AI performance insights..."):
                        ai_response = get_ai_insights_for_insights(
                            "Review our financial performance, trends, and provide strategic recommendations."
                        )
                        st.session_state.ai_insights = ai_response
                        st.session_state.insights_type = "Performance Review"

            if 'ai_insights' in st.session_state and st.session_state.ai_insights:
                st.markdown(f"#### {st.session_state.insights_type}")
                st.markdown(st.session_state.ai_insights)

                if st.button("Clear AI Insights", key="clear_ai_insights"):
                    if 'ai_insights' in st.session_state:
                        del st.session_state.ai_insights
                    if 'insights_type' in st.session_state:
                        del st.session_state.insights_type
                    st.rerun()

            # Basic AI Insights
            st.subheader("📋 Basic Financial Metrics")
            insights = get_ai_insights(data)
            for insight in insights:
                st.markdown(f"- {insight}")

            st.subheader("KPI Breakdown")
            summary_data = {
                "KPI": ["Cash on Hand", "Burn Rate", "Runway"],
                "Current Value": [
                    f"${data['Cash_on_Hand'].iloc[-1]:,.0f}",
                    f"${data['Burn_Rate'].iloc[-1]:,.0f}/day",
                    f"{data['Runway_Months'].iloc[-1]:.1f} months",
                ],
                "7-Day Change": [
                    f"{((data['Cash_on_Hand'].iloc[-1] - data['Cash_on_Hand'].iloc[-7]) / data['Cash_on_Hand'].iloc[-7] * 100):+.1f}%" if len(data) >= 7 else "N/A",
                    f"{((data['Burn_Rate'].iloc[-1] - data['Burn_Rate'].iloc[-7]) / data['Burn_Rate'].iloc[-7] * 10.0):+.1f}%" if len(data) >= 7 else "N/A",
                    f"{(data['Runway_Months'].iloc[-1] - data['Runway_Months'].iloc[-7]):+.1f} months" if len(data) >= 7 else "N/A",
                ],
                "Period Change": [
                    f"{((data['Cash_on_Hand'].iloc[-1] - data['Cash_on_Hand'].iloc[0]) / data['Cash_on_Hand'].iloc[0]) * 100:+.1f}%",
                    f"{((data['Burn_Rate'].iloc[-1] - data['Burn_Rate'].iloc[0]) / data['Burn_Rate'].iloc[0]) * 100:+.1f}%",
                    f"{(data['Runway_Months'].iloc[-1] - data['Runway_Months'].iloc[0]):+.1f} months",
                ],
            }
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

        else:
            st.warning("No financial data available. Please upload data using the sidebar.")

    except Exception as e:
        st.error(f"Error generating insights: {str(e)}")
        st.info("Please check your data and try again.")

    # ===============================
    # Append Due Tables
    # ===============================
    st.subheader("📊 Accounts Payable / Receivable Insights")
    try:
        due_data = generate_due_tables()
        ap_due_table = due_data.get("AP_Due")
        ar_due_table = due_data.get("AR_Due")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Account Payables Due")
            if ap_due_table:
                st.markdown(ap_due_table)
            else:
                st.info("No Account Payables data available.")
        with col2:
            st.subheader("Account Receivables Due")
            if ar_due_table:
                st.markdown(ar_due_table)
            else:
                st.info("No Account Receivables data available.")
    except Exception as e:
        st.error(f"An error occurred while generating AP/AR tables: {e}")

    # ===============================
    # Opportunities/Warnings from insight.py
    # ===============================
    st.subheader("AI Warnings and Opportunities")
    with st.spinner("Generating AI Warnings and Opportunities..."):
        try:
            insights_data = generate_insights()
            opportunities = insights_data.get("opportunities", {})
            warnings = insights_data.get("warnings", {})

            col3, col4 = st.columns(2)
            with col3:
                st.subheader("Opportunities")
                full_opp_text = ""
                ar_opps = opportunities.get("AR", "")
                ap_opps = opportunities.get("AP", "")
                if ar_opps:
                    full_opp_text += ar_opps + "\n"
                if ap_opps:
                    full_opp_text += ap_opps
                if full_opp_text:
                    lines = [line.strip() for line in full_opp_text.split('\n') if line.strip()]
                    # Show all opportunities, not just the first 2
                    if lines:
                        for line in lines:
                            st.success(line)
                    else:
                        st.info("No new opportunities.")
                else:
                    st.info("No new opportunities.")

            with col4:
                st.subheader("Warnings")
                full_warn_text = ""
                ar_warnings = warnings.get("AR", "")
                ap_warnings = warnings.get("AP", "")
                if ar_warnings:
                    full_warn_text += ar_warnings + "\n"
                if ap_warnings:
                    full_warn_text += ap_warnings
                if full_warn_text:
                    lines = [line.strip() for line in full_warn_text.split('\n') if line.strip()]
                    # Show all warnings, not just the first 2
                    if lines:
                        for line in lines:
                            st.warning(line)
                    else:
                        st.info("No new warnings.")
                else:
                    st.info("No new warnings.")
        except Exception as e:
            st.error(f"An error occurred while generating AI insights: {e}")