"""AI Assistant page with chat interface for financial queries."""

import streamlit as st

from services.chat_services import process_financial_question
from services.forecast_services import create_forecast_chart, run_forecast_job
from services.query_doc import query_documents
from utils import get_data_loader, save_chat_message


def suggest_questions():
    """Provide CFO-focused actionable example prompts organized by category."""
    return [
        # FINANCIAL ANALYSIS - Core Business Metrics
        "What are our revenue trends?",
        "What is our profit margin?",
        "What are our operational efficiency metrics?",
        # "Show me our financial performance summary",
        # "What are our key financial KPIs?",
        # "Analyze our working capital",
        # "What are our debt-to-equity ratios?",
        # "Show me our profitability analysis",
        # "What are our cost structure trends?",
        # FORECASTING - Future Planning
        "Generate a forecast for Sales department",
        "Create a forecast for HR department",
        # "Forecast our budget for IT department",
        # "Predict revenue for next quarter",
        # "Project cash flow for next 6 months",
        # "Forecast expenses for Operations",
        # "Create budget projection for Finance",
        # "Predict spending trends for Marketing",
        # RAG DOCUMENT ANALYSIS - Invoice & Payment Data
        "What are the important considerations from retail system services and Card schemes regulations",
        "What are the capital requirements?",
    ]


def is_forecast_question(question):
    """Check if the question is asking for forecasting."""
    forecast_keywords = [
        "forecast",
        "predict",
        "projection",
        "generate a forecast",
        "create a forecast",
    ]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in forecast_keywords)


def is_rag_question(question):
    """Check if the question is asking for document/invoice/regulation analysis."""
    rag_keywords = [
        "invoice",
        "payment",
        "overdue",
        "regulation",
        "license",
        "warning",
        "opportunity",
        "account receivable",
        "account payable",
        "receivables",
        "payables",
        "purchase orders",
        "po",
        "terms and conditions",
        "t&c",
        "discount",
        "penalty",
        "late fee",
        "retail payment",
        "card scheme",
        "compliance",
        "due date",
        "settlement",
        "financial obligation",
        "supplier",
        "vendor",
        "customer",
        "payment schedule",
        "extended terms",
        "regulatory requirement",
        "reporting requirement",
        "internal control",
        "rps",
        "penal interest",
        "interest charge",
        "late payment",
        "guarantee",
        "reminder notice",
        " capital requirements",
    ]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in rag_keywords)


def process_question(question, data):
    """Process a question using routing for financial analysis, forecasting, and RAG document analysis."""
    try:
        # Routing based on question content
        if is_forecast_question(question):
            # Use forecast service
            response = run_forecast_job(question)
            if response and "forecast_data" in response:
                # Return forecast data with the response for storage in chat history
                department = extract_department(question)
                return {
                    "text": "## Forecast Generated\n\nForecast data has been generated and chart displayed below.",
                    "forecast_data": response["forecast_data"],
                    "forecast_department": department,
                }
            else:
                return "Unable to generate forecast. Please ensure you mention a specific department."
        elif is_rag_question(question):
            # Use RAG document service for invoice/regulation questions
            try:
                response = query_documents(question)
                return f"## Document Analysis\n\n{response}"
            except Exception as e:
                return f"## Document Analysis\n\nError: {str(e)}. Please try again with a different question."
        else:
            # Use chatbot service for financial analysis questions
            response = process_financial_question(question)

            # Handle dict response (extract generated_text if it's a dict)
            if isinstance(response, dict) and "generated_text" in response:
                return response["generated_text"]
            elif isinstance(response, str):
                return response
            else:
                return str(response)
    except Exception as e:
        return f"Error processing your question: {str(e)}. Please try again."


def extract_department(question):
    """Extract department name from question."""
    departments = ["HR", "IT", "Operations", "Sales", "Finance", "Marketing"]
    question_upper = question.upper()
    for dept in departments:
        if dept.upper() in question_upper:
            return dept
    return "Unknown"


def handle_question_processing(question, data):
    """Handle the complete question processing workflow."""
    st.session_state.processing_question = True

    try:
        with st.spinner("Processing your question..."):
            # Get response (could be text or dict with forecast data)
            response = process_question(question, data)

            # Store response in chat history
            st.session_state.ai_chat_history.append((question, response))

            # Save to database (text only for database)
            if isinstance(response, dict):
                save_chat_message(question, response["text"])
            else:
                save_chat_message(question, response)
    except Exception as e:
        st.error(f"Error processing question: {str(e)}")
    finally:
        st.session_state.processing_question = False

    st.rerun()


def render():
    """Render a modern, futuristic AI Assistant experience (fresh design)."""
    data_loader = get_data_loader()
    data = data_loader.get_raw_data()

    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []
    if "processing_question" not in st.session_state:
        st.session_state.processing_question = False

    # Note: Alert questions are now handled inline in the dashboard, not here
    st.markdown(
        """
    <style>
      .panel {background: linear-gradient(180deg, rgba(13,13,23,0.92), rgba(6,6,12,0.98)); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 16px;}
      .chat-title {color: #e6e9ef; font-size: 1.25rem; font-weight: 700; margin: 0 0 4px;}
      .chat-box {max-height: 420px; overflow-y: auto; padding-right: 6px; transition: max-height .25s ease;}
      .chat-box.empty {min-height: 0; max-height: 0; height: 0; margin: 0; padding: 0; overflow: hidden;}
      .msg {border-radius: 12px; padding: 12px 14px; margin: 8px 0; max-width: 88%;}
      .msg-user {background: linear-gradient(135deg, rgba(148,2,245,0.20), rgba(41,128,185,0.20)); border: 1px solid rgba(148,2,245,0.35); color: #f1f3f5; margin-left: auto;}
      .msg-ai {background: linear-gradient(180deg, rgba(18,18,30,0.95), rgba(12,12,22,0.98)); border: 1px solid rgba(255,255,255,0.08); color: #cfd6dd;}
      .composer textarea {height: 72px !important;}

      /* Style Streamlit expander to look like our panel */
      [data-testid="stExpander"] > details {background: linear-gradient(180deg, rgba(13,13,23,0.92), rgba(6,6,12,0.98)); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;}
      [data-testid="stExpander"] summary {color: #c9d1d9; font-weight: 600;}
      [data-testid="stExpander"] .streamlit-expanderContent {padding: 8px 12px 12px 12px;}
    </style>
    """,
        unsafe_allow_html=True,
    )

    col_main, col_side = st.columns([2.2, 1])
    with col_main:
        chat_container = st.container()
        with chat_container:
            if st.session_state.ai_chat_history:
                st.markdown('<div class="chat-box">', unsafe_allow_html=True)
                for idx, chat_item in enumerate(st.session_state.ai_chat_history):
                    # Handle chat format (question, answer)
                    if len(chat_item) >= 2:
                        question, answer = chat_item[0], chat_item[1]
                    else:
                        continue

                    user_msg = f"You ➠ {question}"
                    st.markdown(
                        f"<div class='msg msg-user'>{user_msg}</div>",
                        unsafe_allow_html=True,
                    )

                    # Determine service type for display
                    if is_forecast_question(question):
                        service_type = "Forecasting Service"
                    elif is_rag_question(question):
                        service_type = "Document Analysis (RAG)"
                    else:
                        service_type = "Financial Analysis"

                    # Handle response format (could be string or dict with forecast data)
                    if isinstance(answer, dict):
                        response_text = answer["text"]
                        forecast_data = answer.get("forecast_data")
                        forecast_department = answer.get("forecast_department")
                    else:
                        response_text = answer
                        forecast_data = None
                        forecast_department = None

                    # Display AI response with service type
                    ai_msg = f"Krayra ⤵ ({service_type})<br/>{response_text}"

                    # Add forecast insights to the main message if available
                    if "Forecast Generated" in response_text and forecast_data:
                        from services.forecast_services import (
                            generate_chatbot_forecast_insights,
                        )

                        insights = generate_chatbot_forecast_insights(
                            forecast_data, forecast_department
                        )
                        # Merge insights into the main message
                        ai_msg += f"<br/>{insights}"

                    st.markdown(
                        f"<div class='msg msg-ai'>{ai_msg}</div>",
                        unsafe_allow_html=True,
                    )

                    # Show forecast chart if available
                    if "Forecast Generated" in response_text and forecast_data:
                        # Display forecast chart
                        create_forecast_chart(
                            forecast_data, forecast_department, chart_height=200
                        )

                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="chat-box empty"></div>', unsafe_allow_html=True
                )

        # Use form for Enter key support
        with st.form(key="question_form", clear_on_submit=True):
            user_question = st.text_area(
                "Your question",
                height=72,
                placeholder="Ask about financial metrics, forecasts, invoices, regulations, or business performance...",
                key="ai_question_input",
                label_visibility="collapsed",
            )

            col1, col2 = st.columns([1, 1])
            with col1:
                submitted = st.form_submit_button(
                    "Ask TO KraYa",
                    type="primary",
                    disabled=st.session_state.get("processing_question", False),
                )
            with col2:
                clear_clicked = st.form_submit_button(
                    "Clear", disabled=st.session_state.get("processing_question", False)
                )

        # Handle form submission
        if submitted and user_question.strip():
            handle_question_processing(user_question, data)
        elif clear_clicked:
            st.session_state.ai_chat_history = []
            st.session_state.processing_question = False
            # Clear the session state and let the page naturally refresh
            st.rerun()

        # Define button_disabled for quick questions
        button_disabled = st.session_state.get("processing_question", False)

    with col_side:
        with st.expander("Quick questions", expanded=True):
            if st.session_state.get("processing_question", False):
                st.info("Processing your question...")

            questions = suggest_questions()
            for idx, question in enumerate(questions):
                button_key = f"quick_btn_{idx}"

                if st.button(
                    question,
                    key=button_key,
                    use_container_width=True,
                    disabled=button_disabled,
                ):
                    handle_question_processing(question, data)

        with st.expander("CFO Data Status", expanded=True):
            if data is not None:
                st.success("CFO dashboard data active")
                st.info(f"{len(data)} financial records loaded")
            else:
                st.warning("CFO data unavailable")
                st.info("ERP financial data required for analysis")

                # Service Status
                st.success("📊 Financial Analysis: Active")
                st.success("🔮 Forecasting Service: Active")
                st.success("📄 Document Analysis (RAG): Active")

            if st.session_state.ai_chat_history:
                st.metric(
                    "CFO queries processed", len(st.session_state.ai_chat_history)
                )
