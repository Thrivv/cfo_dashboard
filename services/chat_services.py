"""Chat services for AI assistant functionality."""

import runpod

from prompts import get_retry_prompt, get_system_prompt, get_smart_prompt, get_question_classification_prompt
from utils import get_chunk_service
from utils.config import RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID

runpod.api_key = RUNPOD_API_KEY
endpoint = runpod.Endpoint(RUNPOD_ENDPOINT_ID)


def format_llm_response(response_text):
    """Centralized function to format LLM responses for consistent display across all pages.
    Handles markdown tables and other formatting properly for Streamlit.

    Args:
        response_text (str): Raw LLM response text

    Returns:
        str: Formatted response with proper markdown handling
    """
    if not response_text:
        return response_text

    # Check if response contains markdown tables
    if "|" in response_text and "\n" in response_text:
        # This is likely a markdown table, return as-is for Streamlit to render
        return response_text
    else:
        # Return plain text without HTML formatting
        return response_text


def is_table_response(response_text):
    """Check if the response contains a markdown table.
    
    Args:
        response_text (str): AI response text
        
    Returns:
        bool: True if response contains a markdown table
    """
    return "|" in response_text and "\n" in response_text and "---" in response_text


def run_chatbot_job(prompt):
    """Submit a job to the RAG application for financial analysis.

    Args:
        prompt (str): User query or financial question
    """
    try:
        run_request = endpoint.run_sync(
            {
                "prompt": prompt,
                "application": "CFOChatbot",
                "sampling_params": {"temperature": 0.1, "max_tokens": 200},
            },
            timeout=180,  # Timeout in seconds
        )
        return run_request
    except TimeoutError:
        return "Job timed out. Please try again."
    except Exception as e:
        return f"Error: {str(e)}"


def classify_question(question):
    """Classify if a question is financial/business related using LLM.
    
    Args:
        question (str): User question to classify
        
    Returns:
        str: "FINANCIAL" or "NON_FINANCIAL"
    """
    try:
        # Get classification prompt
        prompt = get_question_classification_prompt(question)
        
        # Get AI response
        response = run_chatbot_job(prompt)
        
        # Extract text from response
        if isinstance(response, dict) and "generated_text" in response:
            response_str = response["generated_text"].strip().upper()
        else:
            response_str = str(response).strip().upper()
        
        # Return classification
        if "NON_FINANCIAL" in response_str:
            return "NON_FINANCIAL"
        else:
            return "FINANCIAL"
            
    except Exception as e:
        # Default to financial if classification fails
        return "FINANCIAL"


def process_financial_question(question):
    """Process questions - let AI determine if financial data is needed.

    Args:
        question (str): Question from user

    Returns:
        str: AI response based on question type
    """
    try:
        # Always try to get financial data first
        chunk_service = get_chunk_service()
        if not chunk_service._chunks:
            if not chunk_service.load_and_chunk_data():
                return "Unable to load financial data. Please ensure data is available."

        # Get all chunks formatted for LLM
        chunk_data = chunk_service.get_all_chunks_for_llm()

        if not chunk_data or chunk_data == "No data chunks available":
            return "No financial data available for analysis."

        # Use intelligent prompt that lets LLM decide when to use tables
        prompt = get_smart_prompt(chunk_data, question)

        # Get AI response
        response = run_chatbot_job(prompt)

        # Validate response
        if not response or "Job failed" in str(response):
            return "Unable to process your question at this time. Please try again."

        # Extract text from response (handle both dict and string)
        if isinstance(response, dict) and "generated_text" in response:
            response_str = response["generated_text"]
        else:
            response_str = str(response)

        # No retry logic needed - the simplified prompt should work correctly

        # Apply centralized formatting for consistent display across all pages
        return format_llm_response(response_str)

    except Exception as e:
        return f"Error processing financial question: {str(e)}"
