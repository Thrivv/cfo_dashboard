import streamlit as st
import time
import re
import numpy as np
from typing import Dict, Tuple

from services.chat_services import process_financial_question, is_table_response, classify_question
from services.forecast_services import create_forecast_chart, run_forecast_job, generate_chatbot_forecast_insights
from services.query_doc import query_documents
from utils.database import save_chat_message
from utils.llm_client import call_vllm

# Embedding / similarity tools
try:
    from sentence_transformers import SentenceTransformer
    from numpy.linalg import norm
except Exception:
    SentenceTransformer = None
    norm = None

# --- Configuration: example queries per bucket ---
EXAMPLES_BY_BUCKET = {
    "RAG": [
        "What are the retail system services and Card schemes regulations",
        "Show me important conditions mentioned in Purchase order",
        "What are the rebate rules for vendor X",
        "List compliance requirements for card scheme settlement",
        "Find contract T&Cs related to late fee and penalty",
        "What are the upcoming invoices?",
        "What are the overdue invoices",
        "What are the retail system services and Card schemes regulations",
        "What are the important conditions mentioned in Purchase order?"
    ],
    "FORECAST": [
        "Generate a forecast for Sales department",
        "Create a forecast for HR department",
        "Forecast next quarter revenue",
        "Predict sales pipeline for next 6 months",
        "What will be the trend for cash balance next year?"
    ],
    "FINANCIAL": [
        "What are our revenue trends?",
        "What is our profit margin?",
        "Compare revenue vs expenses by quarter",
        "Show me profit margin trends over time",
        "Compare our performance across departments"
    ],
}

GREETING_KEYWORDS = [
        "hi", "hii", "hey there", "hii...", "hello", "hey", "good morning", "good afternoon", "good evening",
        "greetings", "howdy", "what's up", "sup", "yo", "hi...", "who are you", "what is your name","how are you",
        "what can you do for me", "what can you do for me","what do you do", "what do you know", "what do you think",
]

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Precompute embeddings cache
_EMBED_MODEL = None
_EXAMPLE_EMBS: Dict[str, np.ndarray] = {}

# Thresholds
SEMANTIC_SIM_THRESHOLD = 0.60  # tuned; fall back to LLM if below
TOP_K = 3  # for nearest example check

# Quick regex / keyword markers for fast routing (hybrid)
FORECAST_PATTERN = r"\b(forecast|predict|projection|scenario|what will|next quarter|next month|next year|trend for|predicting|will be|forecast for|how much cash will|projected|projection|cash in|cash out|inflows|outflows|what if|scenario|simulate|simulation)\b"
DB_QUERY_PATTERN = r"\b(invoice|invoices|rebate summary|rebate rule summary|rebate|payment|overdue|warning|opportunity|account receivable|ap|ar|account payable|receivables|payables|discount|penalty|late fee|due date|settlement|supplier|vendor|customer|customers|payment schedule|interest charge|late payment)\b"
RAG_PATTERN = r"\b(regulation|license|purchase orders|purchase order|po|terms and conditions|t&c|retail payment system|retail payment|retail payemnt system service|card scheme|card scheme regulation|compliance|financial obligation|extended terms|regulatory requirement|reporting requirement|internal control|rps|guarantee|reminder notice|capital requirements)\b"

def _init_embedding_model():
    """Load embedding model once."""
    global _EMBED_MODEL, _EXAMPLE_EMBS
    if _EMBED_MODEL is not None:
        return
    if SentenceTransformer is None:
        _EMBED_MODEL = None
        return
    _EMBED_MODEL = SentenceTransformer(EMBEDDING_MODEL)
    # compute example embeddings
    for bucket, examples in EXAMPLES_BY_BUCKET.items():
        embs = _EMBED_MODEL.encode(examples, convert_to_numpy=True, show_progress_bar=False)
        _EXAMPLE_EMBS[bucket] = embs


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return 0.0
    denom = (norm(a) * norm(b))
    return float(np.dot(a, b) / denom) if denom != 0 else 0.0


def semantic_route(question: str) -> Tuple[str, float]:
    """
    Semantic routing: embed the question and compute nearest bucket by
    mean/nearest-example cosine similarity. Returns (bucket, score).
    """
    if _EMBED_MODEL is None:
        return ("UNKNOWN", 0.0)
    q_emb = _EMBED_MODEL.encode([question], convert_to_numpy=True)[0]
    best_bucket = "UNKNOWN"
    best_score = 0.0
    for bucket, ex_embs in _EXAMPLE_EMBS.items():
        # compute similarity to top-K nearest example in the bucket
        sims = [ _cosine_sim(q_emb, ex) for ex in ex_embs ]
        # take mean of top-K
        topk = sorted(sims, reverse=True)[:TOP_K]
        score = float(np.mean(topk)) if len(topk) > 0 else 0.0
        if score > best_score:
            best_score = score
            best_bucket = bucket
    return best_bucket, best_score


def quick_regex_route(question: str) -> Tuple[str, float]:
    """
    Fast deterministic check using keywords - returns (bucket, confidence_score).
    """
    q = question.lower()
    # Greetings
    if q.strip() in GREETING_KEYWORDS or q.startswith(("hi ", "hello ", "hey ")):
        return ("GREETING", 1.0)
    # Forecast priority
    if re.search(FORECAST_PATTERN, q, re.IGNORECASE):
        return ("FORECAST", 0.95)
    # DB / invoice queries are grouped into RAG
    if re.search(DB_QUERY_PATTERN, q, re.IGNORECASE):
        return ("RAG", 0.9)
    # RAG keywords (policies/regulations)
    if re.search(RAG_PATTERN, q, re.IGNORECASE):
        return ("RAG", 0.9)
    return ("UNKNOWN", 0.0)


def llm_classify_route(question: str) -> Tuple[str, float]:
    """
    Deterministic LLM classifier fallback. Returns (bucket, score).
    """
    prompt = f"""
    You are a financial query classification expert. Your task is to classify a given user query into one of three categories: RAG, FORECAST, or FINANCIAL.

    Here are the rules for classification:

    1.  **RAG**: Classify the query as RAG if it is related to any of the following:
        *   Account receivables
        *   Payables
        *   Regulations
        *   Purchase orders
        *   Rebates

    2. **FORECAST**: Classify the query as FORECAST if it is related to forecasting, predictions, scenario analysis, what-if modeling, future cash availability,projected balances, projected KPIs, or expected values in a future period.


    3.  **FINANCIAL**: Classify the query as FINANCIAL if it pertains to Key Performance Indicator (KPI) analysis. This includes queries about:
        *   Date / Period
        *   Business Unit / Department
        *   Revenue (Actual), Revenue (Budget / Forecast)
        *   Cost of Goods Sold (COGS)
        *   Gross Profit
        *   Operating Expenses (OPEX)
        *   EBITDA
        *   Net Income
        *   Cash Inflows, Cash Outflows, Net Cash Flow, Cash Balance
        *   Days Sales Outstanding (DSO), Days Payable Outstanding (DPO)
        *   Working Capital
        *   Total Assets, Total Liabilities, Equity
        *   Debt Outstanding, Debt-to-Equity Ratio, Current Ratio
        *   Budget Variance (%)
        *   Year-over-Year Growth (%), Return on Equity (ROE), Return on Assets (ROA)
        *   Gross Margin %, Operating Margin %, EBITDA Margin %
        *   Inventory Value, Inventory Turnover
        *   Capital Expenditure (CapEx), Operational Expenditure (OpEx)
        *   Headcount, Cost per Employee
        *   Sales Pipeline Value, Order Backlog

    Please respond with only one of the following classifications: RAG, FORECAST, or FINANCIAL.

    Query: "{question}"
    Classification:
    """
    
    classification = call_vllm(prompt).strip()

    if classification in ["RAG", "FORECAST", "FINANCIAL"]:
        return classification, 0.9  # High confidence as it's an LLM classification
    else:
        return "UNKNOWN", 0.5


def route_question(question: str) -> Tuple[str, str]:
    """
    Orchestrates the routing of a question.
    1. Quick regex check
    2. Semantic search
    3. LLM classification as fallback
    """
    # 1. Quick regex route
    bucket, score = quick_regex_route(question)
    if bucket != "UNKNOWN":
        return bucket, "Regex"

    # 2. Semantic route
    bucket, score = semantic_route(question)
    if score >= SEMANTIC_SIM_THRESHOLD:
        return bucket, "Semantic"

    # 3. LLM classification fallback
    bucket, score = llm_classify_route(question)
    return bucket, "LLM"


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
        "What are the upcoming invoices?",
        "What are the overdue invoices",
        "What are the retail system services and Card schemes regulations",
        "What are the important conditions mentioned in Purchase order?",
    ]

def process_question(question):
    """Process a question using routing for financial analysis, forecasting, and RAG document analysis."""
    try:
        # Route the question to the appropriate category
        category, method = route_question(question)
        print(f"Classification: {method}, Intent: {category}")

        if category == "GREETING":
            return "Hello! I'm Kraya, your financial AI assistant. I'm here to help you with financial analysis, forecasting, and document insights. How can I assist you today?"
        
        elif category == "FORECAST":
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
        
        elif category == "RAG":
            # Use RAG document service for invoice/regulation questions
            try:
                response = query_documents(question)
                return f"## Document Analysis\n\n{response}"
            except Exception as e:
                return f"## Document Analysis\n\nError: {str(e)}. Please try again with a different question."

        elif category == "FINANCIAL":
             # Use chatbot service for financial analysis questions
            response = process_financial_question(question)

            # Handle dict response (extract generated_text if it's a dict)
            if isinstance(response, dict) and "generated_text" in response:
                return response["generated_text"]
            elif isinstance(response, str):
                return response
            else:
                return str(response)

        else: # UNKNOWN or other cases
            return "I don't have data to answer this question. I'm specialized in financial analysis, forecasting, and business insights. Please ask me about revenue trends, profit margins, department performance, or other financial metrics."

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

# Initialize the embedding model and example embeddings on startup
_init_embedding_model()

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
            <div style=\"text-align: center; padding: 60px 20px; color: #666;">
                <h1 class=\"animate-character\">Hi... There! I'm Kraya Your AI Assistant</h1>
                <p style=\"font-size: 16px; margin: 0;">I'm here to help you with your financial questions and analysis.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
