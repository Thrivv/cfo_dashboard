import streamlit as st
import requests
import json
import time
from typing import Optional, Dict, Any
import pandas as pd


class RAGService:
    """Service class to interact with RAG API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def health_check(self) -> bool:
        """Check if RAG service is available."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def ingest_document(self, file_content: bytes, filename: str, doc_name: str) -> Dict[str, Any]:
        """Upload and ingest a document into the RAG system."""
        try:
            files = {"file": (filename, file_content, "application/pdf")}
            data = {"doc_name": doc_name}
            
            response = requests.post(
                f"{self.base_url}/ingest",
                files=files,
                data=data,
                timeout=200
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Document ingested successfully"}
            else:
                return {"success": False, "message": f"Error: {response.text}"}
                
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Request timed out. Please try again."}
        except Exception as e:
            return {"success": False, "message": f"Error uploading document: {str(e)}"}
    
    def query_document(self, query: str, template: str = "default") -> Dict[str, Any]:
        """Query the RAG system with a question."""
        try:
            data = {
                "query": query,
                "template": template
            }
            
            response = requests.post(
                f"{self.base_url}/query",
                data=data,
                timeout=200
            )
            
            if response.status_code == 200:
                return {"success": True, "response": response.text}
            else:
                return {"success": False, "message": f"Error: {response.text}"}
                
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Query timed out. Please try again."}
        except Exception as e:
            return {"success": False, "message": f"Error querying document: {str(e)}"}


def format_response_for_display(response_text: str) -> str:
    """Format RAG response for consistent display in Streamlit."""
    if not response_text:
        return "No response received."
    
    # Clean up any inconsistent formatting
    import re
    
    # Remove any markdown formatting
    response_text = re.sub(r'\*\*(.*?)\*\*', r'\1', response_text)  # Remove **bold**
    response_text = re.sub(r'\*(.*?)\*', r'\1', response_text)      # Remove *italic*
    response_text = re.sub(r'_(.*?)_', r'\1', response_text)        # Remove _italic_
    
    # Remove mathematical formulas
    response_text = re.sub(r'[=+\-*/^(){}[\]]+', '', response_text)
    
    # Ensure consistent bullet points
    response_text = re.sub(r'^[\s]*[•·▪▫]\s*', '- ', response_text, flags=re.MULTILINE)
    response_text = re.sub(r'^[\s]*\d+\.\s*', '- ', response_text, flags=re.MULTILINE)
    
    # Clean up whitespace
    response_text = re.sub(r'\s+', ' ', response_text).strip()
    
    return response_text


def render():
    """Render the Document Analysis page with RAG integration."""
    
    st.markdown(
        """
        <style>
        .panel {background: linear-gradient(180deg, rgba(13,13,23,0.92), rgba(6,6,12,0.98)); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 16px;}
        .section-title {color: #e6e9ef; font-size: 1.25rem; font-weight: 700; margin: 0 0 16px;}
        .status-success {color: #28a745; font-weight: 600;}
        .status-error {color: #dc3545; font-weight: 600;}
        .chat-title {color: #e6e9ef; font-size: 1.25rem; font-weight: 700; margin: 0 0 4px;}
        .chat-box {max-height: 420px; overflow-y: auto; padding-right: 6px; transition: max-height .25s ease;}
        .chat-box.empty {min-height: 0; max-height: 0; height: 0; margin: 0; padding: 0; overflow: hidden;}
        .msg {border-radius: 12px; padding: 12px 14px; margin: 8px 0; max-width: 88%;}
        .msg-user {background: linear-gradient(135deg, rgba(148,2,245,0.20), rgba(41,128,185,0.20)); border: 1px solid rgba(148,2,245,0.35); color: #f1f3f5; margin-left: auto;}
        .msg-ai {background: linear-gradient(180deg, rgba(18,18,30,0.95), rgba(12,12,22,0.98)); border: 1px solid rgba(255,255,255,0.08); color: #cfd6dd;}
        .composer textarea {height: 72px !important;}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Initialize RAG service
    rag_service = RAGService()
    
    # Check RAG service status
    if not rag_service.health_check():
        st.markdown('<p class="status-error">Server Offline</p>', unsafe_allow_html=True)
        st.warning("RAG service is not available. Please ensure the RAG containers are running.")
        return
    
    col_main, col_side = st.columns([2.2, 1])
    
    with col_main:
        pass  # No title needed
    
    # Initialize session state
    if 'document_analysis_history' not in st.session_state:
        st.session_state.document_analysis_history = []
    if 'uploaded_documents' not in st.session_state:
        st.session_state.uploaded_documents = []
    if 'current_document' not in st.session_state:
        st.session_state.current_document = None
    if 'processing_query' not in st.session_state:
        st.session_state.processing_query = False
    if 'clear_input' not in st.session_state:
        st.session_state.clear_input = False
    if 'text_area_value' not in st.session_state:
        st.session_state.text_area_value = ""
    
    # Document Upload Section in sidebar
    with col_side:
        st.markdown('<p class="status-success">🟢 Server Online</p>', unsafe_allow_html=True)
        
        with st.expander("Upload Document", expanded=True):
            uploaded_file = st.file_uploader(
                "Choose a PDF file to analyze",
                type=['pdf'],
                help="Upload PDF documents for AI analysis"
            )
            
            if uploaded_file is not None:
                doc_name = st.text_input(
                    "Document Name",
                    value=uploaded_file.name.replace('.pdf', ''),
                    help="Give your document a descriptive name"
                )
                
                if st.button("Ingest Document", type="primary", use_container_width=True):
                    if doc_name.strip():
                        with st.spinner("Processing document..."):
                            result = rag_service.ingest_document(
                                uploaded_file.getvalue(),
                                uploaded_file.name,
                                doc_name.strip()
                            )
                            
                            if result["success"]:
                                st.success("Document ingested successfully!")
                                st.session_state.uploaded_documents.append({
                                    "name": doc_name.strip(),
                                    "filename": uploaded_file.name,
                                    "timestamp": time.time()
                                })
                                st.session_state.current_document = doc_name.strip()
                                st.rerun()
                            else:
                                st.error(f"Error: {result['message']}")
                    else:
                        st.warning("Please enter a document name.")
        
        # Document Management in sidebar
        if st.session_state.uploaded_documents:
            with st.expander("Uploaded Documents", expanded=True):
                for i, doc in enumerate(st.session_state.uploaded_documents):
                    is_current = st.session_state.current_document == doc["name"]
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if is_current:
                            st.markdown(f"**{doc['name']}** (Current)")
                        else:
                            st.markdown(f"{doc['name']}")
                    
                    with col2:
                        if not is_current and st.button("Select", key=f"select_{i}"):
                            st.session_state.current_document = doc["name"]
                            st.rerun()
    
    # Main Chat Area
    with col_main:
        if st.session_state.current_document:
            st.markdown('<div class="panel"><div class="chat-title">Kraya AI Assistant</div>', unsafe_allow_html=True)
            chat_container = st.container()
            
            with chat_container:
                if st.session_state.document_analysis_history:
                    st.markdown('<div class="chat-box">', unsafe_allow_html=True)
                    for question, answer in st.session_state.document_analysis_history:
                        user_msg = f"You ➠ {question}"
                        st.markdown(f"<div class='msg msg-user'>{user_msg}</div>", unsafe_allow_html=True)
                        
                        formatted_answer = format_response_for_display(answer)
                        ai_msg = f"Kraya ⤵<br/>{formatted_answer}"
                        st.markdown(f"<div class='msg msg-ai'>{ai_msg}</div>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="chat-box empty"></div>', unsafe_allow_html=True)
            
            if st.session_state.clear_input:
                st.session_state.text_area_value = ""
                st.session_state.clear_input = False
            
            user_question = st.text_area(
                "Your question", 
                height=72, 
                placeholder="Ask about the uploaded document (e.g., 'What is the net income?', 'Summarize key risks')...", 
                key="question_input", 
                label_visibility="collapsed", 
                value=st.session_state.text_area_value
            )
            st.session_state.text_area_value = user_question
            
            button_disabled = st.session_state.get('processing_query', False) or not st.session_state.current_document
            
            c_send, c_clear = st.columns([1, 1])
            
            with c_send:
                if st.button("Ask to Kraya", type="primary", key="ask_btn", disabled=button_disabled):
                    if user_question.strip() and st.session_state.current_document:
                        st.session_state.processing_query = True
                        st.session_state.clear_input = True
                        with st.spinner("Processing your question..."):
                            result = rag_service.query_document(
                                user_question.strip(),
                                "default"
                            )
                            
                            if result["success"]:
                                st.session_state.document_analysis_history.append((user_question.strip(), result["response"]))
                            else:
                                st.error(f"Error: {result['message']}")
                        st.session_state.processing_query = False
                        st.rerun()
                    else:
                        st.warning("Please upload a document and enter a question.")
            
            with c_clear:
                if st.button("Clear Chat", key="clear_btn", disabled=button_disabled):
                    st.session_state.document_analysis_history = []
                    st.session_state.clear_input = True
                    st.session_state.processing_query = False
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Upload a document above to start asking questions and getting AI-powered analysis.")
    
    
    
