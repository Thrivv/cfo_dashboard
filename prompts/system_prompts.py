"""
System prompts for CFO Dashboard AI Assistant.

This module contains all system prompts and templates used by the AI Assistant.
"""

# Available prompt types
PROMPT_TYPES = {
    "system": "system_prompt",
    "retry": "retry_prompt",
    "financial": "financial_analysis",
    "chat": "chat_response"
}

# LLM settings (removed - using chat_services.py configuration)

def get_system_prompt(chunk_data: str, question: str) -> str:
    """
    Generate dynamic system prompt for financial analysis.
    
    Args:
        chunk_data (str): Financial data chunks
        question (str): User question
        
    Returns:
        str: Formatted system prompt
    """
    return f"""Answer in MAXIMUM 150 WORDS. Be extremely brief.

DATA:
{chunk_data}

QUESTION:
{question}

FORMAT:
Key Findings:
👉 Item 1 with exact values
👉 Item 2 with exact values
👉 Item 3 with exact values

Conclusion: 1-2 sentences with insights

RULES:
• Use exact values from data
• MAXIMUM 150 WORDS - count and stop at 150
• Use arrows (👉) instead of bullet points
• CRITICAL: Each arrow item must be on a separate line
• Start each arrow item on a new line
• Be direct and professional
• No tools or functions
"""


def get_retry_prompt(question: str) -> str:
    """
    Generate retry prompt for failed responses.
    
    Args:
        question (str): User question
        
    Returns:
        str: Retry prompt
    """
    return f"""Answer directly: {question}
            
MAXIMUM 150 WORDS. Format as:
Key Findings:
👉 Item 1 with exact values
👉 Item 2 with exact values

Conclusion: 1-2 sentences

CRITICAL: Each arrow item must be on a separate line. Use arrows (👉) and proper line breaks. No tools or functions.
"""


def get_system_prompt_template() -> str:
    """
    Get the base system prompt template.
    
    Returns:
        str: Base system prompt template
    """
    return """Answer in MAXIMUM 150 WORDS. Be extremely brief.

DATA:
{chunk_data}

QUESTION:
{question}

FORMAT:
Key Findings:
👉 Item 1 with exact values
👉 Item 2 with exact values
👉 Item 3 with exact values

Conclusion: 1-2 sentences with insights

RULES:
• Use exact values from data
• MAXIMUM 150 WORDS - count and stop at 150
• Use arrows (👉) instead of bullet points
• CRITICAL: Each arrow item must be on a separate line
• Start each arrow item on a new line
• Be direct and professional
• No tools or functions
"""


def get_retry_prompt_template() -> str:
    """
    Get the retry prompt template.
    
    Returns:
        str: Retry prompt template
    """
    return """Answer directly: {question}
            
MAXIMUM 150 WORDS. Format as:
Key Findings:
👉 Item 1 with exact values
👉 Item 2 with exact values

Conclusion: 1-2 sentences

CRITICAL: Each arrow item must be on a separate line. Use arrows (👉) and proper line breaks. No tools or functions.
"""
