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
if "user_settings" not in st.session_state:
    st.session_state.user_settings = {}
if "settings_need_reload" not in st.session_state:
    st.session_state.settings_need_reload = True

# Custom CSS - ChatGPT-style with PROPER fixes
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* CRITICAL FIX 1: Chat input - ONLY fix Container, make inner elements static */
    section[data-testid="stMain"] {
        padding-bottom: 120px !important;
    }
    
    /* ONLY fix the container - this prevents white duplicate bar */
    /* CRITICAL: Force to bottom of viewport */
    div[data-testid="stChatInputContainer"] {
        position: fixed !important;
        bottom: 0 !important;
        top: auto !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: min(980px, calc(100vw - 24px)) !important;
        z-index: 9999 !important;
        background: #202123 !important;
        padding: 1rem !important;
        border-top: 3px solid #ffffff !important;
        box-shadow: 0 -4px 12px rgba(0,0,0,0.3) !important;
        margin: 0 !important;
    }
    
    /* Make inner elements static/transparent to prevent duplication */
    div[data-testid="stChatInput"],
    form[data-testid="stChatInputForm"] {
        position: static !important;
        left: auto !important;
        right: auto !important;
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Prevent horizontal scroll */
    body {
        overflow-x: hidden !important;
    }
    
    /* Ensure main content doesn't overlap with fixed input */
    .main .block-container,
    section[data-testid="stMain"] > div:first-child {
        padding-bottom: 150px !important;
    }
    
    /* CRITICAL FIX 2: Chat message alignment - Custom classes */
    .msg {
        max-width: 48% !important;
        padding: 14px 18px !important;
        border-radius: 12px !important;
        margin-bottom: 1.5rem !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
        word-wrap: break-word !important;
    }
    
    .msg.user {
        margin-left: auto !important;
        margin-right: 2% !important;
        background-color: #343541 !important;
        border-radius: 12px 12px 0 12px !important;
        text-align: left !important;
    }
    
    .msg.ai {
        margin-right: auto !important;
        margin-left: 2% !important;
        background-color: #444654 !important;
        border-radius: 12px 12px 12px 0 !important;
    }
    
    /* CRITICAL FIX 3: Avatar visibility - FORCE BLUE COLOR, HIGHLY VISIBLE */
    /* Target all possible avatar button selectors */
    button[key="sidebar_avatar"],
    div[data-testid="stButton"] > button[key="sidebar_avatar"],
    button[data-baseweb="button"][key="sidebar_avatar"],
    section[data-testid="stSidebar"] button[key="sidebar_avatar"],
    section[data-testid="stSidebar"] button:has-text("👤"),
    section[data-testid="stSidebar"] button:has-text("?"),
    section[data-testid="stSidebar"] button[aria-label*="avatar"],
    section[data-testid="stSidebar"] button[aria-label*="Account"],
    section[data-testid="stSidebar"] button[class*="sidebar_avatar"] {
        border-radius: 50% !important;
        width: 60px !important;
        height: 60px !important;
        min-width: 60px !important;
        min-height: 60px !important;
        padding: 0 !important;
        font-size: 24px !important;
        font-weight: 900 !important;
        border: 4px solid #3b82f6 !important; /* FORCE Blue border */
        background-color: #3b82f6 !important; /* FORCE Blue background - override everything */
        color: #ffffff !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5), 0 6px 20px rgba(0,0,0,0.8) !important;
        position: relative !important;
        margin: 8px auto !important;
        line-height: 1 !important;
        text-align: center !important;
    }
    
    /* Ensure avatar text/icon is visible and never shows "?" */
    button[key="sidebar_avatar"] *,
    button[key="sidebar_avatar"]::before,
    section[data-testid="stSidebar"] button[key="sidebar_avatar"] * {
        color: #ffffff !important;
        font-weight: 900 !important;
    }
    
    /* Force visibility - override any Streamlit defaults */
    button[key="sidebar_avatar"],
    section[data-testid="stSidebar"] button[key="sidebar_avatar"] {
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    button[key="sidebar_avatar"]:hover {
        background-color: var(--avatar-hover, #2563eb) !important; /* Darker blue on hover */
        border-color: #3b82f6 !important;
        transform: scale(1.05) !important;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.8), 0 8px 24px rgba(0,0,0,0.9) !important;
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


def archive_conversation(conversation_id: str) -> bool:
    """Archive a conversation."""
    response = api_request("POST", f"/api/v1/conversations/{conversation_id}/archive")
    return response and response.status_code == 200


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation."""
    response = api_request("DELETE", f"/api/v1/conversations/{conversation_id}")
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


def get_user_settings(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user settings from backend."""
    try:
        response = api_request("GET", f"/api/v1/users/settings?user_id={user_id}")
        if response and response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        return None


def update_user_settings(user_id: str, settings: Dict[str, Any]) -> bool:
    """Update user settings on backend."""
    try:
        response = api_request("PUT", f"/api/v1/users/settings?user_id={user_id}", json=settings)
        return response and response.status_code == 200
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        return False


def render_settings():
    """Render comprehensive settings panel with tabs."""
    # Header with back button
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("←", key="back_to_chat", help="Back to Chat"):
            st.session_state.show_settings = False
            st.rerun()
    with col2:
        st.markdown('<div class="main-header">⚙️ Settings</div>', unsafe_allow_html=True)
    
    # Get user ID (use email or generate one)
    user_id = st.session_state.get("user_email") or st.session_state.get("user_name") or "default_user"
    
    # Load settings from backend or use defaults
    if "user_settings" not in st.session_state or st.session_state.get("settings_need_reload", False):
        settings_data = get_user_settings(user_id)
        if settings_data:
            st.session_state.user_settings = settings_data
        else:
            # Default settings
            st.session_state.user_settings = {
                "language": "English",
                "theme": "Dark",
                "font_size": 14,
                "auto_save_conversations": True,
                "default_model": "gpt-4-turbo-preview",
                "custom_instructions": "",
                "response_style": "Professional",
                "email_notifications": False,
                "browser_notifications": False,
                "desktop_notifications": False,
                "session_timeout_minutes": 1440,
                "two_factor_auth": False,
                "data_retention_days": 365,
                "auto_delete_old_conversations": False,
                "integrations": {},
                "gpt_settings": {}
            }
        st.session_state.settings_need_reload = False
    
    settings = st.session_state.user_settings
    
    # Settings tabs
    tabs = ["General", "GPT Settings", "Personalization", "Notifications", "Data Control", "Security", "Account", "Integrations"]
    selected_tab = st.radio("", tabs, horizontal=True, key="settings_tabs_radio", label_visibility="collapsed")
    st.session_state.settings_tab = selected_tab
    
    st.markdown("---")
    
    # Tab content
    if selected_tab == "General":
        st.subheader("General Settings")
        
        with st.form("general_settings_form"):
            col1, col2 = st.columns(2)
            with col1:
                language = st.selectbox(
                    "Language",
                    ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Chinese", "Japanese", "Korean"],
                    index=["English", "Spanish", "French", "German", "Italian", "Portuguese", "Chinese", "Japanese", "Korean"].index(settings.get("language", "English")) if settings.get("language", "English") in ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Chinese", "Japanese", "Korean"] else 0,
                    key="setting_lang"
                )
                theme = st.selectbox(
                    "Theme",
                    ["Dark", "Light", "Auto"],
                    index=["Dark", "Light", "Auto"].index(settings.get("theme", "Dark")),
                    key="setting_theme"
                )
            with col2:
                font_size = st.slider(
                    "Font Size",
                    12, 20, settings.get("font_size", 14),
                    key="setting_font"
                )
                default_model = st.selectbox(
                    "Default Model",
                    ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
                    index=["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"].index(settings.get("default_model", "gpt-4-turbo-preview")) if settings.get("default_model", "gpt-4-turbo-preview") in ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"] else 0,
                    key="setting_model"
                )
            
            auto_save = st.checkbox(
                "Auto-save conversations",
                value=settings.get("auto_save_conversations", True),
                key="setting_auto_save"
            )
            
            if st.form_submit_button("Save General Settings"):
                update_data = {
                    "language": language,
                    "theme": theme,
                    "font_size": font_size,
                    "default_model": default_model,
                    "auto_save_conversations": auto_save
                }
                if update_user_settings(user_id, update_data):
                    st.session_state.user_settings.update(update_data)
                    st.success("✅ General settings saved!")
                    st.rerun()
                else:
                    st.error("Failed to save settings. Please try again.")
    
    elif selected_tab == "GPT Settings":
        st.subheader("GPT-Specific Settings")
        st.info("Configure settings for individual GPTs/businesses. These override general settings for specific GPTs.")
        
        # Get list of GPTs
        gpts = st.session_state.get("gpts", [])
        if not gpts:
            gpts = get_businesses()
            st.session_state.gpts = gpts
        
        if gpts:
            selected_gpt_id = st.selectbox(
                "Select GPT",
                [gpt.get("id") for gpt in gpts],
                format_func=lambda x: next((gpt.get("name", x) for gpt in gpts if gpt.get("id") == x), x),
                key="gpt_settings_select"
            )
            
            gpt_settings = settings.get("gpt_settings", {}).get(selected_gpt_id, {})
            
            with st.form("gpt_settings_form"):
                gpt_custom_instructions = st.text_area(
                    "Custom Instructions for this GPT",
                    value=gpt_settings.get("custom_instructions", ""),
                    height=100,
                    key="gpt_custom_instructions"
                )
                gpt_response_style = st.selectbox(
                    "Response Style for this GPT",
                    ["Professional", "Casual", "Technical", "Creative"],
                    index=["Professional", "Casual", "Technical", "Creative"].index(gpt_settings.get("response_style", "Professional")) if gpt_settings.get("response_style", "Professional") in ["Professional", "Casual", "Technical", "Creative"] else 0,
                    key="gpt_response_style"
                )
                
                if st.form_submit_button("Save GPT Settings"):
                    gpt_settings_dict = settings.get("gpt_settings", {})
                    gpt_settings_dict[selected_gpt_id] = {
                        "custom_instructions": gpt_custom_instructions,
                        "response_style": gpt_response_style
                    }
                    update_data = {"gpt_settings": gpt_settings_dict}
                    if update_user_settings(user_id, update_data):
                        st.session_state.user_settings.setdefault("gpt_settings", {})[selected_gpt_id] = gpt_settings_dict[selected_gpt_id]
                        st.success("✅ GPT settings saved!")
                        st.rerun()
                    else:
                        st.error("Failed to save GPT settings. Please try again.")
        else:
            st.info("No GPTs available. Create a GPT first.")
    
    elif selected_tab == "Personalization":
        st.subheader("Personalization")
        
        with st.form("personalization_form"):
            custom_instructions = st.text_area(
                "Custom Instructions",
                value=settings.get("custom_instructions", ""),
                height=150,
                help="Provide instructions for how the AI should behave, respond, and format its answers.",
                key="setting_instructions"
            )
            response_style = st.selectbox(
                "Response Style",
                ["Professional", "Casual", "Technical", "Creative"],
                index=["Professional", "Casual", "Technical", "Creative"].index(settings.get("response_style", "Professional")) if settings.get("response_style", "Professional") in ["Professional", "Casual", "Technical", "Creative"] else 0,
                key="setting_style"
            )
            
            if st.form_submit_button("Save Personalization"):
                update_data = {
                    "custom_instructions": custom_instructions,
                    "response_style": response_style
                }
                if update_user_settings(user_id, update_data):
                    st.session_state.user_settings.update(update_data)
                    st.success("✅ Personalization settings saved!")
                    st.rerun()
                else:
                    st.error("Failed to save settings. Please try again.")
    
    elif selected_tab == "Notifications":
        st.subheader("Notification Settings")
        
        with st.form("notifications_form"):
            email_notif = st.checkbox(
                "Email notifications",
                value=settings.get("email_notifications", False),
                key="notif_email"
            )
            browser_notif = st.checkbox(
                "Browser notifications",
                value=settings.get("browser_notifications", False),
                key="notif_browser"
            )
            desktop_notif = st.checkbox(
                "Desktop notifications",
                value=settings.get("desktop_notifications", False),
                key="notif_desktop"
            )
            
            if st.form_submit_button("Save Notification Settings"):
                update_data = {
                    "email_notifications": email_notif,
                    "browser_notifications": browser_notif,
                    "desktop_notifications": desktop_notif
                }
                if update_user_settings(user_id, update_data):
                    st.session_state.user_settings.update(update_data)
                    st.success("✅ Notification settings saved!")
                    st.rerun()
                else:
                    st.error("Failed to save settings. Please try again.")
    
    elif selected_tab == "Data Control":
        st.subheader("Data Control")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export All Data", key="export_data", use_container_width=True):
                st.info("Export functionality coming soon. This will download all your conversations, documents, and settings.")
        
        with col2:
            if st.button("🗑️ Delete All Conversations", key="delete_conversations", use_container_width=True, type="secondary"):
                if st.session_state.get("confirm_delete_conversations", False):
                    # Delete all conversations
                    try:
                        conversations = get_conversations(business_id=st.session_state.selected_gpt)
                        deleted_count = 0
                        for conv in conversations:
                            if delete_conversation(conv.get("id")):
                                deleted_count += 1
                        st.success(f"✅ Deleted {deleted_count} conversations!")
                        st.session_state.conversations = []
                        st.session_state.chat_history = []
                        st.session_state.current_conversation_id = None
                        st.session_state.confirm_delete_conversations = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting conversations: {e}")
                else:
                    st.session_state.confirm_delete_conversations = True
                    st.warning("⚠️ Click again to confirm deletion of all conversations. This cannot be undone!")
        
        st.markdown("---")
        
        with st.form("data_retention_form"):
            data_retention = st.slider(
                "Data Retention Period (days)",
                30, 1095, settings.get("data_retention_days", 365),
                key="data_retention"
            )
            auto_delete = st.checkbox(
                "Auto-delete conversations older than retention period",
                value=settings.get("auto_delete_old_conversations", False),
                key="auto_delete_old"
            )
            
            if st.form_submit_button("Save Data Retention Settings"):
                update_data = {
                    "data_retention_days": data_retention,
                    "auto_delete_old_conversations": auto_delete
                }
                if update_user_settings(user_id, update_data):
                    st.session_state.user_settings.update(update_data)
                    st.success("✅ Data retention settings saved!")
                    st.rerun()
                else:
                    st.error("Failed to save settings. Please try again.")
    
    elif selected_tab == "Security":
        st.subheader("Security Settings")
        
        with st.form("security_form"):
            session_timeout = st.number_input(
                "Session Timeout (minutes)",
                min_value=15,
                max_value=10080,
                value=settings.get("session_timeout_minutes", 1440),
                key="session_timeout"
            )
            two_fa = st.checkbox(
                "Two-Factor Authentication",
                value=settings.get("two_factor_auth", False),
                help="Require a second authentication factor for login",
                key="setting_2fa"
            )
            
            st.markdown("---")
            st.markdown("### Change Password")
            current_password = st.text_input("Current Password", type="password", key="current_password")
            new_password = st.text_input("New Password", type="password", key="new_password")
            confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")
            
            if st.form_submit_button("Save Security Settings"):
                update_data = {
                    "session_timeout_minutes": session_timeout,
                    "two_factor_auth": two_fa
                }
                
                # Handle password change
                if new_password:
                    if new_password != confirm_password:
                        st.error("New passwords do not match!")
                    elif not current_password:
                        st.error("Please enter your current password!")
                    else:
                        st.info("Password change functionality will be implemented with full authentication system.")
                
                if update_user_settings(user_id, update_data):
                    st.session_state.user_settings.update(update_data)
                    st.success("✅ Security settings saved!")
                    st.rerun()
                else:
                    st.error("Failed to save settings. Please try again.")
    
    elif selected_tab == "Account":
        st.subheader("Account Settings")
        
        with st.form("account_form"):
            name = st.text_input(
                "Name",
                value=st.session_state.user_name or "Guest",
                key="setting_name"
            )
            email = st.text_input(
                "Email",
                value=st.session_state.user_email or "",
                key="setting_email"
            )
            
            st.markdown("---")
            st.markdown("### Subscription")
            st.info("💎 Free Plan - Upgrade coming soon!")
            
            if st.form_submit_button("Save Account Settings"):
                st.session_state.user_name = name
                st.session_state.user_email = email
                st.success("✅ Account settings saved!")
                st.rerun()
    
    elif selected_tab == "Integrations":
        st.subheader("App Connectors")
        st.info("Connect your apps to enhance AI capabilities. Integrations coming soon!")
        
        integrations = settings.get("integrations", {})
        
        col1, col2 = st.columns(2)
        with col1:
            gmail_connected = st.checkbox("Gmail", value=integrations.get("gmail", False), key="connector_gmail", disabled=True)
            outlook_connected = st.checkbox("Outlook", value=integrations.get("outlook", False), key="connector_outlook", disabled=True)
            slack_connected = st.checkbox("Slack", value=integrations.get("slack", False), key="connector_slack", disabled=True)
        
        with col2:
            google_drive_connected = st.checkbox("Google Drive", value=integrations.get("google_drive", False), key="connector_gdrive", disabled=True)
            dropbox_connected = st.checkbox("Dropbox", value=integrations.get("dropbox", False), key="connector_dropbox", disabled=True)
            notion_connected = st.checkbox("Notion", value=integrations.get("notion", False), key="connector_notion", disabled=True)
        
        st.info("🔜 Integration features are under development. Stay tuned!")
    
    st.markdown("---")
    if st.button("Close Settings", key="close_settings", use_container_width=True):
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
        
        # CRITICAL: Force-create conversation BEFORE allowing upload/query
        new_conv_title = f"New Chat {datetime.now().strftime('%I:%M %p')}"
        
        try:
            new_conv = create_conversation(st.session_state.selected_gpt, title=new_conv_title)
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
                st.error("Could not create conversation on server. Please try again.")
        except Exception as e:
            logger.error(f"Error creating new conversation: {e}")
            st.error(f"Failed to create conversation: {e}")
        
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
                
                # Show menu options when menu button is clicked - OUTSIDE columns
                if st.session_state.get(f"show_menu_{conv.get('id')}", False):
                    st.markdown("---")
                    if st.button("✏️ Rename", key=f"rename_{conv.get('id')}", use_container_width=True):
                        st.session_state[f"renaming_{conv.get('id')}"] = True
                        st.session_state[f"show_menu_{conv.get('id')}"] = False
                        st.rerun()
                    
                    if st.button("📦 Archive", key=f"archive_{conv.get('id')}", use_container_width=True):
                        if archive_conversation(conv.get('id')):
                            st.success("Conversation archived!")
                            st.session_state[f"show_menu_{conv.get('id')}"] = False
                            # Refresh conversations list
                            cache_key = f"conversations_cache_{st.session_state.selected_gpt}"
                            try:
                                conversations = get_conversations(business_id=st.session_state.selected_gpt, archived=False)
                                st.session_state[cache_key] = conversations
                                st.session_state.conversations = conversations
                            except:
                                pass
                            st.rerun()
                    
                    if st.button("🗑️ Delete", key=f"delete_{conv.get('id')}", use_container_width=True):
                        if delete_conversation(conv.get('id')):
                            st.success("Conversation deleted!")
                            st.session_state[f"show_menu_{conv.get('id')}"] = False
                            # Clear current conversation if it was deleted
                            if st.session_state.current_conversation_id == conv.get('id'):
                                st.session_state.current_conversation_id = None
                                st.session_state.chat_history = []
                            # Refresh conversations list
                            cache_key = f"conversations_cache_{st.session_state.selected_gpt}"
                            try:
                                conversations = get_conversations(business_id=st.session_state.selected_gpt, archived=False)
                                st.session_state[cache_key] = conversations
                                st.session_state.conversations = conversations
                            except:
                                pass
                            st.rerun()
                    
                    if st.button("✕ Close", key=f"close_menu_{conv.get('id')}", use_container_width=True):
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
                    st.markdown("---")
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
    # CRITICAL: Never show "?" - always use emoji or initials
    avatar_display = initials
    if not avatar_display or avatar_display == "?" or avatar_display.strip() == "":
        avatar_display = "👤"
    button_type = "primary" if st.session_state.user_logged_in else "secondary"
    
    # Style the button to look like a circular avatar - FORCE BLUE COLOR
    # Set CSS variables for avatar styling - ALWAYS BLUE with maximum specificity
    st.markdown("""
    <style>
        :root {
            --avatar-bg: #3b82f6;
            --avatar-hover: #2563eb;
            --avatar-border: #3b82f6;
        }
        /* Maximum specificity to override Streamlit defaults */
        section[data-testid="stSidebar"] button[key="sidebar_avatar"],
        section[data-testid="stSidebar"] div[data-testid="stButton"] button[key="sidebar_avatar"],
        button[key="sidebar_avatar"][data-baseweb="button"],
        button[key="sidebar_avatar"] {
            background-color: #3b82f6 !important;
            border: 4px solid #3b82f6 !important;
            background: #3b82f6 !important;
        }
        button[key="sidebar_avatar"]:hover {
            background-color: #2563eb !important;
            background: #2563eb !important;
        }
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
    
    # Display chat history - CUSTOM RENDERING with classes
    with chat_container:
        for msg in st.session_state.chat_history:
            role = msg["role"]
            content = msg["content"]
            msg_class = "user" if role == "user" else "ai"
            
            # CRITICAL: Strip any raw HTML source boxes from content - AGGRESSIVE CLEANING
            import re
            # Remove source-box divs with flexible whitespace matching
            content = re.sub(r'<div\s+class\s*=\s*["\']source-box["\']>.*?</div>', '', content, flags=re.DOTALL | re.IGNORECASE)
            # Also match without quotes
            content = re.sub(r'<div\s+class\s*=\s*source-box>.*?</div>', '', content, flags=re.DOTALL | re.IGNORECASE)
            # Remove any remaining source-box content (in case div tags are malformed)
            content = re.sub(r'<strong>Source\s+\d+.*?</strong>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<em>Relevance:.*?</em>', '', content, flags=re.DOTALL | re.IGNORECASE)
            # Remove Sources emoji and text
            content = re.sub(r'📚\s*Sources?\s*', '', content, flags=re.IGNORECASE)
            content = re.sub(r'<details.*?Sources?.*?</details>', '', content, flags=re.DOTALL | re.IGNORECASE)
            # Remove ALL HTML tags (aggressive - strip everything)
            content = re.sub(r'<[^>]+>', '', content)
            # Clean up extra whitespace and newlines
            content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
            content = re.sub(r'\s{3,}', ' ', content)  # Multiple spaces to single
            content = content.strip()
            
            # ✅ Do NOT render sources inside the chat bubble (prevents <div class="source-box">… output)
            # Sources are kept in msg["sources"] for potential future use, but not displayed in chat UI
            sources_html = ""
            
            # Escape HTML in content
            import html
            escaped_content = html.escape(content).replace('\n', '<br>')
            
            st.markdown(f"""
            <div class="msg {msg_class}">
                {escaped_content}
            </div>
            """, unsafe_allow_html=True)
    
    # File upload area - compact, ChatGPT-style sidebar
    if st.session_state.get("show_file_upload", False):
        # Use a compact sidebar-style container instead of full width
        with st.container():
            # Compact upload area
            st.markdown('<div style="max-width: 400px; margin: 0 auto;">', unsafe_allow_html=True)
            upload_key = f"prompt_file_uploader_{st.session_state.get('upload_counter', 0)}"
            uploaded_file = st.file_uploader(
                "📎 Attach file",
                type=["pdf", "docx", "txt", "xlsx", "doc", "xls", "pptx", "csv"],
                key=upload_key,
                help="Supported: PDF, DOCX, TXT, XLSX, CSV"
            )
            
            # Process file immediately when uploaded (don't store file object - not serializable)
            if uploaded_file:
                upload_state_key = f"pending_upload_{upload_key}"
                # Check if this exact file is already being processed
                if upload_state_key not in st.session_state:
                    # Store file info (not the object itself)
                    st.session_state[upload_state_key] = {
                        "name": uploaded_file.name,
                        "size": uploaded_file.size,
                        "processed": False
                    }
                
                upload_info = st.session_state[upload_state_key]
                
                # Process if not already processed
                if not upload_info["processed"]:
                    # CRITICAL FIX: Force conversation_id before upload
                    if not st.session_state.current_conversation_id:
                        # Create conversation immediately
                        conv_title = f"Chat {datetime.now().strftime('%I:%M %p')}"
                        conv = create_conversation(st.session_state.selected_gpt, title=conv_title)
                        if conv:
                            st.session_state.current_conversation_id = conv.get("id")
                    
                    # Use conversation_id as business_id for document isolation
                    if not st.session_state.current_conversation_id:
                        st.error("Please start a conversation first before uploading documents.")
                        # Clear pending upload
                        if upload_state_key in st.session_state:
                            del st.session_state[upload_state_key]
                        st.stop()  # Stop execution instead of return
                    
                    business_id = st.session_state.current_conversation_id
                    file_key = f"processed_{business_id}_{upload_info['name']}_{upload_info['size']}"
                    
                    # Log for debugging
                    logger.info(f"Processing upload: {upload_info['name']} for business_id={business_id}")
                    
                    if file_key not in st.session_state:
                        # Mark as processing immediately to prevent duplicate processing
                        st.session_state[upload_state_key]["processed"] = True
                        
                        # Process file immediately (file object is available now)
                        with st.spinner(f"📤 Uploading and processing {upload_info['name']}... This may take a moment."):
                            try:
                                # Read file content now while object is available
                                result = upload_document(business_id, uploaded_file)
                                
                                if result and (not isinstance(result, dict) or "error" not in result):
                                    st.success(f"✅ {upload_info['name']} processed successfully!")
                                    # Add confirmation message to chat
                                    confirmation_msg = {
                                        "role": "assistant",
                                        "content": f"I've processed '{upload_info['name']}'. You can now ask me questions about it!",
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
                                    
                                    # Mark file as processed
                                    st.session_state[file_key] = True
                                    
                                    # Clean up and close upload area
                                    if upload_state_key in st.session_state:
                                        del st.session_state[upload_state_key]
                                    st.session_state.upload_counter = st.session_state.get("upload_counter", 0) + 1
                                    st.session_state.show_file_upload = False
                                    
                                    # Small delay before rerun to ensure message is visible
                                    import time
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    error_msg = f"❌ Failed to process {upload_info['name']}"
                                    if isinstance(result, dict) and "error" in result:
                                        error_detail = result["error"]
                                        error_msg += f"\n\nError: {error_detail}"
                                    st.error(error_msg)
                                    
                                    # Reset upload state to allow retry
                                    if upload_state_key in st.session_state:
                                        del st.session_state[upload_state_key]
                                    if file_key in st.session_state:
                                        del st.session_state[file_key]
                            except Exception as e:
                                logger.error(f"Upload exception: {e}", exc_info=True)
                                st.error(f"❌ Upload failed: {str(e)}")
                                # Reset upload state
                                if upload_state_key in st.session_state:
                                    del st.session_state[upload_state_key]
                    else:
                        st.info(f"ℹ️ {upload_info['name']} was already processed.")
                        # Clean up
                        if upload_state_key in st.session_state:
                            del st.session_state[upload_state_key]
                        st.session_state.upload_counter = st.session_state.get("upload_counter", 0) + 1
                        st.session_state.show_file_upload = False
                        st.rerun()
                                    # Add confirmation message to chat
                                    confirmation_msg = {
                                        "role": "assistant",
                                        "content": f"I've processed '{upload_info['name']}'. You can now ask me questions about it!",
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
                                    
                                    # Mark file as processed
                                    st.session_state[file_key] = True
                                    
                                    # Clean up and close upload area
                                    if upload_state_key in st.session_state:
                                        del st.session_state[upload_state_key]
                                    st.session_state.upload_counter = st.session_state.get("upload_counter", 0) + 1
                                    st.session_state.show_file_upload = False
                                    
                                    # Small delay before rerun to ensure message is visible
                                    import time
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    error_msg = f"❌ Failed to process {upload_info['name']}"
                                    if isinstance(result, dict) and "error" in result:
                                        error_detail = result["error"]
                                        error_msg += f"\n\nError: {error_detail}"
                                    st.error(error_msg)
                                    
                                    # Reset upload state to allow retry
                                    if upload_state_key in st.session_state:
                                        del st.session_state[upload_state_key]
                                    if file_key in st.session_state:
                                        del st.session_state[file_key]
                            except Exception as e:
                                logger.error(f"Upload exception: {e}", exc_info=True)
                                st.error(f"❌ Upload failed: {str(e)}")
                                # Reset upload state
                                if upload_state_key in st.session_state:
                                    del st.session_state[upload_state_key]
                    else:
                        st.error("File object lost. Please try uploading again.")
                        if upload_state_key in st.session_state:
                            del st.session_state[upload_state_key]
                else:
                    st.info(f"ℹ️ {upload_info['name']} was already processed.")
                    # Clean up
                    if upload_state_key in st.session_state:
                        del st.session_state[upload_state_key]
                    st.session_state.upload_counter = st.session_state.get("upload_counter", 0) + 1
                    st.session_state.show_file_upload = False
                    st.rerun()
            
            # Close button - compact
            if st.button("✕ Close", key="close_file_upload_btn", help="Close file upload"):
                st.session_state.show_file_upload = False
                # Clear any pending uploads
                upload_state_key = f"pending_upload_{upload_key}"
                if upload_state_key in st.session_state:
                    del st.session_state[upload_state_key]
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
        # CRITICAL FIX: Force-create conversation BEFORE allowing query
        if not st.session_state.current_conversation_id:
            conv_title = user_query[:50] + "..." if len(user_query) > 50 else user_query
            conv = create_conversation(st.session_state.selected_gpt, title=conv_title)
            if not conv:
                st.error("Failed to create conversation. Please try again.")
                st.rerun()
            else:
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
        
        # CRITICAL FIX: Add user message IMMEDIATELY (no rerun in middle)
        user_msg = {
            "role": "user",
            "content": user_query
        }
        st.session_state.chat_history.append(user_msg)
        
        # Save user message to backend
        try:
            api_request("POST", f"/api/v1/conversations/{st.session_state.current_conversation_id}/messages",
                      json={"role": "user", "content": user_query, "sources": []})
        except Exception as e:
            logger.warning(f"Could not save user message to backend: {e}")
        
        # Get response IMMEDIATELY - CRITICAL: Use conversation_id as business_id
        with st.spinner("Thinking..."):
            try:
                # CRITICAL FIX: Use conversation_id as business_id for document isolation
                business_id_for_query = st.session_state.current_conversation_id
                
                logger.info(f"🔍 Making chat query with business_id={business_id_for_query}, query={user_query[:50]}")
                response = chat_query(
                    business_id_for_query,
                    user_query,
                    st.session_state.chat_history[:-1],  # Exclude the just-added user message
                    st.session_state.current_conversation_id,
                    reply_as_me=st.session_state.reply_as_me
                )
                
                logger.info(f"📥 Received response: {response is not None}, has answer: {response and response.get('answer') is not None if response else False}")
                
                if response and response.get("answer"):
                    # CRITICAL: Strip any HTML source boxes from answer text - AGGRESSIVE CLEANING
                    answer_text = response.get("answer", "I apologize, but I couldn't generate a response.")
                    import re
                    # Remove source-box divs with flexible whitespace matching
                    answer_text = re.sub(r'<div\s+class\s*=\s*["\']source-box["\']>.*?</div>', '', answer_text, flags=re.DOTALL | re.IGNORECASE)
                    # Also match without quotes
                    answer_text = re.sub(r'<div\s+class\s*=\s*source-box>.*?</div>', '', answer_text, flags=re.DOTALL | re.IGNORECASE)
                    # Remove any remaining source-box content (in case div tags are malformed)
                    answer_text = re.sub(r'<strong>Source\s+\d+.*?</strong>', '', answer_text, flags=re.DOTALL | re.IGNORECASE)
                    answer_text = re.sub(r'<em>Relevance:.*?</em>', '', answer_text, flags=re.DOTALL | re.IGNORECASE)
                    # Remove Sources emoji and text
                    answer_text = re.sub(r'📚\s*Sources?\s*', '', answer_text, flags=re.IGNORECASE)
                    answer_text = re.sub(r'<details.*?Sources?.*?</details>', '', answer_text, flags=re.DOTALL | re.IGNORECASE)
                    # Remove ALL HTML tags (aggressive - strip everything)
                    answer_text = re.sub(r'<[^>]+>', '', answer_text)
                    # Clean up extra whitespace and newlines
                    answer_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', answer_text)
                    answer_text = re.sub(r'\s{3,}', ' ', answer_text)  # Multiple spaces to single
                    answer_text = answer_text.strip()
                    
                    assistant_msg = {
                        "role": "assistant",
                        "content": answer_text,
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
                        logger.error(f"❌ Chat query returned error: {error_msg}")
                    else:
                        logger.error(f"❌ Chat query returned no answer. Response: {response}")
                    
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
        
        # CRITICAL: Force rerun to display both user message and response
        st.rerun()
    
    # JavaScript to fix prompt field position and avatar visibility
    st.markdown("""
    <script>
    (function() {
        function fixPromptFieldPosition() {
            // CRITICAL: Force prompt field to bottom
            const chatInput = document.querySelector('div[data-testid="stChatInputContainer"]');
            if (chatInput) {
                chatInput.style.position = 'fixed';
                chatInput.style.bottom = '0';
                chatInput.style.top = 'auto';
                chatInput.style.left = '50%';
                chatInput.style.transform = 'translateX(-50%)';
                chatInput.style.width = 'min(980px, calc(100vw - 24px))';
                chatInput.style.zIndex = '9999';
                chatInput.style.margin = '0';
                
                // Remove any duplicate styling from inner elements
                const innerElements = chatInput.querySelectorAll('div[data-testid="stChatInput"], form[data-testid="stChatInputForm"]');
                innerElements.forEach(el => {
                    el.style.position = 'static';
                    el.style.left = 'auto';
                    el.style.right = 'auto';
                    el.style.background = 'transparent';
                    el.style.border = '0';
                    el.style.boxShadow = 'none';
                });
            }
        }
        
        function fixAvatarVisibility() {
            let avatar = document.querySelector('button[key="sidebar_avatar"]');
            if (!avatar) {
                const sidebar = document.querySelector('section[data-testid="stSidebar"]');
                if (sidebar) {
                    const buttons = sidebar.querySelectorAll('button');
                    buttons.forEach(btn => {
                        const text = (btn.textContent || btn.innerText || '').trim();
                        if (text === '👤' || text === '?' || btn.getAttribute('aria-label')?.includes('avatar') || btn.getAttribute('aria-label')?.includes('Account')) {
                            avatar = btn;
                        }
                    });
                }
            }
            
            if (avatar) {
                let avatarText = (avatar.textContent || avatar.innerText || '').trim();
                if (avatarText === '?' || avatarText === '' || !avatarText) {
                    avatarText = '👤';
                    avatar.textContent = '👤';
                    avatar.innerHTML = '👤';
                }
                
                avatar.style.borderRadius = '50%';
                avatar.style.width = '60px';
                avatar.style.height = '60px';
                avatar.style.minWidth = '60px';
                avatar.style.minHeight = '60px';
                avatar.style.border = '4px solid #3b82f6';
                avatar.style.backgroundColor = '#3b82f6';
                avatar.style.color = '#ffffff';
                avatar.style.fontSize = '24px';
                avatar.style.fontWeight = '900';
                avatar.style.visibility = 'visible';
                avatar.style.opacity = '1';
                avatar.style.display = 'flex';
                avatar.style.alignItems = 'center';
                avatar.style.justifyContent = 'center';
            }
        }
        
        function applyFixes() {
            fixPromptFieldPosition();
            fixAvatarVisibility();
        }
        
        applyFixes();
        setTimeout(applyFixes, 100);
        setTimeout(applyFixes, 500);
        setTimeout(applyFixes, 1000);
        
        // Watch for DOM changes
        const observer = new MutationObserver(applyFixes);
        observer.observe(document.body, { childList: true, subtree: true });
    })();
    </script>
    """, unsafe_allow_html=True)
