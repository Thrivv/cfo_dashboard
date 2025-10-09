"""Chat services for AI assistant functionality."""

import runpod

from prompts import get_retry_prompt, get_system_prompt, get_general_question_prompt
from utils import get_chunk_service
from utils.config import RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID

runpod.api_key = RUNPOD_API_KEY
endpoint = runpod.Endpoint(RUNPOD_ENDPOINT_ID)


def is_financial_question(question):
    """Determine if a question is financial or general.
    
    Args:
        question (str): User question
        
    Returns:
        bool: True if financial question, False if general question
    """
    question_lower = question.lower()
    
    # Financial keywords
    financial_keywords = [
        'revenue', 'profit', 'loss', 'cash', 'budget', 'forecast', 'expense',
        'income', 'balance', 'sheet', 'statement', 'financial', 'accounting',
        'kpi', 'metric', 'ratio', 'margin', 'growth', 'debt', 'equity',
        'liquidity', 'solvency', 'roi', 'ebitda', 'p&l', 'accounts payable',
        'accounts receivable', 'inventory', 'assets', 'liabilities', 'capital',
        'investment', 'funding', 'valuation', 'earnings', 'dividend',
        'cash flow', 'working capital', 'leverage', 'dso', 'dpo', 'turnover'
    ]
    
    # Check if question contains financial keywords
    for keyword in financial_keywords:
        if keyword in question_lower:
            return True
    
    # Check for general question patterns
    general_patterns = [
        'what is', 'how does', 'explain', 'define', 'tell me about',
        'machine learning', 'artificial intelligence', 'technology',
        'hello', 'hi', 'greetings', 'how are you', 'who are you'
    ]
    
    for pattern in general_patterns:
        if pattern in question_lower:
            return False
    
    # Default to financial if unclear
    return True


def format_llm_response(response_text):
    """Centralized function to format LLM responses for consistent display across all pages.
    Converts newlines to HTML breaks for proper rendering in Streamlit.

    Args:
        response_text (str): Raw LLM response text

    Returns:
        str: Formatted response with HTML line breaks
    """
    if not response_text:
        return response_text

    # Convert newlines to HTML breaks for proper formatting
    return response_text.replace("\n", "<br/>")


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
                "sampling_params": {"temperature": 0.1, "max_tokens": 512},
            },
            timeout=60,  # Timeout in seconds
        )
        return run_request
    except TimeoutError:
        return "Job timed out. Please try again."
    except Exception as e:
        return f"Error: {str(e)}"


def process_financial_question(question):
    """Process questions with appropriate prompt based on question type.

    Args:
        question (str): Question from user (financial or general)

    Returns:
        str: AI response based on question type
    """
    try:
        # Determine if question is financial or general
        if not is_financial_question(question):
            # Use general question prompt for non-financial questions
            prompt = get_general_question_prompt(question)
        else:
            # Use financial data for financial questions
            chunk_service = get_chunk_service()
            if not chunk_service._chunks:
                if not chunk_service.load_and_chunk_data():
                    return "Unable to load financial data. Please ensure data is available."

            # Get all chunks formatted for LLM
            chunk_data = chunk_service.get_all_chunks_for_llm()

            if not chunk_data or chunk_data == "No data chunks available":
                return "No financial data available for analysis."

            # Create prompt with financial data context using dynamic prompt
            prompt = get_system_prompt(chunk_data, question)

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

        # Filter out tool calls and JSON responses
        if response_str.startswith('{"tool":') or response_str.startswith("{"):
            # If response is a tool call, ask for direct analysis using dynamic retry prompt
            retry_prompt = get_retry_prompt(question)

            retry_response = run_chatbot_job(retry_prompt)
            if isinstance(retry_response, dict) and "generated_text" in retry_response:
                response_str = retry_response["generated_text"]
            else:
                response_str = str(retry_response)

        # Apply centralized formatting for consistent display across all pages
        return format_llm_response(response_str)

    except Exception as e:
        return f"Error processing financial question: {str(e)}"
