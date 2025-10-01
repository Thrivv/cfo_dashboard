import requests
import time
import os

API_KEY = "rpa_KN3HAWGAIXJVZPKFL7WD5JV8XYIZW27LWYZC2RYZ1wthhi"
ENDPOINT_ID = "lkbk4plvvt0vah"
BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def run_rag_document_job(prompt):
    """
    Submit a job to the RAG document analysis RunPod endpoint.
    
    Args:
        prompt (str): Document-related question
    """
    data = {
        "input": {
            "prompt": prompt,
            "application": "RAG",
            "sampling_params": {
                "temperature": 0.1,
                "max_tokens": 2000,
                "repetition_penalty": 1.2
            }
        }
    }

    # Step 1: Submit the job
    response = requests.post(f"{BASE_URL}/run", headers=headers, json=data)
    job = response.json()
    job_id = job["id"]

    # Step 2: Poll for the result
    while True:
        status_response = requests.get(f"{BASE_URL}/status/{job_id}", headers=headers)
        status_json = status_response.json()

        if status_json["status"] == "COMPLETED":
            return status_json["output"]
        elif status_json["status"] == "FAILED":
            return f"Job failed: {status_json}"
        else:
            time.sleep(1)

def process_document_question(question):
    """
    Process document-related questions using RAG API.
    
    Args:
        question (str): Document question from user
        
    Returns:
        str: AI response based on document content
    """
    try:
        # Get RAG API URL from environment or use default
        rag_api_url = os.getenv('RAG_API_URL', 'http://localhost:8000')
        
        # Call RAG API
        response = requests.post(
            f"{rag_api_url}/query",
            data={
                "query": question,
                "template": "default"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            # Handle different response formats
            if isinstance(result, dict):
                if 'generated_text' in result:
                    return result['generated_text']
                elif 'answer' in result:
                    return result['answer']
                else:
                    return str(result)
            else:
                return str(result)
        else:
            return f"RAG API error: {response.status_code} - {response.text}"
            
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to RAG API. Please ensure the RAG service is running."
    except requests.exceptions.Timeout:
        return "Error: RAG API request timed out. Please try again."
    except Exception as e:
        return f"Error processing document question: {str(e)}"

def get_question_data_source(question):
    """
    Data Source-Based Routing: Determine what data source the question needs.
    This is the recommended approach based on comprehensive testing.
    
    Args:
        question (str): User question
        
    Returns:
        str: Service type - 'RAG_DOCUMENT', 'FINANCIAL_ANALYSIS', 'FORECAST'
    """
    question_lower = question.lower()
    
    # 1. Check if question needs INVOICE data (RAG Document Service)
    invoice_keywords = [
        'invoice', 'invoices', 'overdue invoices', 'invoice data', 'invoice analysis',
        'payment status', 'outstanding', 'due date', 'invoice date',
        'payment patterns', 'customer payment', 'payment data',
        'payment summary', 'invoice summary', 'invoice aging', 'aging analysis',
        'customers have the highest', 'top 3 overdue', 'past due'
    ]
    if any(keyword in question_lower for keyword in invoice_keywords):
        return "RAG_DOCUMENT"
    
    # 2. Check if question needs REGULATION data (RAG Document Service)
    regulation_keywords = [
        'policy', 'policies', 'document', 'documents', 'manual', 'procedure', 'procedures',
        'regulation', 'regulations', 'guideline', 'guidelines', 'rule', 'rules',
        'budget policy', 'expense policy', 'payroll policy', 'delegation policy',
        'insurance policy', 'treasury policy', 'accounting manual', 'approval limits',
        'financial policies', 'university policies', 'what does the policy say',
        'according to the policy', 'policy states', 'policy covers',
        'requirement', 'compliance', 'license', 'capital requirement', 'audit requirement',
        'regulatory obligations', 'reporting requirements', 'risk management guidelines'
    ]
    if any(keyword in question_lower for keyword in regulation_keywords):
        return "RAG_DOCUMENT"
    
    # 3. Check if question needs FORECASTING (Forecast Service)
    forecast_keywords = [
        'forecast', 'predict', 'projection', 'graph', 'chart', 'generate forecast',
        'create forecast', 'budget forecast', 'revenue forecast'
    ]
    if any(keyword in question_lower for keyword in forecast_keywords):
        return "FORECAST"
    
    # 4. Check if question needs FINANCIAL METRICS (Financial Analysis Service)
    financial_keywords = [
        'revenue', 'profit', 'margin', 'cash flow', 'balance sheet', 'income statement',
        'financial performance', 'operational', 'efficiency', 'growth', 'decline',
        'quarterly', 'monthly', 'yearly', 'annual', 'kpi', 'key performance', 
        'dashboard', 'overview', 'trends', 'trend', 'analysis', 'analytics', 
        'performance', 'metrics', 'financial analysis', 'customer data', 'customer analysis'
    ]
    if any(keyword in question_lower for keyword in financial_keywords):
        return "FINANCIAL_ANALYSIS"
    
    # 5. Default to Financial Analysis for ambiguous questions
    return "FINANCIAL_ANALYSIS"

def is_document_question(question):
    """
    Legacy function for backward compatibility.
    Now uses Data Source-Based routing internally.
    
    Args:
        question (str): User question
        
    Returns:
        bool: True if it's a document question
    """
    return get_question_data_source(question) == "RAG_DOCUMENT"
