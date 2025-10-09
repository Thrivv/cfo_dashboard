"""System prompts for CFO Dashboard AI Assistant.

This module contains all system prompts and templates used by the AI Assistant.
"""

# Available prompt types
PROMPT_TYPES = {
    "system": "system_prompt",
    "retry": "retry_prompt",
    "financial": "financial_analysis",
    "chat": "chat_response",
    "general": "general_question_prompt",
    "greeting": "greeting_prompt",
}

# LLM settings (removed - using chat_services.py configuration)


def is_financial_question(question: str) -> bool:
    """Check if the question is related to financial data analysis.
    
    Args:
        question (str): User question
        
    Returns:
        bool: True if financial question, False otherwise
    """
    financial_keywords = [
        'revenue', 'profit', 'loss', 'cash', 'liquidity', 'debt', 'equity',
        'margin', 'ratio', 'forecast', 'budget', 'expense', 'income',
        'balance sheet', 'income statement', 'cash flow', 'financial',
        'earnings', 'assets', 'liabilities', 'roi', 'growth', 'decline',
        'quarterly', 'annual', 'monthly', 'trend', 'analysis', 'kpi',
        'metrics', 'performance', 'dso', 'collections', 'payables',
        'receivables', 'inventory', 'turnover', 'leverage', 'ratios'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in financial_keywords)


def get_system_prompt(chunk_data: str, question: str) -> str:
    """Generate dynamic system prompt for financial analysis.

    Args:
        chunk_data (str): Financial data chunks
        question (str): User question

    Returns:
        str: Formatted system prompt
    """
    # Check if this is a financial question
    if not is_financial_question(question):
        return get_general_question_prompt(question)
    
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
• Use arrows (👉) instead of bullet points
• CRITICAL: Each arrow item must be on a separate line
• Start each arrow item on a new line
• Be direct and professional
• No tools or functions
• CRITICAL: Only use current data provided - do not reference outdated information
"""


def get_retry_prompt(question: str) -> str:
    """Generate retry prompt for failed responses.

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

CRITICAL: Each arrow item must be on a separate line. Use arrows (👉) and proper line breaks. No tools or functions. Only use current data provided. If question is not about financial data, respond naturally without using the financial data format.
"""


def get_general_question_prompt(question: str) -> str:
    """Generate prompt for non-financial questions.
    
    Args:
        question (str): User question
        
    Returns:
        str: General response prompt
    """
    return f"""You are Krayra, a helpful AI assistant. Answer this question naturally and conversationally:

{question}

Guidelines:
- Be helpful and informative
- Keep responses concise but complete (max 200 words)
- Use a friendly, professional tone
- If you don't know something, say so
- No special formatting, bullet points, or arrows needed
- Respond as if having a normal conversation
- Don't use "Key Findings" or structured format
"""


def get_greeting_prompt() -> str:
    """Get the greeting prompt for Krayra AI Assistant.

    Returns:
        str: Greeting prompt
    """
    return "I am Krayra, your financial AI assistant. How can I help you with your financial analysis today?"
