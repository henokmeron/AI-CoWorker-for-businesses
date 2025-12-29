"""
Streamlit frontend for AI Assistant Coworker - ChatGPT-style interface.
Properly structured like ChatGPT with sidebar avatar, prompt-area file attachment, and dropdown menus.
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
# Backend is on Fly.io - update this if your Fly.io app name is different
BACKEND_URL = os.getenv("BACKEND_URL", "https://ai-coworker-for-businesses.fly.dev")
API_KEY = os.getenv("API_KEY", "ai-coworker-secret-key-2024")

# Set page config
st.set_page_config(
    page_title="AI Assistant Coworker",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
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
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "show_edit_gpt" not in st.session_state:
    st.session_state.show_edit_gpt = False
if "editing_gpt_id" not in st.session_state:
    st.session_state.editing_gpt_id = None
if "reply_as_me" not in st.session_state:
    st.session_state.reply_as_me = False
if "show_auth_dropdown" not in st.session_state:
    st.session_state.show_auth_dropdown = False
if "show_file_upload" not in st.session_state:
    st.session_state.show_file_upload = False
# CRITICAL: Force hide file uploader on initial load
if not st.session_state.get("_file_upload_initialized", False):
    st.session_state.show_file_upload = False
    st.session_state._file_upload_initialized = True
if "gpt_dropdown_open" not in st.session_state:
    st.session_state.gpt_dropdown_open = {}
if "chat_history_loaded" not in st.session_state:
    st.session_state.chat_history_loaded = False
if "upload_counter" not in st.session_state:
    st.session_state.upload_counter = 0

# Custom CSS - ChatGPT-style with PROPER fixes
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* CRITICAL FIX 1: Chat input at bottom - PROPER implementation with sidebar support */
    /* Streamlit sidebar is typically 21rem (336px) when open */
    section[data-testid="stMain"] {
        padding-bottom: 120px !important;
    }
    
    /* Target the actual chat input container that Streamlit creates */
    /* CRITICAL: Use calc() to properly center and account for sidebar */
    div[data-testid="stChatInputContainer"],
    div[data-testid="stChatInput"],
    div[data-testid="stChatInputContainer"] > div,
    form[data-testid="stChatInputForm"],
    div[data-testid="stChatInputContainer"] > form {
        position: fixed !important;
        bottom: 0 !important;
        left: 21rem !important; /* Start after sidebar when open */
        right: 0 !important;
        background: #202123 !important;
        padding: 1rem !important;
        padding-right: 2rem !important; /* Extra padding to ensure send button is visible */
        z-index: 999 !important;
        border-top: 3px solid #ffffff !important; /* WHITE BORDER as requested */
        border-left: 2px solid #343541 !important;
        box-shadow: 0 -4px 12px rgba(0,0,0,0.3) !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        max-width: calc(100% - 21rem) !important; /* Ensure it doesn't overflow */
    }
    
    /* When sidebar is collapsed, adjust left position and max-width */
    section[data-testid="stSidebar"][aria-expanded="false"] ~ div[data-testid="stAppViewContainer"] 
    div[data-testid="stChatInputContainer"],
    section[data-testid="stSidebar"][aria-expanded="false"] ~ div[data-testid="stAppViewContainer"] 
    form[data-testid="stChatInputForm"] {
        left: 0 !important; /* Full width when sidebar closed */
        max-width: 100% !important;
    }
    
    /* Ensure the input field and send button are properly contained */
    div[data-testid="stChatInputContainer"] > div,
    form[data-testid="stChatInputForm"] > div {
        width: 100% !important;
        max-width: 100% !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }
    
    /* Ensure send button is always visible */
    div[data-testid="stChatInputContainer"] button,
    form[data-testid="stChatInputForm"] button {
        flex-shrink: 0 !important;
        min-width: auto !important;
    }
    
    /* Ensure main content doesn't overlap with fixed input */
    .main .block-container,
    section[data-testid="stMain"] > div:first-child {
        padding-bottom: 150px !important;
    }
    
    /* CRITICAL FIX 2: Chat message alignment - User RIGHT, AI LEFT with center line */
    /* Center line to separate user and AI messages - positioned relative to main content */
    section[data-testid="stMain"] {
        position: relative;
    }
    section[data-testid="stMain"]::before {
        content: '';
        position: fixed;
        left: calc(21rem + 50%);
        top: 0;
        bottom: 120px;
        width: 2px;
        background: linear-gradient(to bottom, transparent, #565869 10%, #565869 90%, transparent);
        z-index: 0;
        pointer-events: none;
        transform: translateX(-50%);
    }
    
    /* When sidebar is collapsed, adjust center line */
    section[data-testid="stSidebar"][aria-expanded="false"] ~ div[data-testid="stAppViewContainer"] 
    section[data-testid="stMain"]::before {
        left: 50%;
    }
    
    /* Target ALL chat message containers - use more specific selectors */
    div[data-testid="stChatMessage"] {
        display: flex !important;
        width: 100% !important;
        margin-bottom: 1.5rem !important;
        position: relative;
        z-index: 1;
    }
    
    /* User messages - align to RIGHT - use multiple selector strategies */
    /* Strategy 1: :has() selector for modern browsers */
    div[data-testid="stChatMessage"]:has(img[alt="user"]),
    div[data-testid="stChatMessage"]:has(img[alt*="User"]),
    div[data-testid="stChatMessage"]:has(img[alt*="user"]) {
        justify-content: flex-end !important;
        flex-direction: row-reverse !important;
    }
    
    /* Strategy 2: Direct child selector - user messages have specific structure */
    div[data-testid="stChatMessage"] > div:first-child:has(img[alt="user"]),
    div[data-testid="stChatMessage"] > div:first-child:has(img[alt*="user"]) {
        order: 2;
    }
    
    /* User message content box - right aligned with proper styling */
    div[data-testid="stChatMessage"]:has(img[alt="user"]) > div:last-child,
    div[data-testid="stChatMessage"]:has(img[alt*="User"]) > div:last-child,
    div[data-testid="stChatMessage"]:has(img[alt*="user"]) > div:last-child,
    div[data-testid="stChatMessage"]:has(img[alt="user"]) > div:nth-child(2),
    div[data-testid="stChatMessage"]:has(img[alt*="user"]) > div:nth-child(2) {
        max-width: 48% !important;
        margin-left: auto !important;
        margin-right: 2% !important;
        background-color: #343541 !important;
        border-radius: 12px 12px 0 12px !important;
        padding: 14px 18px !important;
        text-align: left !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    }
    
    /* Assistant messages - align to LEFT */
    div[data-testid="stChatMessage"]:has(img[alt="assistant"]),
    div[data-testid="stChatMessage"]:has(img[alt*="Assistant"]),
    div[data-testid="stChatMessage"]:has(img[alt*="assistant"]) {
        justify-content: flex-start !important;
        flex-direction: row !important;
    }
    
    /* Assistant message content box - left aligned */
    div[data-testid="stChatMessage"]:has(img[alt="assistant"]) > div:last-child,
    div[data-testid="stChatMessage"]:has(img[alt*="Assistant"]) > div:last-child,
    div[data-testid="stChatMessage"]:has(img[alt*="assistant"]) > div:last-child,
    div[data-testid="stChatMessage"]:has(img[alt="assistant"]) > div:nth-child(2),
    div[data-testid="stChatMessage"]:has(img[alt*="assistant"]) > div:nth-child(2) {
        max-width: 48% !important;
        margin-right: auto !important;
        margin-left: 2% !important;
        background-color: #444654 !important;
        border-radius: 12px 12px 12px 0 !important;
        padding: 14px 18px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    }
    
    /* Fallback: Use attribute selectors and class-based targeting */
    div[data-testid="stChatMessage"][data-message-role="user"],
    div[data-testid="stChatMessage"] [class*="user"] {
        justify-content: flex-end !important;
        flex-direction: row-reverse !important;
    }
    div[data-testid="stChatMessage"][data-message-role="assistant"],
    div[data-testid="stChatMessage"] [class*="assistant"] {
        justify-content: flex-start !important;
        flex-direction: row !important;
    }
    
    /* Additional fallback: Target by message structure */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        /* This is a last resort - will be overridden by more specific selectors */
    }
    
    /* CRITICAL FIX 3: Avatar visibility - HIGHLY VISIBLE with white border */
    /* Target all possible avatar button selectors */
    button[key="sidebar_avatar"],
    div[data-testid="stButton"] > button[key="sidebar_avatar"],
    button[data-baseweb="button"][key="sidebar_avatar"],
    section[data-testid="stSidebar"] button[key="sidebar_avatar"] {
        border-radius: 50% !important;
        width: 60px !important;
        height: 60px !important;
        min-width: 60px !important;
        min-height: 60px !important;
        padding: 0 !important;
        font-size: 24px !important;
        font-weight: 900 !important;
        border: 4px solid #ffffff !important;
        background-color: var(--avatar-bg, #ff6b6b) !important;
        color: #ffffff !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 0 0 3px rgba(255,255,255,0.8), 0 6px 20px rgba(0,0,0,0.8) !important;
        position: relative !important;
        margin: 8px auto !important;
        line-height: 1 !important;
        text-align: center !important;
    }
    
    /* Ensure avatar text/icon is visible */
    button[key="sidebar_avatar"] *,
    button[key="sidebar_avatar"]::before {
        color: #ffffff !important;
        font-weight: 900 !important;
    }
    
    /* Outer glow ring for maximum visibility */
    button[key="sidebar_avatar"]::before {
        content: '';
        position: absolute;
        top: -8px;
        left: -8px;
        right: -8px;
        bottom: -8px;
        border-radius: 50%;
        border: 4px solid #ffffff;
        opacity: 0.9;
        z-index: -1;
        animation: pulse 2s infinite;
        box-shadow: 0 0 10px rgba(255,255,255,0.5);
    }
    
    @keyframes pulse {
        0%, 100% { 
            opacity: 0.9;
            transform: scale(1);
        }
        50% { 
            opacity: 0.7;
            transform: scale(1.05);
        }
    }
    
    button[key="sidebar_avatar"]:hover {
        background-color: var(--avatar-hover, #ee5a5a) !important;
        border-color: #ffffff !important;
        transform: scale(1.1) !important;
        box-shadow: 0 0 0 4px rgba(255,255,255,1), 0 8px 24px rgba(0,0,0,0.9) !important;
    }
    
    /* Force visibility - override any Streamlit defaults */
    button[key="sidebar_avatar"] {
        visibility: visible !important;
        opacity: 1 !important;
    }
    
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
    
    /* GPT dropdown menu */
    .gpt-dropdown {
        position: relative;
        display: inline-block;
    }
    .gpt-dropdown-content {
        display: none;
        position: absolute;
        background-color: #202123;
        min-width: 200px;
        box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
        z-index: 1;
        border: 1px solid #343541;
        border-radius: 8px;
        margin-top: 4px;
    }
    .gpt-dropdown-item {
        color: #ececf1;
        padding: 12px 16px;
        text-decoration: none;
        display: block;
        cursor: pointer;
        border-bottom: 1px solid #343541;
    }
    .gpt-dropdown-item:hover {
        background-color: #343541;
    }
    .gpt-dropdown-item:last-child {
        border-bottom: none;
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
    """Make an API request to the backend."""
    url = f"{BACKEND_URL}{endpoint}"
    headers = kwargs.pop("headers", {})
    headers["X-API-Key"] = API_KEY
    
    # Don't set Content-Type for file uploads (multipart/form-data)
    if "files" not in kwargs:
        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            timeout=60,
            **kwargs
        )
        return response
    except (ConnectionError, Timeout) as e:
        logger.error(f"Connection error: {e}")
        return None
    except Exception as e:
        logger.error(f"Request error: {e}")
        return None


def get_businesses() -> List[Dict[str, Any]]:
    """Get all businesses (GPTs)."""
    response = api_request("GET", "/api/v1/businesses")
    if response and response.status_code == 200:
        return response.json()
    return []


def get_business(business_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific business (GPT)."""
    response = api_request("GET", f"/api/v1/businesses/{business_id}")
    if response and response.status_code == 200:
        return response.json()
    return None


def update_business(business_id: str, name: Optional[str] = None, description: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Update a business (GPT)."""
    data = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if settings is not None:
        data["settings"] = settings
    
    response = api_request("PUT", f"/api/v1/businesses/{business_id}", json=data)
    if response and response.status_code == 200:
        return response.json()
    return None


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
    try:
        # Prepare file for multipart/form-data upload
        if hasattr(file, 'getvalue'):
            file_content = file.getvalue()
            file_name = file.name
            file_type = getattr(file, 'type', None)
        elif hasattr(file, 'read'):
            file_content = file.read()
            if hasattr(file, 'seek'):
                file.seek(0)
            file_name = getattr(file, 'name', 'uploaded_file')
            file_type = getattr(file, 'content_type', None)
        else:
            file_content = file
            file_name = "uploaded_file"
            file_type = None
        
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')
        
        file_tuple = (file_name, file_content, file_type)
        data = {"business_id": business_id}
        files = {"file": file_tuple}
        
        response = api_request("POST", "/api/v1/documents/upload", files=files, data=data)
        if response and response.status_code == 200:
            return response.json()
        elif response:
            error_text = response.text
            logger.error(f"Upload failed: {response.status_code} - {error_text}")
            try:
                error_json = response.json()
                if 'detail' in error_json:
                    return {"error": error_json['detail'], "status_code": response.status_code}
            except:
                return {"error": error_text, "status_code": response.status_code}
        return {"error": "Upload failed: No response from server", "status_code": 0}
    except Exception as e:
        logger.error(f"Exception during upload: {e}", exc_info=True)
        return None


def get_documents(business_id: str) -> List[Dict[str, Any]]:
    """Get documents for a business (GPT)."""
    response = api_request("GET", f"/api/v1/documents?business_id={business_id}")
    if response and response.status_code == 200:
        return response.json()
    return []


def delete_document(business_id: str, document_id: str) -> bool:
    """Delete a document."""
    response = api_request("DELETE", f"/api/v1/documents/{document_id}")
    return response and response.status_code == 200


def chat_query(business_id: Optional[str], query: str, conversation_history: List[Dict[str, Any]], conversation_id: Optional[str] = None, reply_as_me: bool = False) -> Optional[Dict[str, Any]]:
    """Send a chat query."""
    data = {
        "query": query,
        "conversation_history": conversation_history,
        "conversation_id": conversation_id,
        "reply_as_me": reply_as_me
    }
    if business_id:
        data["business_id"] = business_id
    
    response = api_request("POST", "/api/v1/chat", json=data)
    if response and response.status_code == 200:
        return response.json()
    elif response:
        try:
            error_json = response.json()
            return {"error": error_json.get("detail", "Unknown error")}
        except:
            return {"error": response.text}
    return {"error": "No response from server"}


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


def get_user_initials():
    """Get user initials for avatar."""
    if st.session_state.user_logged_in and st.session_state.user_name:
        name = st.session_state.user_name
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[0].upper() if name else "👤"
    # Return a user icon emoji instead of "?" for better visibility
    return "👤"


def handle_login():
    """Handle user login."""
    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            # Simple login - in production, use proper auth
            if email and password:
                try:
                    response = api_request("POST", "/api/v1/auth/login", json={"email": email, "password": password})
                    if response and response.status_code == 200:
                        result = response.json()
                        st.session_state.user_logged_in = True
                        st.session_state.user_name = result.get("user_name", email.split("@")[0].title())
                        st.session_state.user_email = result.get("user_email", email)
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except Exception as e:
                    logger.error(f"Login error: {e}")
                    st.error("Login failed. Please try again.")


def render_settings():
    """Render settings panel."""
    st.markdown('<div class="main-header">⚙️ Settings</div>', unsafe_allow_html=True)
    
    with st.form("settings_form"):
        st.text_input("Name", value=st.session_state.user_name or "Guest", key="setting_name")
        st.text_input("Email", value=st.session_state.user_email or "", key="setting_email")
        
        if st.form_submit_button("Save"):
            st.session_state.user_name = st.session_state.setting_name
            st.session_state.user_email = st.session_state.setting_email
            st.success("Settings saved!")
            st.rerun()
    
    if st.button("← Back"):
        st.session_state.show_settings = False
        st.rerun()


def render_edit_gpt_panel():
    """Render edit GPT panel."""
    gpt_id = st.session_state.editing_gpt_id
    if not gpt_id:
        st.session_state.show_edit_gpt = False
        st.rerun()
        return
    
    gpt = get_business(gpt_id)
    if not gpt:
        st.error("GPT not found")
        st.session_state.show_edit_gpt = False
        st.rerun()
        return
    
    st.markdown('<div class="main-header">✏️ Edit GPT</div>', unsafe_allow_html=True)
    
    with st.form("edit_gpt_form"):
        name = st.text_input("Name", value=gpt.get("name", ""), key="edit_gpt_name")
        description = st.text_area("Description", value=gpt.get("description", ""), key="edit_gpt_description")
        
        if st.form_submit_button("Save"):
            if update_business(gpt_id, name=name, description=description):
                st.success("GPT updated!")
                st.session_state.show_edit_gpt = False
                st.session_state.editing_gpt_id = None
                st.rerun()
            else:
                st.error("Failed to update GPT")
    
    if st.button("← Back"):
        st.session_state.show_edit_gpt = False
        st.session_state.editing_gpt_id = None
        st.rerun()


# Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">MY GPTS</div>', unsafe_allow_html=True)
    
    # Create GPT button
    if st.button("➕ Create GPT", use_container_width=True, key="create_gpt_btn"):
        name = st.text_input("GPT Name", key="new_gpt_name_input")
        if name:
            new_gpt = create_business(name)
            if new_gpt:
                st.success("GPT created!")
                st.rerun()
    
    # Load and display GPTs
    try:
        gpts = get_businesses()
        st.session_state.gpts = gpts
        
        if gpts:
            for gpt in gpts:
                gpt_id = gpt.get('id')
                gpt_name = gpt.get('name', 'Unnamed GPT')
                is_selected = st.session_state.selected_gpt == gpt_id
                
                col1, col2 = st.columns([8, 1])
                with col1:
                    button_style = "primary" if is_selected else "secondary"
                    if st.button(gpt_name, key=f"gpt_{gpt_id}", use_container_width=True, type=button_style):
                        st.session_state.selected_gpt = gpt_id
                        st.session_state.current_conversation_id = None
                        st.session_state.chat_history = []
                        st.session_state.chat_history_loaded = False
                        st.rerun()
                
                with col2:
                    if st.button("⋮", key=f"gpt_menu_{gpt_id}", help="Options"):
                        st.session_state.gpt_dropdown_open[gpt_id] = not st.session_state.gpt_dropdown_open.get(gpt_id, False)
                        st.rerun()
                
                if st.session_state.gpt_dropdown_open.get(gpt_id, False):
                    st.markdown("---")
                    if st.button("✏️ Edit", key=f"gpt_edit_{gpt_id}", use_container_width=True):
                        st.session_state.editing_gpt_id = gpt_id
                        st.session_state.show_edit_gpt = True
                        st.session_state.gpt_dropdown_open[gpt_id] = False
                        st.rerun()
                    if st.button("🗑️ Delete", key=f"gpt_delete_{gpt_id}", use_container_width=True):
                        # Delete functionality would go here
                        st.info("Delete feature coming soon")
                        st.session_state.gpt_dropdown_open[gpt_id] = False
                        st.rerun()
                    if st.button("✕ Close", key=f"gpt_close_{gpt_id}", use_container_width=True):
                        st.session_state.gpt_dropdown_open[gpt_id] = False
                        st.rerun()
        else:
            st.info("No GPTs yet. Create one to get started!")
    except Exception as e:
        logger.error(f"Error loading GPTs: {e}", exc_info=True)
        st.error(f"Error loading GPTs: {str(e)}")
        st.info("Please check your backend connection and try again.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Bottom section: Conversations
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">Conversations</div>', unsafe_allow_html=True)
    
    # New Chat button - ACTUALLY CREATE A NEW CONVERSATION
    if st.button("➕ New Chat", use_container_width=True, key="new_chat_btn"):
        # CRITICAL: Clear EVERYTHING to prevent chat bleeding
        st.session_state.current_conversation_id = None
        st.session_state.chat_history = []
        st.session_state.chat_history_loaded = False
        
        # Clear processed file flags
        for key in list(st.session_state.keys()):
            if key.startswith("processed_") or key.startswith("show_menu_") or key.startswith("renaming_"):
                del st.session_state[key]
        
        # Create a new conversation on the backend
        business_id = st.session_state.selected_gpt or "temp_chat"
        new_conv_title = f"New Chat {datetime.now().strftime('%I:%M %p')}"
        
        try:
            new_conv = create_conversation(business_id, title=new_conv_title)
            if new_conv:
                st.session_state.current_conversation_id = new_conv.get('id')
                st.session_state.chat_history = []
                st.session_state.chat_history_loaded = False
                
                # CRITICAL: Immediately refresh conversations list
                cache_key = f"conversations_cache_{st.session_state.selected_gpt}"
                try:
                    conversations = get_conversations(business_id=st.session_state.selected_gpt, archived=False)
                    st.session_state[cache_key] = conversations
                    st.session_state.conversations = conversations
                    st.session_state["last_gpt_for_conversations"] = st.session_state.selected_gpt
                    logger.info(f"✅ Created new conversation and refreshed list: {len(conversations)} conversations")
                except Exception as e:
                    logger.warning(f"Could not refresh conversations list: {e}")
            else:
                st.warning("Could not create conversation on server, continuing locally")
        except Exception as e:
            logger.error(f"Error creating new conversation: {e}")
            st.warning("Continuing with local chat (not saved to server)")
        
        st.rerun()
    
    # Load and display conversations
    cache_key = f"conversations_cache_{st.session_state.selected_gpt}"
    last_gpt_key = "last_gpt_for_conversations"
    
    gpt_changed = st.session_state.get(last_gpt_key) != st.session_state.selected_gpt
    has_cache = cache_key in st.session_state and len(st.session_state.get(cache_key, [])) > 0
    
    try:
        if not has_cache or gpt_changed:
            conversations = get_conversations(business_id=st.session_state.selected_gpt, archived=False)
            st.session_state[cache_key] = conversations
            st.session_state[last_gpt_key] = st.session_state.selected_gpt
            st.session_state.conversations = conversations
            logger.info(f"✅ Loaded {len(conversations)} conversations for GPT: {st.session_state.selected_gpt}")
        else:
            conversations = st.session_state.get(cache_key, [])
            st.session_state.conversations = conversations
        
        if conversations:
            for conv in conversations[:20]:
                conv_title = conv.get('title', 'Untitled')
                display_title = conv_title[:30] + "..." if len(conv_title) > 30 else conv_title
                is_current = conv.get('id') == st.session_state.current_conversation_id
                
                col1, col2 = st.columns([8, 1])
                
                with col1:
                    button_style = "primary" if is_current else "secondary"
                    if st.button(display_title, key=f"conv_{conv.get('id')}", use_container_width=True, type=button_style):
                        if st.session_state.current_conversation_id != conv.get('id'):
                            st.session_state.chat_history = []
                            st.session_state.chat_history_loaded = False
                            
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
                                st.session_state.chat_history_loaded = True
                                logger.info(f"✅ Loaded conversation {conv.get('id')} with {len(st.session_state.chat_history)} messages")
                            else:
                                st.session_state.chat_history = []
                                st.session_state.current_conversation_id = conv.get('id')
                                st.session_state.chat_history_loaded = True
                            st.rerun()
                
                with col2:
                    if st.button("⋮", key=f"conv_menu_{conv.get('id')}", help="Options"):
                        st.session_state[f"show_menu_{conv.get('id')}"] = not st.session_state.get(f"show_menu_{conv.get('id')}", False)
                        st.rerun()
                
                if st.session_state.get(f"show_menu_{conv.get('id')}", False):
                    st.markdown("---")
                    if st.button("✏️ Rename", key=f"rename_{conv.get('id')}", use_container_width=True):
                        st.session_state[f"renaming_{conv.get('id')}"] = True
                        st.session_state[f"show_menu_{conv.get('id')}"] = False
                        st.rerun()
                    
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
    
    # Bottom of sidebar: Reply as me toggle and Avatar
    st.markdown("---")
    st.checkbox("Reply as me", value=st.session_state.reply_as_me, key="reply_as_me_toggle", 
                help="Toggle between personalized replies and categorization mode")
    st.session_state.reply_as_me = st.session_state.get("reply_as_me_toggle", False)
    
    # Avatar at bottom-left of sidebar (like ChatGPT) - FIXED AT BOTTOM
    st.markdown("---")
    initials = get_user_initials()
    
    # Avatar button - visible button with initials or user icon
    # Use emoji or initials, never "?"
    avatar_display = initials if initials != "?" else "👤"
    button_type = "primary" if st.session_state.user_logged_in else "secondary"
    
    # Style the button to look like a circular avatar - make it HIGHLY visible
    avatar_bg = '#10a37f' if st.session_state.user_logged_in else '#ff6b6b'
    avatar_hover = '#0d8a6b' if st.session_state.user_logged_in else '#ee5a5a'
    avatar_border = '#ffffff'
    
    # Set CSS variables for avatar styling
    st.markdown(f"""
    <style>
        :root {{
            --avatar-bg: {avatar_bg};
            --avatar-hover: {avatar_hover};
            --avatar-border: {avatar_border};
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Create avatar button with explicit styling
    if st.button(f"{avatar_display}", key="sidebar_avatar", help="Account menu", use_container_width=True, type=button_type):
        st.session_state.show_auth_dropdown = not st.session_state.show_auth_dropdown
        st.rerun()
    
    # Show dropdown menu in sidebar when avatar is clicked
    if st.session_state.show_auth_dropdown:
        st.markdown("---")
        st.markdown("### Account")
        if st.session_state.user_logged_in:
            st.markdown(f"**{st.session_state.user_name or 'User'}**")
            if st.button("⚙️ Settings", key="avatar_settings", use_container_width=True):
                st.session_state.show_settings = True
                st.session_state.show_auth_dropdown = False
                st.rerun()
            if st.button("⬆️ Upgrade", key="avatar_upgrade", use_container_width=True):
                st.info("Upgrade feature coming soon!")
                st.session_state.show_auth_dropdown = False
                st.rerun()
            if st.button("❓ Help", key="avatar_help", use_container_width=True):
                st.info("Help center coming soon!")
                st.session_state.show_auth_dropdown = False
                st.rerun()
            if st.button("🚪 Log out", key="avatar_logout", use_container_width=True):
                st.session_state.user_logged_in = False
                st.session_state.user_name = None
                st.session_state.user_email = None
                st.session_state.show_auth_dropdown = False
                st.rerun()
        else:
            handle_login()


# Main content area
if st.session_state.show_settings:
    render_settings()
elif st.session_state.show_edit_gpt:
    render_edit_gpt_panel()
    st.markdown('<div style="opacity: 0.3;">', unsafe_allow_html=True)
    st.markdown('<div class="main-header">💬 Chat</div>', unsafe_allow_html=True)
    st.info("Close Edit GPT panel to continue chatting")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    # Normal chat view
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
    
    # CRITICAL: Load chat history on page load/refresh if we have a conversation_id
    if st.session_state.current_conversation_id and (not st.session_state.get("chat_history_loaded", False) or len(st.session_state.chat_history) == 0):
        try:
            logger.info(f"🔄 Loading conversation {st.session_state.current_conversation_id}")
            response = api_request("GET", f"/api/v1/conversations/{st.session_state.current_conversation_id}")
            if response and response.status_code == 200:
                loaded_conv = response.json()
                messages = loaded_conv.get("messages", [])
                if messages:
                    st.session_state.chat_history = [
                        {
                            "role": msg.get("role"),
                            "content": msg.get("content"),
                            "sources": msg.get("sources", [])
                        }
                        for msg in messages
                    ]
                    st.session_state.chat_history_loaded = True
                    logger.info(f"✅ Loaded conversation with {len(st.session_state.chat_history)} messages")
                else:
                    st.session_state.chat_history_loaded = True
                    logger.info(f"ℹ️  Conversation {st.session_state.current_conversation_id} is empty")
            else:
                logger.warning(f"⚠️  Could not load conversation {st.session_state.current_conversation_id}")
                st.session_state.chat_history_loaded = True
        except Exception as e:
            logger.error(f"❌ Failed to load conversation: {e}", exc_info=True)
            st.session_state.chat_history_loaded = True
    
    # Chat interface - Display chat history FIRST
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
    
    # File upload area - shown above chat input when "+" button is clicked
    if st.session_state.get("show_file_upload", False):
        with st.container():
            st.markdown('<div class="file-upload-area">', unsafe_allow_html=True)
            upload_key = f"prompt_file_uploader_{st.session_state.get('upload_counter', 0)}"
            uploaded_file = st.file_uploader(
                "📎 Attach file",
                type=["pdf", "docx", "txt", "xlsx", "doc", "xls", "pptx", "csv"],
                key=upload_key,
                help="Supported: PDF, DOCX, TXT, XLSX"
            )
            
            if uploaded_file:
                business_id = st.session_state.selected_gpt or "temp_chat"
                file_key = f"processed_{business_id}_{uploaded_file.name}_{uploaded_file.size}"
                
                if file_key not in st.session_state:
                    st.session_state[file_key] = True
                    with st.spinner(f"Processing {uploaded_file.name}..."):
                        result = upload_document(business_id, uploaded_file)
                        if result and not isinstance(result, dict) or (isinstance(result, dict) and "error" not in result):
                            st.success(f"✅ {uploaded_file.name} processed!")
                            # Add confirmation message to chat
                            confirmation_msg = {
                                "role": "assistant",
                                "content": f"I've processed '{uploaded_file.name}'. You can now ask me questions about it!",
                                "sources": []
                            }
                            st.session_state.chat_history.append(confirmation_msg)
                            
                            # Save confirmation message to backend if we have a conversation
                            if st.session_state.current_conversation_id:
                                try:
                                    api_request("POST", f"/api/v1/conversations/{st.session_state.current_conversation_id}/messages", 
                                              json={"role": "assistant", "content": confirmation_msg["content"], "sources": []})
                                except:
                                    pass
                            
                            st.session_state.upload_counter = st.session_state.get("upload_counter", 0) + 1
                            st.session_state.show_file_upload = False
                            st.rerun()
                        else:
                            error_msg = f"❌ Failed to process {uploaded_file.name}"
                            if isinstance(result, dict) and "error" in result:
                                error_detail = result["error"]
                                error_msg += f"\n\nError: {error_detail}"
                            st.error(error_msg)
                            if file_key in st.session_state:
                                del st.session_state[file_key]
                else:
                    st.info(f"ℹ️ {uploaded_file.name} was already processed.")
                    st.session_state.upload_counter = st.session_state.get("upload_counter", 0) + 1
                    st.session_state.show_file_upload = False
                    st.rerun()
            
            col1, col2 = st.columns([1, 10])
            with col1:
                if st.button("✕", key="close_file_upload_btn", help="Close"):
                    st.session_state.show_file_upload = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
    # CRITICAL FIX: Chat input at bottom with attachment button
    # Use columns to create layout with attachment button
    input_container = st.container()
    with input_container:
        input_cols = st.columns([0.05, 0.95])
        with input_cols[0]:
            if st.button("➕", key="attach_file_btn", help="Attach file", use_container_width=True):
                st.session_state.show_file_upload = not st.session_state.show_file_upload
                st.rerun()
        with input_cols[1]:
            user_query = st.chat_input("Message...")
    
    # Handle chat input
    if user_query:
        # Create conversation if needed
        if not st.session_state.current_conversation_id:
            conv_title = user_query[:50] + "..." if len(user_query) > 50 else user_query
            conv = create_conversation(st.session_state.selected_gpt, title=conv_title)
            if conv:
                st.session_state.current_conversation_id = conv.get("id")
                # Immediately refresh conversations list
                cache_key = f"conversations_cache_{st.session_state.selected_gpt}"
                try:
                    conversations = get_conversations(business_id=st.session_state.selected_gpt, archived=False)
                    st.session_state[cache_key] = conversations
                    st.session_state.conversations = conversations
                    st.session_state["last_gpt_for_conversations"] = st.session_state.selected_gpt
                    logger.info(f"✅ Created new conversation and refreshed list: {len(conversations)} conversations")
                except Exception as e:
                    logger.warning(f"Could not refresh conversations list: {e}")
        
        # Add user message to session state
        user_msg = {
            "role": "user",
            "content": user_query
        }
        st.session_state.chat_history.append(user_msg)
        
        # Save user message to backend immediately
        if st.session_state.current_conversation_id:
            try:
                api_request("POST", f"/api/v1/conversations/{st.session_state.current_conversation_id}/messages",
                          json={"role": "user", "content": user_query, "sources": []})
            except Exception as e:
                logger.warning(f"Could not save user message to backend: {e}")
        
        # Get response - CRITICAL: This must work and display
        with st.spinner("Thinking..."):
            try:
                business_id_for_query = st.session_state.selected_gpt or "temp_chat"
                response = chat_query(
                    business_id_for_query,
                    user_query,
                    st.session_state.chat_history[:-1],
                    st.session_state.current_conversation_id,
                    reply_as_me=st.session_state.reply_as_me
                )
                
                if response and response.get("answer"):
                    assistant_msg = {
                        "role": "assistant",
                        "content": response.get("answer", "I apologize, but I couldn't generate a response."),
                        "sources": response.get("sources", [])
                    }
                    st.session_state.chat_history.append(assistant_msg)
                    
                    # Save assistant message to backend immediately
                    if st.session_state.current_conversation_id:
                        try:
                            api_request("POST", f"/api/v1/conversations/{st.session_state.current_conversation_id}/messages",
                                      json={"role": "assistant", "content": assistant_msg["content"], "sources": assistant_msg.get("sources", [])})
                            logger.info(f"✅ Saved assistant message to conversation {st.session_state.current_conversation_id}")
                        except Exception as e:
                            logger.warning(f"Could not save assistant message to backend: {e}")
                else:
                    error_msg = "Sorry, I encountered an error. Please check the backend logs or try again."
                    if response and isinstance(response, dict) and "error" in response:
                        error_msg = response["error"]
                    assistant_msg = {
                        "role": "assistant",
                        "content": error_msg,
                        "sources": []
                    }
                    st.session_state.chat_history.append(assistant_msg)
                    
                    if st.session_state.current_conversation_id:
                        try:
                            api_request("POST", f"/api/v1/conversations/{st.session_state.current_conversation_id}/messages",
                                      json={"role": "assistant", "content": error_msg, "sources": []})
                        except:
                            pass
            except Exception as e:
                logger.error(f"Chat error: {e}", exc_info=True)
                error_msg = f"Error: {str(e)}"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": error_msg,
                    "sources": []
                })
        
        # CRITICAL: Force rerun to display the response
        st.rerun()
    
    # JavaScript to fix chat input position and chat alignment
    st.markdown("""
    <script>
    (function() {
        function moveChatInputToBottom() {
            // Find Streamlit chat input container
            const chatInput = document.querySelector('div[data-testid="stChatInputContainer"]') || 
                             document.querySelector('form[data-testid="stChatInputForm"]') ||
                             document.querySelector('div[data-testid="stChatInput"]');
            
            // Check if sidebar is open - check multiple ways
            const sidebar = document.querySelector('section[data-testid="stSidebar"]');
            let sidebarOpen = true; // Default to open
            if (sidebar) {
                const expanded = sidebar.getAttribute('aria-expanded');
                const computedStyle = window.getComputedStyle(sidebar);
                sidebarOpen = expanded !== 'false' && computedStyle.display !== 'none' && computedStyle.width !== '0px';
            }
            const sidebarWidth = sidebarOpen ? '21rem' : '0';
            
            if (chatInput) {
                chatInput.style.position = 'fixed';
                chatInput.style.bottom = '0';
                chatInput.style.left = sidebarWidth;
                chatInput.style.right = '0';
                chatInput.style.zIndex = '999';
                chatInput.style.background = '#202123';
                chatInput.style.borderTop = '3px solid #ffffff'; // WHITE BORDER
                chatInput.style.borderLeft = sidebarOpen ? '2px solid #343541' : 'none';
                chatInput.style.padding = '1rem';
                chatInput.style.paddingRight = '2rem'; // Extra padding for send button
                chatInput.style.boxShadow = '0 -4px 12px rgba(0,0,0,0.3)';
                chatInput.style.maxWidth = sidebarOpen ? 'calc(100% - 21rem)' : '100%';
                chatInput.style.display = 'flex';
                chatInput.style.alignItems = 'center';
                
                // Ensure the inner container doesn't overflow
                const innerContainer = chatInput.querySelector('div') || chatInput.querySelector('form');
                if (innerContainer) {
                    innerContainer.style.width = '100%';
                    innerContainer.style.maxWidth = '100%';
                    innerContainer.style.display = 'flex';
                    innerContainer.style.alignItems = 'center';
                    innerContainer.style.gap = '0.5rem';
                }
                
                // Also style the input field itself for visibility
                const inputField = chatInput.querySelector('input') || chatInput.querySelector('textarea');
                if (inputField) {
                    inputField.style.border = '2px solid #565869';
                    inputField.style.borderRadius = '8px';
                    inputField.style.padding = '0.75rem';
                    inputField.style.flex = '1';
                    inputField.style.minWidth = '0'; // Allow shrinking
                }
                
                // Ensure send button is visible and doesn't get cut off
                const sendButton = chatInput.querySelector('button[type="submit"]') || 
                                 chatInput.querySelector('button:has(svg)') ||
                                 Array.from(chatInput.querySelectorAll('button')).find(btn => 
                                     btn.querySelector('svg') || btn.textContent.includes('Send') || btn.textContent.includes('→')
                                 );
                if (sendButton) {
                    sendButton.style.flexShrink = '0';
                    sendButton.style.minWidth = 'auto';
                    sendButton.style.visibility = 'visible';
                    sendButton.style.opacity = '1';
                }
            }
        }
        
        function fixChatAlignment() {
            // Find all chat messages - use more aggressive selection
            const messages = document.querySelectorAll('div[data-testid="stChatMessage"]');
            
            messages.forEach((msg, index) => {
                // Multiple strategies to detect user vs assistant
                // Strategy 1: Check for avatar images
                const userImg = msg.querySelector('img[alt="user"], img[alt*="User"], img[alt*="user"]');
                const assistantImg = msg.querySelector('img[alt="assistant"], img[alt*="Assistant"], img[alt*="assistant"]');
                
                // Strategy 2: Check message structure - user messages often have different structure
                const msgContent = msg.textContent || '';
                const isUserMessage = userImg || 
                                     msg.querySelector('[class*="user"]') ||
                                     (index % 2 === 0 && !assistantImg); // Fallback: even indices might be user
                
                if (userImg || (isUserMessage && !assistantImg)) {
                    // User message - align RIGHT
                    msg.style.display = 'flex';
                    msg.style.justifyContent = 'flex-end';
                    msg.style.flexDirection = 'row-reverse';
                    msg.style.width = '100%';
                    msg.style.marginBottom = '1.5rem';
                    
                    // Find and style the message content box - try multiple selectors
                    let contentBox = msg.querySelector('div:last-child') || 
                                   msg.querySelector('div:nth-child(2)') ||
                                   msg.querySelector('[class*="message"]') ||
                                   Array.from(msg.children).find(child => 
                                       child.tagName === 'DIV' && child.children.length > 0
                                   );
                    
                    if (!contentBox) {
                        // Create a wrapper if needed
                        const textNodes = Array.from(msg.childNodes).filter(node => 
                            node.nodeType === 3 && node.textContent.trim()
                        );
                        if (textNodes.length > 0) {
                            contentBox = document.createElement('div');
                            textNodes.forEach(node => contentBox.appendChild(node.cloneNode(true)));
                            msg.appendChild(contentBox);
                        }
                    }
                    
                    if (contentBox) {
                        contentBox.style.maxWidth = '48%';
                        contentBox.style.marginLeft = 'auto';
                        contentBox.style.marginRight = '2%';
                        contentBox.style.backgroundColor = '#343541';
                        contentBox.style.borderRadius = '12px 12px 0 12px';
                        contentBox.style.padding = '14px 18px';
                        contentBox.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
                        contentBox.style.textAlign = 'left';
                    }
                } else if (assistantImg || (!isUserMessage)) {
                    // Assistant message - align LEFT
                    msg.style.display = 'flex';
                    msg.style.justifyContent = 'flex-start';
                    msg.style.flexDirection = 'row';
                    msg.style.width = '100%';
                    msg.style.marginBottom = '1.5rem';
                    
                    // Find and style the message content box
                    let contentBox = msg.querySelector('div:last-child') || 
                                   msg.querySelector('div:nth-child(2)') ||
                                   msg.querySelector('[class*="message"]') ||
                                   Array.from(msg.children).find(child => 
                                       child.tagName === 'DIV' && child.children.length > 0
                                   );
                    
                    if (!contentBox) {
                        const textNodes = Array.from(msg.childNodes).filter(node => 
                            node.nodeType === 3 && node.textContent.trim()
                        );
                        if (textNodes.length > 0) {
                            contentBox = document.createElement('div');
                            textNodes.forEach(node => contentBox.appendChild(node.cloneNode(true)));
                            msg.appendChild(contentBox);
                        }
                    }
                    
                    if (contentBox) {
                        contentBox.style.maxWidth = '48%';
                        contentBox.style.marginRight = 'auto';
                        contentBox.style.marginLeft = '2%';
                        contentBox.style.backgroundColor = '#444654';
                        contentBox.style.borderRadius = '12px 12px 12px 0';
                        contentBox.style.padding = '14px 18px';
                        contentBox.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
                    }
                }
            });
        }
        
        function fixAvatarVisibility() {
            const avatar = document.querySelector('button[key="sidebar_avatar"]');
            if (avatar) {
                // Get the text content to determine if logged in
                const avatarText = (avatar.textContent || avatar.innerText || '').trim();
                const isLoggedIn = avatarText !== '?' && avatarText !== '👤' && avatarText.length > 0;
                
                avatar.style.borderRadius = '50%';
                avatar.style.width = '60px';
                avatar.style.height = '60px';
                avatar.style.minWidth = '60px';
                avatar.style.minHeight = '60px';
                avatar.style.border = '4px solid #ffffff';
                avatar.style.backgroundColor = isLoggedIn ? '#10a37f' : '#ff6b6b';
                avatar.style.color = '#ffffff';
                avatar.style.fontSize = '24px';
                avatar.style.fontWeight = '900';
                avatar.style.boxShadow = '0 0 0 3px rgba(255,255,255,0.8), 0 6px 20px rgba(0,0,0,0.8)';
                avatar.style.visibility = 'visible';
                avatar.style.opacity = '1';
                avatar.style.display = 'flex';
                avatar.style.alignItems = 'center';
                avatar.style.justifyContent = 'center';
                
                // If it's still showing "?", replace with emoji
                if (avatarText === '?') {
                    avatar.textContent = '👤';
                    avatar.innerHTML = '👤';
                }
            }
        }
        
        function applyAllFixes() {
            moveChatInputToBottom();
            fixChatAlignment();
            fixAvatarVisibility();
        }
        
        // Run immediately
        applyAllFixes();
        
        // Run after delays to catch dynamically loaded elements
        setTimeout(applyAllFixes, 100);
        setTimeout(applyAllFixes, 500);
        setTimeout(applyAllFixes, 1000);
        
        // Also run on mutations
        const observer = new MutationObserver(applyAllFixes);
        observer.observe(document.body, { childList: true, subtree: true });
        
        // Watch for sidebar toggle
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            const sidebarObserver = new MutationObserver(() => {
                setTimeout(applyAllFixes, 100);
            });
            sidebarObserver.observe(sidebar, { attributes: true, attributeFilter: ['aria-expanded'] });
        }
    })();
    </script>
    """, unsafe_allow_html=True)
