"""
Streamlit frontend for AI Assistant Coworker.
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
# Use deployed backend by default (production URL)
BACKEND_URL = os.getenv("BACKEND_URL", "https://ai-coworker-for-businesses.onrender.com")
API_KEY = os.getenv("API_KEY", "ai-coworker-secret-key-2024")

# Set page config
st.set_page_config(
    page_title="AI Assistant Coworker",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Comprehensive styling for professional UI
st.markdown("""
<style>
    /* Main headers */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1f77b4;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    
    /* Source boxes */
    .source-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 3px solid #1f77b4;
    }
    
    /* Sidebar organization */
    .sidebar-section {
        margin-bottom: 1.5rem;
        padding: 0.5rem 0;
    }
    .sidebar-section-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    
    /* Responsive design - prevent text breaking */
    .sidebar-text {
        word-wrap: break-word;
        overflow-wrap: break-word;
        hyphens: auto;
    }
    
    /* Chat menu items */
    .chat-menu-item {
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        word-wrap: break-word;
    }
    
    /* Dropdown fixes */
    .stSelectbox label {
        color: #ffffff !important;
        font-size: 14px !important;
        font-weight: normal !important;
    }
    .stSelectbox > div > div {
        color: #ffffff !important;
        background-color: #262730 !important;
    }
    div[data-baseweb="select"] > div {
        color: #ffffff !important;
    }
    
    /* File upload button styling */
    .file-upload-button {
        display: inline-block;
        padding: 0.5rem;
        cursor: pointer;
    }
    
    /* Responsive media queries */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.8rem;
        }
        .sidebar-section {
            margin-bottom: 1rem;
        }
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# Helper functions
def api_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """Make API request with authentication."""
    headers = kwargs.pop("headers", {})
    headers["X-API-Key"] = API_KEY
    
    # Only set Content-Type for JSON requests
    if "json" in kwargs:
        headers["Content-Type"] = "application/json"
    
    url = f"{BACKEND_URL}{endpoint}"
    
    try:
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        
        if response.status_code >= 400:
            error_text = response.text
            try:
                error_json = response.json()
                error_text = error_json.get("detail", error_text)
            except:
                pass
            # Don't show error for every request - only log it
            logger.error(f"API Error {response.status_code}: {error_text}")
            # Only show critical errors to user
            if response.status_code >= 500:
                st.error(f"API Error: {error_text}")
        
        return response
    except requests.exceptions.ConnectionError:
        error_msg = f"❌ Cannot connect to backend at {BACKEND_URL}. Is it running?"
        st.error(error_msg)
        logger.error(error_msg)
        return None
    except requests.exceptions.Timeout:
        error_msg = f"❌ Backend timeout. The server is taking too long to respond."
        st.error(error_msg)
        logger.error(error_msg)
        return None
    except Exception as e:
        error_msg = f"❌ Request failed: {str(e)}"
        st.error(error_msg)
        logger.error(error_msg)
        return None


def get_businesses() -> List[Dict[str, Any]]:
    """Get list of businesses."""
    try:
        response = api_request("GET", "/api/v1/businesses")
        if response and response.status_code == 200:
            businesses = response.json()
            return businesses if isinstance(businesses, list) else []
        return []
    except Exception as e:
        st.error(f"Error fetching businesses: {str(e)}")
        return []


def create_business(name: str, description: str = "") -> bool:
    """Create a new business."""
    try:
        response = api_request(
            "POST",
            "/api/v1/businesses",
            json={"name": name, "description": description}
        )
        if response and response.status_code == 200:
            return True
        return False
    except Exception as e:
        st.error(f"Error creating business: {str(e)}")
        return False


def upload_document(business_id: str, file) -> Dict[str, Any]:
    """Upload a document."""
    try:
        files = {"file": (file.name, file, file.type)}
        data = {"business_id": business_id}
        
        response = api_request(
            "POST",
            "/api/v1/documents/upload",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error uploading document: {str(e)}")
        return None


def get_documents(business_id: str) -> List[Dict[str, Any]]:
    """Get documents for a business."""
    try:
        response = api_request(
            "GET",
            f"/api/v1/documents?business_id={business_id}"
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching documents: {str(e)}")
        return []


def chat_query(business_id: str, query: str, history: List = None) -> Dict[str, Any]:
    """Send a chat query."""
    try:
        # Convert history to proper format
        formatted_history = []
        if history:
            for msg in history:
                formatted_history.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        payload = {
            "business_id": business_id,
            "query": query,
            "conversation_history": formatted_history,
            "conversation_id": st.session_state.get("current_conversation_id"),  # Pass conversation_id
            "max_sources": 5
        }
        
        logger.info(f"Sending chat request to {BACKEND_URL}/api/v1/chat")
        response = api_request(
            "POST",
            "/api/v1/chat",
            json=payload
        )
        
        if response and response.status_code == 200:
            result = response.json()
            logger.info(f"Chat response received: {len(result.get('answer', ''))} chars")
            return result
        elif response:
            error_text = response.text
            try:
                error_json = response.json()
                error_text = error_json.get("detail", error_text)
            except:
                pass
            logger.error(f"Chat error {response.status_code}: {error_text}")
            st.error(f"Chat error: {error_text}")
        else:
            logger.error("No response from chat endpoint")
            st.error("No response from backend. Check if backend is running.")
        return None
    except Exception as e:
        logger.error(f"Error in chat query: {e}", exc_info=True)
        st.error(f"Error in chat query: {str(e)}")
        return None


def get_conversations(business_id: str, archived: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Get conversations for a business."""
    try:
        params = {"business_id": business_id}
        if archived is True:
            params["archived"] = "true"
        elif archived is False:
            params["archived"] = "false"
        # If archived is None, don't include the parameter (get all)
        
        response = api_request("GET", "/api/v1/conversations", params=params)
        if response and response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return []


def create_conversation(business_id: str, title: str = None) -> Dict[str, Any]:
    """Create a new conversation."""
    try:
        response = api_request(
            "POST",
            "/api/v1/conversations",
            json={"business_id": business_id, "title": title}
        )
        if response and response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        return None


def archive_conversation(conversation_id: str) -> bool:
    """Archive a conversation."""
    try:
        response = api_request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/archive"
        )
        return response and response.status_code == 200
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        return False


def unarchive_conversation(conversation_id: str) -> bool:
    """Unarchive a conversation."""
    try:
        response = api_request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/unarchive"
        )
        return response and response.status_code == 200
    except Exception as e:
        logger.error(f"Error unarchiving conversation: {e}")
        return False


def rename_conversation(conversation_id: str, new_title: str) -> bool:
    """Rename a conversation."""
    try:
        response = api_request(
            "PUT",
            f"/api/v1/conversations/{conversation_id}",
            json={"title": new_title}
        )
        return response and response.status_code == 200
    except Exception as e:
        logger.error(f"Error renaming conversation: {e}")
        return False


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation permanently."""
    try:
        response = api_request(
            "DELETE",
            f"/api/v1/conversations/{conversation_id}"
        )
        return response and response.status_code == 200
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return False


def unarchive_conversation(conversation_id: str) -> bool:
    """Unarchive a conversation."""
    try:
        response = api_request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/unarchive"
        )
        return response and response.status_code == 200
    except Exception as e:
        logger.error(f"Error unarchiving conversation: {e}")
        return False


def rename_conversation(conversation_id: str, new_title: str) -> bool:
    """Rename a conversation."""
    try:
        response = api_request(
            "PUT",
            f"/api/v1/conversations/{conversation_id}",
            json={"title": new_title}
        )
        return response and response.status_code == 200
    except Exception as e:
        logger.error(f"Error renaming conversation: {e}")
        return False


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation permanently."""
    try:
        response = api_request(
            "DELETE",
            f"/api/v1/conversations/{conversation_id}"
        )
        return response and response.status_code == 200
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return False


def delete_document(document_id: str) -> bool:
    """Delete a document."""
    try:
        response = api_request(
            "DELETE",
            f"/api/v1/documents/{document_id}"
        )
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error deleting document: {str(e)}")
        return False


# Initialize session state
if "selected_business" not in st.session_state:
    st.session_state.selected_business = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "Chat"
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "conversations" not in st.session_state:
    st.session_state.conversations = []
if "chat_type" not in st.session_state:
    st.session_state.chat_type = "business"  # Default to business chat


# Sidebar - Reorganized with clear sections
with st.sidebar:
    st.markdown("## 🤖 AI Assistant Coworker")
    st.markdown("---")
    
    # SECTION 1: Navigation (Top)
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">Navigation</div>', unsafe_allow_html=True)
    page = st.radio(
        "",
        ["Chat", "Documents", "Business Settings"],
        key="nav_radio",
        label_visibility="collapsed"
    )
    st.session_state.current_page = page
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # SECTION 2: Active Business (Middle)
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">Active Business</div>', unsafe_allow_html=True)
    
    # Always try to get businesses, but handle errors gracefully
    try:
        businesses = get_businesses()
    except Exception as e:
        logger.error(f"Error loading businesses: {e}")
        businesses = []
        st.warning("Could not load businesses. Check backend connection.")
    
    if businesses and len(businesses) > 0:
        business_options = {b["name"]: b["id"] for b in businesses}
        selected_name = st.selectbox(
            "Select Business",
            options=list(business_options.keys()),
            key="business_select",
            index=0 if business_options else None,
            label_visibility="visible"
        )
        if selected_name:
            st.session_state.selected_business = business_options[selected_name]
            
            # Show business stats
            selected_biz = next((b for b in businesses if b["id"] == st.session_state.selected_business), None)
            if selected_biz:
                st.metric("Documents", selected_biz.get("document_count", 0))
    else:
        st.info("No businesses found. Create one below.")
        if not st.session_state.selected_business:
            st.session_state.selected_business = None
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # SECTION 3: Chat Management (only show on Chat page)
    if st.session_state.current_page == "Chat":
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">Chat Type</div>', unsafe_allow_html=True)
        
        # Quick Chat vs Business Chat selection
        chat_type = st.radio(
            "",
            ["💬 Quick Chat", "🏢 Business Chat"],
            key="chat_type_radio",
            label_visibility="collapsed",
            help="Quick Chat: Temporary, no saving. Business Chat: Saved to business."
        )
        
        # Store chat type in session state
        st.session_state.chat_type = "quick" if "Quick" in chat_type else "business"
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Only show business chat management if Business Chat is selected
        if st.session_state.chat_type == "business" and st.session_state.selected_business:
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-section-title">Business Conversations</div>', unsafe_allow_html=True)
            
            # New Chat button
            if st.button("➕ New Chat", use_container_width=True, help="Start a new business conversation"):
                st.session_state.chat_history = []
                st.session_state.current_conversation_id = None
                st.rerun()
        
            # Load conversations list
            try:
                conversations = get_conversations(st.session_state.selected_business, archived=False)
                if conversations:
                    st.markdown("#### Recent Chats")
                    for conv in conversations[:20]:  # Show last 20
                    conv_title = conv.get('title', 'Untitled')
                    # Truncate long titles
                    display_title = conv_title[:25] + "..." if len(conv_title) > 25 else conv_title
                    
                    # Highlight current conversation
                    is_current = conv.get('id') == st.session_state.current_conversation_id
                    
                    # Create a row for each chat item with inline menu
                    col_chat, col_dots, col_menu = st.columns([7, 0.5, 2.5])
                    
                    with col_chat:
                        button_label = f"💬 {display_title}" if not is_current else f"▶️ {display_title}"
                        button_style = "primary" if is_current else "secondary"
                        if st.button(button_label, key=f"conv_btn_{conv.get('id')}", use_container_width=True, type=button_style):
                            # Load conversation
                            try:
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
                            except Exception as e:
                                st.error(f"Error loading chat: {e}")
                    
                    with col_dots:
                        # Three-dot menu button
                        menu_key = f"menu_{conv.get('id')}"
                        if st.button("⋯", key=menu_key, help="More options", use_container_width=True):
                            # Toggle menu state
                            current_state = st.session_state.get(f"show_menu_{conv.get('id')}", False)
                            st.session_state[f"show_menu_{conv.get('id')}"] = not current_state
                            st.rerun()
                    
                    # Show inline menu dropdown if active (right next to the chat)
                    with col_menu:
                        if st.session_state.get(f"show_menu_{conv.get('id')}", False):
                            # Simple list of options (like OpenAI) - vertical stack
                            menu_container = st.container()
                            with menu_container:
                                if st.button("✏️ Rename", key=f"rename_btn_{conv.get('id')}", use_container_width=True):
                                    st.session_state[f"renaming_{conv.get('id')}"] = True
                                    st.rerun()
                                
                                if st.button("📦 Archive", key=f"arch_btn_{conv.get('id')}", use_container_width=True):
                                    if archive_conversation(conv.get('id')):
                                        st.success("Archived!")
                                        st.session_state[f"show_menu_{conv.get('id')}"] = False
                                        st.rerun()
                                
                                if st.button("🗑️ Delete", key=f"del_btn_{conv.get('id')}", use_container_width=True, type="secondary"):
                                    if delete_conversation(conv.get('id')):
                                        st.success("Deleted!")
                                        st.session_state[f"show_menu_{conv.get('id')}"] = False
                                        st.rerun()
                                
                                if st.button("✕ Close", key=f"close_menu_{conv.get('id')}", use_container_width=True):
                                    st.session_state[f"show_menu_{conv.get('id')}"] = False
                                    st.rerun()
                            
                            # Handle rename input if needed
                            if st.session_state.get(f"renaming_{conv.get('id')}", False):
                                new_title = st.text_input("New name:", value=conv_title, key=f"rename_input_{conv.get('id')}")
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    if st.button("✓", key=f"save_rename_{conv.get('id')}"):
                                        if new_title and new_title.strip():
                                            if rename_conversation(conv.get('id'), new_title.strip()):
                                                st.success("Renamed!")
                                                st.session_state[f"show_menu_{conv.get('id')}"] = False
                                                st.session_state[f"renaming_{conv.get('id')}"] = False
                                                st.rerun()
                                with col_cancel:
                                    if st.button("✕", key=f"cancel_rename_{conv.get('id')}"):
                                        st.session_state[f"renaming_{conv.get('id')}"] = False
                                        st.rerun()
            else:
                st.info("No previous chats. Start chatting to create one!")
            st.markdown('</div>', unsafe_allow_html=True)
        elif st.session_state.chat_type == "quick":
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-section-title">Quick Chat</div>', unsafe_allow_html=True)
            st.info("💬 Quick chats are temporary and won't be saved. Perfect for quick document questions!")
            if st.button("🔄 New Quick Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.current_conversation_id = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")
            st.warning("Error loading conversations")
    
    st.markdown("---")
    
    # SECTION 4: Create Business (Bottom)
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">Quick Actions</div>', unsafe_allow_html=True)
    with st.expander("➕ Create Business"):
        new_biz_name = st.text_input("Business Name", key="quick_new_biz")
        if st.button("Create", key="quick_create_btn"):
            if new_biz_name:
                if create_business(new_biz_name):
                    st.success(f"Created: {new_biz_name}")
                    st.rerun()
            else:
                st.error("Please enter a name")
    st.markdown('</div>', unsafe_allow_html=True)


# Main content
if st.session_state.current_page == "Chat":
    st.markdown('<div class="main-header">💬 Chat with Your Documents</div>', unsafe_allow_html=True)
    
    # Check backend connection silently (don't show status message)
    try:
        health_response = api_request("GET", "/health")
        if not health_response or health_response.status_code != 200:
            st.error(f"⚠️ Backend is not responding. Check if it's running at {BACKEND_URL}")
            st.warning("""
            **Backend Connection Issue:**
            - Check if the backend is deployed and running on Render
            - Verify the BACKEND_URL is correct
            - If using Render free tier, the backend may be sleeping (first request takes ~30 seconds)
            - Check Render logs for errors
            """)
            st.stop()
    except requests.exceptions.ConnectionError:
        st.error(f"⚠️ Cannot connect to backend at {BACKEND_URL}")
        st.warning("""
        **Backend Connection Issue:**
        - Check if the backend is deployed and running on Render
        - Verify the BACKEND_URL is correct
        - If using Render free tier, the backend may be sleeping (first request takes ~30 seconds)
        - Check Render logs for errors
        """)
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Backend error: {str(e)}")
        st.info(f"Backend URL: {BACKEND_URL}")
        st.stop()
    
    if not st.session_state.selected_business:
        st.warning("Please select or create a business first.")
    else:
        st.markdown('<div class="sub-header">Ask questions about your uploaded documents</div>', unsafe_allow_html=True)
        
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
        
        # ChatGPT-style file attachment: Plus button in prompt field (no drag-and-drop in chat)
        # For Quick Chat, allow file uploads but they'll be temporary
        # For Business Chat, require business selection
        can_upload = (chat_type == "quick") or (chat_type == "business" and st.session_state.selected_business)
        
        if can_upload:
            # File uploader styled as plus button (appears above chat input, like ChatGPT)
            chat_file = st.file_uploader(
                "➕ Attach file",
                type=None,
                key="chat_file_uploader",
                help="Click to attach a file to this chat",
                label_visibility="visible"
            )
            
            if chat_file:
                # Process file immediately when selected
                with st.spinner(f"Processing {chat_file.name}..."):
                    # For Quick Chat, use a temporary business ID; for Business Chat, use selected business
                    upload_business_id = st.session_state.selected_business if st.session_state.selected_business else "quick_temp"
                    result = upload_document(upload_business_id, chat_file)
                    if result:
                        st.success(f"✅ {chat_file.name} processed! Ask questions about it.")
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": f"I've processed '{chat_file.name}'. You can now ask me questions about it!",
                            "sources": []
                        })
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to process {chat_file.name}")
            
            # Chat input (appears right below file button)
            if chat_type == "quick":
                user_query = st.chat_input("Ask a question (Quick Chat - won't be saved)...")
            else:
                user_query = st.chat_input("Ask a question about your documents...")
        else:
            if chat_type == "business":
                user_query = st.chat_input("Please select a business first...", disabled=True)
            else:
                user_query = st.chat_input("Ask a question (Quick Chat)...")
        
        if user_query and st.session_state.selected_business:
            # Create conversation if needed
            if not st.session_state.current_conversation_id:
                conv = create_conversation(
                    st.session_state.selected_business,
                    title=user_query[:50] + "..." if len(user_query) > 50 else user_query
                )
                if conv:
                    st.session_state.current_conversation_id = conv.get("id")
            
            # Add user message immediately
            user_msg = {
                "role": "user",
                "content": user_query
            }
            st.session_state.chat_history.append(user_msg)
            
            # Get response
            with st.spinner("🤔 Thinking..."):
                try:
                    response = chat_query(
                        business_id_for_chat,
                        user_query,
                        st.session_state.chat_history[:-1]  # Exclude the message we just added
                    )
                    
                    if response and response.get("answer"):
                        # Add assistant message
                        assistant_msg = {
                            "role": "assistant",
                            "content": response.get("answer", "I apologize, but I couldn't generate a response."),
                            "sources": response.get("sources", [])
                        }
                        st.session_state.chat_history.append(assistant_msg)
                        
                        # Messages are now automatically saved by backend when conversation_id is provided
                    else:
                        # Get actual error from response
                        error_msg = "Sorry, I encountered an error. Please check the backend logs or try again."
                        if response and isinstance(response, dict) and "error" in response:
                            error_msg = response["error"]
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": error_msg,
                            "sources": []
                        })
                except Exception as e:
                    error_detail = str(e)
                    logger.error(f"Chat error: {error_detail}", exc_info=True)
                    st.error(f"Error: {error_detail}")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"Error: {error_detail}",
                        "sources": []
                    })
            
            st.rerun()


elif st.session_state.current_page == "Documents":
    st.markdown('<div class="main-header">📄 Document Management</div>', unsafe_allow_html=True)
    
    if not st.session_state.selected_business:
        st.warning("Please select or create a business first.")
    else:
        st.markdown('<div class="sub-header">Upload and manage your business documents</div>', unsafe_allow_html=True)
        
        # Upload section
        st.markdown("### Upload Documents")
        st.info("💡 Supported: PDF, DOCX, PPTX, XLSX, CSV, TXT, images (with OCR), and 30+ more file types")
        
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
            type=None,  # Accept all file types
            key="file_uploader"
        )
        
        if uploaded_files:
            if st.button("📤 Upload All"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {file.name}...")
                    result = upload_document(st.session_state.selected_business, file)
                    
                    if result:
                        st.success(f"✅ {file.name}: {result['message']}")
                    else:
                        st.error(f"❌ Failed to upload {file.name}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.text("Upload complete!")
                st.balloons()
        
        st.markdown("---")
        
        # Document list
        st.markdown("### Uploaded Documents")
        documents = get_documents(st.session_state.selected_business)
        
        if documents:
            for doc in documents:
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"📄 **{doc['filename']}**")
                with col2:
                    st.write(f"{doc['file_type'].upper()}")
                with col3:
                    st.write(f"{doc['file_size'] / 1024:.1f} KB")
                with col4:
                    st.write(f"{doc['chunk_count']} chunks")
                with col5:
                    if st.button("🗑️", key=f"delete_{doc['id']}"):
                        if delete_document(doc['id']):
                            st.success("Deleted!")
                            st.rerun()
        else:
            st.info("No documents uploaded yet. Upload some documents to get started!")


elif st.session_state.current_page == "Business Settings":
    st.markdown('<div class="main-header">⚙️ Business Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage businesses, conversations, and configurations</div>', unsafe_allow_html=True)
    
    # Create tabs for different settings (like OpenAI)
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Businesses", 
        "📦 Archived Chats", 
        "⚙️ General", 
        "🔒 Data Controls", 
        "ℹ️ System Info"
    ])
    
    with tab1:
        # Create new business
        st.markdown("### Create New Business")
        with st.form("create_business_form"):
            biz_name = st.text_input("Business Name *")
            biz_desc = st.text_area("Description (optional)")
            
            submitted = st.form_submit_button("Create Business")
            
            if submitted:
                if biz_name:
                    if create_business(biz_name, biz_desc):
                        st.success(f"✅ Successfully created: {biz_name}")
                        st.rerun()
                else:
                    st.error("Please enter a business name")
        
        st.markdown("---")
        
        # List existing businesses
        st.markdown("### Existing Businesses")
        businesses = get_businesses()
        
        if businesses and len(businesses) > 0:
            for biz in businesses:
                with st.expander(f"🏢 {biz.get('name', 'Unknown')} (ID: {biz.get('id', 'N/A')})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** `{biz.get('id', 'N/A')}`")
                        st.write(f"**Description:** {biz.get('description', 'N/A')}")
                    
                    with col2:
                        st.write(f"**Documents:** {biz.get('document_count', 0)}")
                        created = biz.get('created_at', 'N/A')
                        if created != 'N/A' and len(str(created)) > 10:
                            st.write(f"**Created:** {str(created)[:10]}")
                        else:
                            st.write(f"**Created:** {created}")
        else:
            st.info("No businesses found. Create one above to get started!")
    
    with tab2:
        st.markdown("### 📦 Archived Conversations")
        st.markdown("Conversations you've archived. You can unarchive them to restore them to your chat list.")
        
        if not st.session_state.selected_business:
            st.warning("Please select a business first to view archived conversations.")
        else:
            # Load archived conversations
            try:
                archived_conversations = get_conversations(st.session_state.selected_business, archived=True)
            except Exception as e:
                logger.error(f"Error loading archived conversations: {e}")
                archived_conversations = []
            
            if archived_conversations:
                st.info(f"Found {len(archived_conversations)} archived conversation(s)")
                
                for conv in archived_conversations:
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.write(f"**{conv.get('title', 'Untitled')}**")
                        created = conv.get('created_at', 'N/A')
                        if created and len(str(created)) > 10:
                            st.caption(f"Created: {str(created)[:10]}")
                        st.caption(f"{len(conv.get('messages', []))} messages")
                    
                    with col2:
                        if st.button("📂 Load", key=f"load_arch_{conv.get('id')}"):
                            try:
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
                                    st.success("Chat loaded! Switch to Chat tab to view it.")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error loading chat: {e}")
                    
                    with col3:
                        col_unarch, col_del = st.columns(2)
                        with col_unarch:
                            if st.button("↩️ Unarchive", key=f"unarch_{conv.get('id')}"):
                                if unarchive_conversation(conv.get('id')):
                                    st.success("Unarchived! It will appear in your chat list.")
                                    st.rerun()
                        with col_del:
                            if st.button("🗑️ Delete", key=f"del_arch_{conv.get('id')}", type="secondary"):
                                if delete_conversation(conv.get('id')):
                                    st.success("Deleted!")
                                    st.rerun()
                    
                    st.divider()
            else:
                st.info("No archived conversations yet. Archive a chat from the sidebar to see it here.")
    
    with tab3:
        st.markdown("### ⚙️ General Settings")
        
        # Authentication section (placeholder for OAuth)
        st.markdown("#### 🔐 Authentication")
        st.info("🔜 OAuth 2.0 authentication (Google/Microsoft) coming soon!")
        st.markdown("""
        **Planned Features:**
        - Google OAuth 2.0 login
        - Microsoft OAuth 2.0 login  
        - Persistent sessions across refreshes
        - User profile management
        - Secure API key management
        """)
        
        # User settings placeholder
        st.markdown("---")
        st.markdown("#### 👤 User Preferences")
        st.info("User settings will be available after authentication is implemented.")
        
        st.markdown("---")
        st.markdown("#### Appearance")
        col1, col2 = st.columns(2)
        with col1:
            theme = st.selectbox("Theme", ["Dark", "Light", "Auto"], index=0)
            st.caption("Theme preference (requires page refresh)")
        
        with col2:
            auto_save = st.checkbox("Auto-save conversations", value=True)
            st.caption("Automatically save all conversations to database")
        
        st.markdown("---")
        st.markdown("#### Model Settings")
        model_info = st.info("Using OpenAI GPT-4 Turbo. Model selection coming soon.")
    
    with tab4:
        st.markdown("### 🔒 Data Controls")
        
        st.markdown("#### Export Data")
        if st.button("📥 Export All Conversations", help="Download all conversations as JSON"):
            if st.session_state.selected_business:
                try:
                    conversations = get_conversations(st.session_state.selected_business, archived=None)
                    import json
                    export_data = {
                        "business_id": st.session_state.selected_business,
                        "exported_at": datetime.now().isoformat(),
                        "conversations": [conv for conv in conversations]
                    }
                    st.download_button(
                        label="Download JSON",
                        data=json.dumps(export_data, indent=2, default=str),
                        file_name=f"conversations_export_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
                except Exception as e:
                    st.error(f"Error exporting: {e}")
            else:
                st.warning("Please select a business first")
        
        st.markdown("---")
        st.markdown("#### Delete Data")
        st.warning("⚠️ These actions cannot be undone!")
        
        if st.button("🗑️ Delete All Archived Conversations", type="secondary"):
            if st.session_state.selected_business:
                try:
                    archived = get_conversations(st.session_state.selected_business, archived=True)
                    deleted = 0
                    for conv in archived:
                        if delete_conversation(conv.get('id')):
                            deleted += 1
                    st.success(f"Deleted {deleted} archived conversations")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting: {e}")
            else:
                st.warning("Please select a business first")
    
    with tab5:
        st.markdown("### ℹ️ System Information")
        
        try:
            health_response = api_request("GET", "/health")
            if health_response and health_response.status_code == 200:
                health = health_response.json()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Status", health.get('status', 'unknown'))
                with col2:
                    st.metric("Version", health.get('version', 'unknown'))
            else:
                st.error("Backend not accessible")
        except Exception as e:
            st.error(f"Error connecting to backend: {e}")
        
        st.markdown("---")
        st.markdown("#### Backend Connection")
        st.code(f"Backend URL: {BACKEND_URL}", language=None)
        
        st.markdown("---")
        st.markdown("#### Database")
        if st.session_state.selected_business:
            try:
                all_conv = get_conversations(st.session_state.selected_business, archived=None)
                archived_conv = get_conversations(st.session_state.selected_business, archived=True)
                st.metric("Total Conversations", len(all_conv))
                st.metric("Archived", len(archived_conv))
                st.metric("Active", len(all_conv) - len(archived_conv))
            except:
                st.warning("Could not load conversation statistics")


# Footer (only show in Business Settings, not in chat)
if st.session_state.current_page != "Chat":
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <small>AI Assistant Coworker | Built with FastAPI + Streamlit + LangChain</small>
    </div>
    """, unsafe_allow_html=True)


