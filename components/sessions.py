"""Session state management for the CFO dashboard."""

from datetime import datetime, timedelta

import streamlit as st


def init_session_state():
    """Initialize session state variables."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "CFO Dashboard"

    if "financial_data" not in st.session_state:
        st.session_state.financial_data = None

    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {
            "theme": "light",
            "currency": "USD",
            "date_format": "%Y-%m-%d",
            "number_format": "comma",
        }

    if "session_start" not in st.session_state:
        st.session_state.session_start = datetime.now()

    if "last_activity" not in st.session_state:
        st.session_state.last_activity = datetime.now()

    st.session_state.last_activity = datetime.now()


def check_session_timeout(timeout_minutes=60):
    """Check if session has timed out."""
    if "last_activity" in st.session_state:
        time_since_activity = datetime.now() - st.session_state.last_activity
        if time_since_activity > timedelta(minutes=timeout_minutes):
            return True
    return False


def clear_session_data():
    """Clear sensitive session data."""
    keys_to_clear = ["financial_data", "uploaded_file", "chat_history"]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def get_session_info():
    """Get session information."""
    if "session_start" in st.session_state:
        session_duration = datetime.now() - st.session_state.session_start
        return {
            "start_time": st.session_state.session_start,
            "duration": session_duration,
            "last_activity": st.session_state.get("last_activity"),
            "current_page": st.session_state.get("current_page"),
        }
    return None


def update_user_preferences(preferences):
    """Update user preferences."""
    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {}

    st.session_state.user_preferences.update(preferences)


def get_user_preference(key, default=None):
    """Get user preference value."""
    return st.session_state.get("user_preferences", {}).get(key, default)
