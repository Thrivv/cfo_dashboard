"""AI Assistant page with modern chat interface for financial queries."""

import streamlit as st
import time

from services.chat_services import process_financial_question, is_table_response
from services.forecast_services import create_forecast_chart, run_forecast_job, generate_chatbot_forecast_insights
from services.query_doc import query_documents
from utils import get_data_loader, save_chat_message


def suggest_questions():
    """Provide CFO-focused actionable example prompts organized by category."""
    return [
        # FINANCIAL ANALYSIS - Core Business Metrics
        "What are our revenue trends?",
        "What is our profit margin?",
        "What are our operational efficiency metrics?",
        # FINANCIAL COMPARISON - Table-based Analysis
        "Compare revenue vs expenses by quarter",
        "Show me profit margin trends over time",
        "Compare our performance across departments",
        # FORECASTING - Future Planning
        "Generate a forecast for Sales department",
        "Create a forecast for HR department",
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
        "capital requirements",
    ]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in rag_keywords)


def process_question(question):
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
                    "original_question": question,
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





def render():
    """Render a modern AI Assistant with native Streamlit chat elements."""
    # Initialize chat history with new format
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Ensure messages is always a list
    if not isinstance(st.session_state.messages, list):
        st.session_state.messages = []

    # Sidebar for Quick questions
    with st.sidebar:
        st.markdown("## Quick Questions")
        st.markdown("Click any question below to get started:")

        questions = suggest_questions()
        for idx, question in enumerate(questions):
            button_key = f"quick_btn_{idx}"
            if st.button(
                question,
                key=button_key,
                use_container_width=True,
            ):
                with st.spinner("Thinking..."):
                    # Add user message to chat history immediately
                    st.session_state.messages.append({"role": "user", "content": question})
                    
                    try:
                        # Get response
                        response = process_question(question)
                        
                        # Save to database (text only for database)
                        if isinstance(response, dict):
                            save_chat_message(question, response["text"])
                        else:
                            save_chat_message(question, response)
                        
                        # Add assistant response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                    except Exception as e:
                        error_msg = f"Error processing your question: {str(e)}. Please try again."
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        save_chat_message(question, error_msg)
                st.rerun()

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Handle different response types
            if isinstance(message["content"], dict):
                # Handle forecast responses
                response_text = message["content"]["text"]
                forecast_data = message["content"].get("forecast_data")
                forecast_department = message["content"].get("forecast_department")
                
                # Display response content
                if is_table_response(response_text):
                    st.markdown(response_text)
                else:
                    st.markdown(response_text)
                
                # Add forecast insights if available
                if "Forecast Generated" in response_text and forecast_data:
                    insights = generate_chatbot_forecast_insights(forecast_data, forecast_department)
                    st.markdown(insights, unsafe_allow_html=True)

                # Show forecast chart if available
                if "Forecast Generated" in response_text and forecast_data:
                    create_forecast_chart(forecast_data, forecast_department, chart_height=200)
            else:
                # Handle string responses
                response_text = message["content"]
                
                # Display response content
                if is_table_response(response_text):
                    st.markdown(response_text)
                else:
                    st.markdown(response_text)

    # Accept user input with modern chat input
    if prompt := st.chat_input("Ask about financial metrics, forecasts, invoices, regulations, or business performance..."):
        # Add user message to chat history immediately
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process the question
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Get response
                    response = process_question(prompt)
                    
                    # Handle different response types
                    if isinstance(response, dict):
                        # Forecast response
                        response_text = response["text"]
                        forecast_data = response.get("forecast_data")
                        forecast_department = response.get("forecast_department")
                        
                        # Display response
                        if is_table_response(response_text):
                            st.markdown(response_text)
                        else:
                            st.markdown(response_text)
                        
                        # Add forecast insights if available
                        if "Forecast Generated" in response_text and forecast_data:
                            insights = generate_chatbot_forecast_insights(forecast_data, forecast_department)
                            st.markdown(insights, unsafe_allow_html=True)
                        
                        # Show forecast chart if available
                        if "Forecast Generated" in response_text and forecast_data:
                            create_forecast_chart(forecast_data, forecast_department, chart_height=200)
                        
                        # Add to chat history
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # Save to database
                        save_chat_message(prompt, response_text)
                    else:
                        # String response
                        if is_table_response(response):
                            st.markdown(response)
                        else:
                            st.markdown(response)
                        
                        # Add to chat history
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # Save to database
                        save_chat_message(prompt, response)
                        
                except Exception as e:
                    error_msg = f"Error processing your question: {str(e)}. Please try again."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    save_chat_message(prompt, error_msg)
    
    # Display placeholder when no messages (after all processing)
    if len(st.session_state.messages) == 0:
        st.markdown(
            """
            <style>
            .animate-character {
                background-image: linear-gradient(
                    -225deg,
                    #231557 0%,
                    #44107a 29%,
                    #ff1361 67%,
                    #fff800 100%
                );
                background-size: auto auto;
                background-clip: border-box;
                background-size: 200% auto;
                color: #fff;
                background-clip: text;
                text-fill-color: transparent;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: textclip 2s linear infinite;
                display: inline-block;
                font-size: 48px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            
            @keyframes textclip {
                to {
                    background-position: 200% center;
                }
            }
            </style>
            <div style="text-align: center; padding: 60px 20px; color: #666;">
                <h1 class="animate-character">Hi... There! I'm Kraya Your AI Assistant</h2>
                <p style="font-size: 16px; margin: 0;">I'm here to help you with your financial questions and analysis.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
