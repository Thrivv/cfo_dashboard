import streamlit as st


def render_sidebar():
    """Render sidebar navigation and return selected page"""

    st.markdown(
        """
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
    """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("Navigation")

        pages = ["CFO Dashboard", "Forecasting", "Insights", "AI Assistant"]

        if "nav_to" in st.session_state and st.session_state.nav_to:
            # Set the current page to the navigation target
            st.session_state.current_page = st.session_state.nav_to
            default_index = (
                pages.index(st.session_state.nav_to)
                if st.session_state.nav_to in pages
                else 0
            )
            # Clear the navigation variable
            st.session_state.nav_to = None
        else:
            if (
                hasattr(st.session_state, "current_page")
                and st.session_state.current_page == "Home"
            ):
                st.session_state.current_page = "CFO Dashboard"
            default_index = 0  # CFO Dashboard is now the default (first in list)

        if (
            "current_page" in st.session_state
            and st.session_state.current_page not in pages
        ):
            st.session_state.current_page = "CFO Dashboard"

        page = st.radio("Select Page", pages, key="current_page", index=default_index)

        return page
