"""Insights page for financial analysis and reporting."""

import os
import sys

import plotly.express as px
import streamlit as st

# Add RAG directory to path for due tables and insights
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RAG"))
)
from services.due_tables import (
    generate_due_tables,
    get_AP_risk_data,
    get_AR_risk_data,
    get_invoice_summary,
    view_risk_invoices,
)
from services.generate_insights import generate_insights


@st.cache_data(ttl=86400)
def get_cached_insights():
    """Generate and cache insights for 24 hours."""
    return generate_insights()


def render():
    """Render the insights page with financial analysis and reporting."""
    st.subheader("📊 Accounts Payable / Receivable Insights")

    due_data = generate_due_tables()
    ar_df = due_data["AR_df"]
    ap_df = due_data["AP_df"]

    st.subheader("Invoice Summary")
    summary_data = get_invoice_summary(ar_df, ap_df)

    fig = px.bar(
        summary_data["summary_df"],
        x="Type",
        y="Total Amount (AED)",
        title="Total Invoice Amounts",
    )
    st.plotly_chart(fig, use_container_width=True, key="invoice_summary")

    st.metric(label="Account Payable", value=f"{summary_data['ap_total']:,} AED")
    st.metric(
        label="Account Receivable", value=f"{summary_data['ar_total']:,} AED"
    )

    try:
        # Top section with risk score and invoice summary
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("AP Payment Delay Risk Score")
            risk_data_ap = get_AP_risk_data(ap_df)

            fig_1 = px.pie(
                risk_data_ap["risk_distribution"],
                names="Risk",
                values="Count",
                title="Payables Delay Risk Distribution",
            )
            st.plotly_chart(fig_1, use_container_width=True, key="ap_risk_distribution")

            st.warning(
                f"High risk of Account Payable payment delays detected in {risk_data_ap['high_risk_count']} invoices totalling {risk_data_ap['high_risk_total']:.2f} AED"
            )

            if st.button("View Risk AP Invoices"):
                st.dataframe(view_risk_invoices(risk_data_ap["high_risk_invoices"]))

        with col2:
            st.subheader("AR Payment Delay Risk Score")
            risk_data_ar = get_AR_risk_data(ar_df)

            fig_2 = px.pie(
                risk_data_ar["risk_distribution"],
                names="Risk",
                values="Count",
                title="Receivables Delay Risk Distribution",
            )
            st.plotly_chart(fig_2, use_container_width=True, key="ar_risk_distribution")

            st.warning(
                f"High risk of Account Receivable payment delays detected in {risk_data_ar['high_risk_count']} invoices totalling {risk_data_ar['high_risk_total']:.2f} AED"
            )

            if st.button("View Risk AR Invoices"):
                st.dataframe(view_risk_invoices(risk_data_ar["high_risk_invoices"]))

    except Exception as e:
        st.error(f"An error occurred while generating AP/AR tables: {e}")

    # ===============================
    # Append Due Tables
    # ===============================
    st.subheader("📊 Upcoming Accounts Payable / Receivable Insights")
    try:
        ap_due_df = due_data.get("AP_Due")
        ar_due_df = due_data.get("AR_Due")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Account Payables Due")
            if ap_due_df is not None and not ap_due_df.empty:
                st.dataframe(ap_due_df)
            else:
                st.info("No Account Payables data available.")

        with col2:
            st.subheader("Account Receivables Due")
            if ar_due_df is not None and not ar_due_df.empty:
                st.dataframe(ar_due_df)
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
            insights_data = get_cached_insights()
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
                    lines = [
                        line.strip()
                        for line in full_opp_text.split("\n")
                        if line.strip()
                    ]
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
                    lines = [
                        line.strip()
                        for line in full_warn_text.split("\n")
                        if line.strip()
                    ]
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


if __name__ == "__main__":
    render()