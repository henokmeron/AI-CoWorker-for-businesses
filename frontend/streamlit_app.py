"""
Streamlit frontend for AI Assistant Coworker - ChatGPT-style interface.
"""
import streamlit as st
import requests
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from requests.exceptions import ConnectionError, Timeout, RequestException, HTTPError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "https://ai-coworker-for-businesses.onrender.com")
API_KEY = os.getenv("API_KEY", "ai-coworker-secret-key-2024")

# Set page config
st.set_page_config(
    page_title="AI Assistant Coworker",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - ChatGPT-style
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sidebar styling */
    .sidebar-section {
        margin-bottom: 1.5rem;
    }
    .sidebar-section-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #8e8ea0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
        padding: 0 0.5rem;
    }
    
    /* Chat item styling */
    .chat-item {
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        cursor: pointer;
        word-wrap: break-word;
    }
    .chat-item:hover {
        background-color: #343541;
    }
    
    /* Main content */
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #ffffff;
    }
    
    /* Source boxes */
    .source-box {
        background-color: #343541;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 3px solid #10a37f;
    }
</style>
""", unsafe_allow_html=True)


# Helper functions
def api_request(method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
    """Make API request with authentication."""
    headers = kwargs.pop("headers", {})
    headers["X-API-Key"] = API_KEY
    
    if "json" in kwargs:
        headers["Content-Type"] = "application/json"
    
    url = f"{BACKEND_URL}{endpoint}"
    
    try:
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        if response.status_code >= 400:
            logger.error(f"API Error: {response.status_code} - {response.text}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return None


def get_businesses() -> List[Dict[str, Any]]:
    """Get list of businesses (GPTs)."""
    response = api_request("GET", "/api/v1/businesses")
    if response and response.status_code == 200:
        return response.json()
    return []


def create_business(name: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Create a new business (GPT)."""
    data = {"name": name}
    if description:
        data["description"] = description
    response = api_request("POST", "/api/v1/businesses", json=data)
    if response and response.status_code == 200:
        return response.json()
    return None


def upload_document(business_id: str, file) -> Optional[Dict[str, Any]]:
    """Upload a document to a business (GPT)."""
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"business_id": business_id}
    response = api_request("POST", f"/api/v1/documents/upload?business_id={business_id}", files=files, data=data)
    if response and response.status_code == 200:
        return response.json()
    return None


def get_documents(business_id: str) -> List[Dict[str, Any]]:
    """Get documents for a business (GPT)."""
    response = api_request("GET", f"/api/v1/documents?business_id={business_id}")
    if response and response.status_code == 200:
        return response.json()
    return []


def chat_query(business_id: Optional[str], query: str, conversation_history: List[Dict[str, Any]], conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Send a chat query."""
    data = {
        "query": query,
        "conversation_history": conversation_history,
        "conversation_id": conversation_id
    }
    if business_id:
        data["business_id"] = business_id
    
    response = api_request("POST", "/api/v1/chat", json=data)
    if response and response.status_code == 200:
        return response.json()
    return None


def get_conversations(business_id: Optional[str] = None, archived: Optional[bool] = False) -> List[Dict[str, Any]]:
    """Get conversations."""
    params = {}
    if business_id:
        params["business_id"] = business_id
    if archived is not None:
        params["archived"] = str(archived).lower()
    
    response = api_request("GET", "/api/v1/conversations", params=params)
    if response and response.status_code == 200:
        return response.json()
    return []


def create_conversation(business_id: Optional[str], title: str) -> Optional[Dict[str, Any]]:
    """Create a new conversation."""
    data = {"title": title}
    if business_id:
        data["business_id"] = business_id
    response = api_request("POST", "/api/v1/conversations", json=data)
    if response and response.status_code == 200:
        return response.json()
    return None


def rename_conversation(conversation_id: str, new_title: str) -> bool:
    """Rename a conversation."""
    data = {"title": new_title}
    response = api_request("PUT", f"/api/v1/conversations/{conversation_id}", json=data)
    return response and response.status_code == 200


def archive_conversation(conversation_id: str) -> bool:
    """Archive a conversation."""
    response = api_request("POST", f"/api/v1/conversations/{conversation_id}/archive")
    return response and response.status_code == 200


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation."""
    response = api_request("DELETE", f"/api/v1/conversations/{conversation_id}")
    return response and response.status_code == 200


# Initialize session state
if "selected_gpt" not in st.session_state:
    st.session_state.selected_gpt = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "conversations" not in st.session_state:
    st.session_state.conversations = []
if "gpts" not in st.session_state:
    st.session_state.gpts = []


# Sidebar - ChatGPT style
with st.sidebar:
    # Top section: My GPTs
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">My GPTs</div>', unsafe_allow_html=True)
    
    # New GPT button
    if st.button("➕ Create GPT", use_container_width=True, key="new_gpt_btn"):
        st.session_state.show_create_gpt = True
        st.rerun()
    
    # Show create GPT form if needed
    if st.session_state.get("show_create_gpt", False):
        with st.form("create_gpt_form"):
            gpt_name = st.text_input("GPT Name", key="gpt_name_input")
            gpt_desc = st.text_area("Description (optional)", key="gpt_desc_input")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Create", use_container_width=True):
                    if gpt_name:
                        gpt = create_business(gpt_name, gpt_desc)
                        if gpt:
                            st.success("GPT created!")
                            st.session_state.show_create_gpt = False
                            st.rerun()
                    else:
                        st.error("Please enter a name")
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_create_gpt = False
                    st.rerun()
    
    # Load and display GPTs
    try:
        gpts = get_businesses()
        st.session_state.gpts = gpts
        
        if gpts:
            for gpt in gpts:
                gpt_name = gpt.get('name', 'Untitled')
                display_name = gpt_name[:30] + "..." if len(gpt_name) > 30 else gpt_name
                is_selected = st.session_state.selected_gpt == gpt.get('id')
                
                # GPT button
                button_style = "primary" if is_selected else "secondary"
                if st.button(display_name, key=f"gpt_{gpt.get('id')}", use_container_width=True, type=button_style):
                    st.session_state.selected_gpt = gpt.get('id')
                    st.session_state.chat_history = []
                    st.session_state.current_conversation_id = None
                    st.rerun()
        else:
            st.info("No GPTs yet. Create one to get started!")
    except Exception as e:
        logger.error(f"Error loading GPTs: {e}")
        st.warning("Error loading GPTs")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Bottom section: Conversations
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">Conversations</div>', unsafe_allow_html=True)
    
    # New Chat button
    if st.button("➕ New Chat", use_container_width=True, key="new_chat_btn"):
        st.session_state.chat_history = []
        st.session_state.current_conversation_id = None
        st.rerun()
    
    # Load and display conversations
    try:
        # Get conversations (use selected GPT if available, otherwise all conversations)
        conversations = get_conversations(
            business_id=st.session_state.selected_gpt,
            archived=False
        )
        st.session_state.conversations = conversations
        
        if conversations:
            for conv in conversations[:20]:  # Show last 20
                conv_title = conv.get('title', 'Untitled')
                display_title = conv_title[:30] + "..." if len(conv_title) > 30 else conv_title
                is_current = conv.get('id') == st.session_state.current_conversation_id
                
                # Conversation button with menu
                col1, col2 = st.columns([8, 1])
                
                with col1:
                    button_style = "primary" if is_current else "secondary"
                    if st.button(display_title, key=f"conv_{conv.get('id')}", use_container_width=True, type=button_style):
                        # Load conversation
                        response = api_request("GET", f"/api/v1/conversations/{conv.get('id')}")
                        if response and response.status_code == 200:
                            loaded_conv = response.json()
                            st.session_state.chat_history = [
                                {
                                    "role": msg.get("role"),
                                    "content": msg.get("content"),
                                    "sources": msg.get("sources", [])
                                }
                                for msg in loaded_conv.get("messages", [])
                            ]
                            st.session_state.current_conversation_id = conv.get('id')
                            st.rerun()
                
                with col2:
                    # Three-dot menu
                    menu_key = f"menu_{conv.get('id')}"
                    if st.button("⋯", key=menu_key, help="More options"):
                        st.session_state[f"show_menu_{conv.get('id')}"] = True
                        st.rerun()
                
                # Show menu if active
                if st.session_state.get(f"show_menu_{conv.get('id')}", False):
                    if st.button("✏️ Rename", key=f"rename_{conv.get('id')}"):
                        st.session_state[f"renaming_{conv.get('id')}"] = True
                        st.session_state[f"show_menu_{conv.get('id')}"] = False
                        st.rerun()
                    
                    if st.button("📦 Archive", key=f"arch_{conv.get('id')}"):
                        if archive_conversation(conv.get('id')):
                            st.success("Archived!")
                            st.session_state[f"show_menu_{conv.get('id')}"] = False
                            st.rerun()
                    
                    if st.button("🗑️ Delete", key=f"del_{conv.get('id')}", type="secondary"):
                        if delete_conversation(conv.get('id')):
                            st.success("Deleted!")
                            st.session_state[f"show_menu_{conv.get('id')}"] = False
                            st.rerun()
                    
                    if st.button("✕ Close", key=f"close_{conv.get('id')}"):
                        st.session_state[f"show_menu_{conv.get('id')}"] = False
                        st.rerun()
                
                # Handle rename
                if st.session_state.get(f"renaming_{conv.get('id')}", False):
                    new_title = st.text_input("New name:", value=conv_title, key=f"rename_input_{conv.get('id')}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✓", key=f"save_rename_{conv.get('id')}"):
                            if new_title and new_title.strip():
                                if rename_conversation(conv.get('id'), new_title.strip()):
                                    st.success("Renamed!")
                                    st.session_state[f"renaming_{conv.get('id')}"] = False
                                    st.rerun()
                    with col2:
                        if st.button("✕", key=f"cancel_rename_{conv.get('id')}"):
                            st.session_state[f"renaming_{conv.get('id')}"] = False
                            st.rerun()
        else:
            st.info("No conversations yet. Start chatting!")
    except Exception as e:
        logger.error(f"Error loading conversations: {e}")
        st.warning("Error loading conversations")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Settings at bottom
    st.markdown("---")
    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.show_settings = True


# Main content
st.markdown('<div class="main-header">💬 Chat</div>', unsafe_allow_html=True)

# Check backend connection
try:
    health_response = api_request("GET", "/health")
    if not health_response or health_response.status_code != 200:
        st.error(f"⚠️ Backend is not responding. Check if it's running at {BACKEND_URL}")
        st.stop()
except Exception as e:
    st.error(f"⚠️ Cannot connect to backend: {e}")
    st.stop()

# Chat interface
chat_container = st.container()

# Display chat history
with chat_container:
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])
                
                # Show sources if available
                if "sources" in msg and msg["sources"]:
                    with st.expander("📚 Sources"):
                        for i, source in enumerate(msg["sources"], 1):
                            st.markdown(f"""
                            <div class="source-box">
                                <strong>Source {i}: {source['document_name']}</strong>
                                {f"(Page {source['page']})" if source.get('page') else ""}
                                <br>
                                <em>Relevance: {source['relevance_score']:.2%}</em>
                                <br><br>
                                {source['chunk_text']}
                            </div>
                            """, unsafe_allow_html=True)

# File upload (ChatGPT style - plus button above input)
if st.session_state.selected_gpt:
    # GPT mode - upload to GPT
    uploaded_file = st.file_uploader(
        "➕ Attach file",
        type=None,
        key="gpt_file_uploader",
        help="Upload a document to this GPT"
    )
    
    if uploaded_file:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            result = upload_document(st.session_state.selected_gpt, uploaded_file)
            if result:
                st.success(f"✅ {uploaded_file.name} processed! Ask questions about it.")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"I've processed '{uploaded_file.name}'. You can now ask me questions about it!",
                    "sources": []
                })
                st.rerun()
            else:
                st.error(f"❌ Failed to process {uploaded_file.name}")
else:
    # Normal chat mode - temporary file upload
    uploaded_file = st.file_uploader(
        "➕ Attach file",
        type=None,
        key="chat_file_uploader",
        help="Attach a temporary file to this chat"
    )
    
    if uploaded_file:
        # For normal chat, we'll use a temporary business ID
        temp_business_id = "temp_chat"
        with st.spinner(f"Processing {uploaded_file.name}..."):
            result = upload_document(temp_business_id, uploaded_file)
            if result:
                st.success(f"✅ {uploaded_file.name} attached! Ask questions about it.")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"I've attached '{uploaded_file.name}'. You can now ask me questions about it!",
                    "sources": []
                })
                st.rerun()
            else:
                st.error(f"❌ Failed to process {uploaded_file.name}")

# Chat input
user_query = st.chat_input("Message...")

if user_query:
    # Create conversation if needed
    if not st.session_state.current_conversation_id:
        conv_title = user_query[:50] + "..." if len(user_query) > 50 else user_query
        conv = create_conversation(st.session_state.selected_gpt, title=conv_title)
        if conv:
            st.session_state.current_conversation_id = conv.get("id")
    
    # Add user message
    user_msg = {
        "role": "user",
        "content": user_query
    }
    st.session_state.chat_history.append(user_msg)
    
    # Get response
    with st.spinner("Thinking..."):
        try:
            response = chat_query(
                st.session_state.selected_gpt,
                user_query,
                st.session_state.chat_history[:-1],
                st.session_state.current_conversation_id
            )
            
            if response and response.get("answer"):
                assistant_msg = {
                    "role": "assistant",
                    "content": response.get("answer", "I apologize, but I couldn't generate a response."),
                    "sources": response.get("sources", [])
                }
                st.session_state.chat_history.append(assistant_msg)
            else:
                error_msg = "Sorry, I encountered an error. Please check the backend logs or try again."
                if response and isinstance(response, dict) and "error" in response:
                    error_msg = response["error"]
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": error_msg,
                    "sources": []
                })
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            st.error(f"Error: {str(e)}")
    
    st.rerun()
