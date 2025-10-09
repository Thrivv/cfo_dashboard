import streamlit as st


def render_header():
    """Render application header with dynamic title/subtitle derived from session state"""
    current_page = st.session_state.get("current_page", "Home")
    page_to_title = {
        "Home": "Home",
        "Forecasting": "Forecasting",
        "Insights": "Insights",
        "AI Assistant": "Thrivv AI Assistant",
        "CFO Dashboard": "CFO Dashboard",
    }
    title = page_to_title.get(current_page, "CFO Dashboard")
    subtitle = "ThrivvAI Financial Intelligence & Analytics Platform"

    st.markdown(
        f"""
    <style>
    .header-container {{
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }}
    .header-title {{
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }}
    .header-subtitle {{
        font-size: 1rem;
        opacity: 0.8;
        margin: 0;
    }}
    </style>
    <div class="header-container">
        <h1 class="header-title">{title}</h1>
        <p class="header-subtitle">{subtitle}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
