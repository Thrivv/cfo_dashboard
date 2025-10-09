import runpod
from utils import get_chunk_service
from prompts import get_system_prompt, get_retry_prompt
from utils.config import RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID

runpod.api_key = RUNPOD_API_KEY
endpoint = runpod.Endpoint(RUNPOD_ENDPOINT_ID)


def format_llm_response(response_text):
    """
    Centralized function to format LLM responses for consistent display across all pages.
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
    """
    Submit a job to the RAG application for financial analysis.

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
    """
    Process financial questions with data chunk integration.

    Args:
        question (str): Financial question from user

    Returns:
        str: AI response based on financial data
    """
    try:
        # Get chunk service and load data
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
