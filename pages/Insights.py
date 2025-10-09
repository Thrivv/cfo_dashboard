import streamlit as st
import sys
import os

# Add RAG directory to path for due tables and insights
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'RAG')))
from due_tables import generate_due_tables
from generate_insights import generate_insights


def render():
    """Render insights page"""
    st.title("Financial Insights")

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