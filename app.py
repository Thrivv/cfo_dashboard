import streamlit as st

from components.sidebar import render_sidebar
from components.header import render_header
from components.sessions import init_session_state
from pages import Budgeting_Forecasting, Insights, CFO_Dashboard, AI_Assistant


st.set_page_config(
    page_title="CFO Dashboard PoC",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """Main application entry point"""
    init_session_state()
    
    current_page = render_sidebar()
    render_header()

    if current_page == "CFO Dashboard":
        CFO_Dashboard.render()
    elif current_page == "Forecasting":
        Budgeting_Forecasting.render()
    elif current_page == "Insights":
        Insights.render()
    elif current_page == "AI Assistant":
        AI_Assistant.render()


if __name__ == "__main__":
    main()


