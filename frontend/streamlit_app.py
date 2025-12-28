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
    
    /* File attachment button next to prompt */
    .file-attach-btn {
        position: absolute;
        left: 8px;
        bottom: 8px;
        z-index: 10;
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 8px;
        border-radius: 4px;
    }
    .file-attach-btn:hover {
        background: rgba(255,255,255,0.1);
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
    
    /* Avatar button in sidebar */
    .sidebar-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #343541;
        border: 2px solid #565869;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: white;
        font-weight: 600;
        font-size: 12px;
        margin: 8px auto;
    }
    .sidebar-avatar:hover {
        background: #40414f;
    }
    .sidebar-avatar.logged-in {
        background: #10a37f;
        border-color: #10a37f;
    }
</style>
""", unsafe_allow_html=True)


# Helper functions
def api_request(method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
    """Make API request with authentication."""
    headers = kwargs.pop("headers", {})
    headers["X-API-Key"] = API_KEY
    
    # Only set Content-Type for JSON requests, NOT for file uploads
    # When files are present, requests library will set multipart/form-data automatically
    if "json" in kwargs and "files" not in kwargs:
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
        # Handle different file object types (Streamlit UploadedFile, file-like objects)
        if hasattr(file, 'getvalue'):
            # Streamlit UploadedFile
            file_content = file.getvalue()
            file_name = file.name
            file_type = getattr(file, 'type', None)
        elif hasattr(file, 'read'):
            # File-like object
            file_content = file.read()
            # Reset file pointer if possible
            if hasattr(file, 'seek'):
                file.seek(0)
            file_name = getattr(file, 'name', 'uploaded_file')
            file_type = getattr(file, 'content_type', None)
        else:
            # Assume it's already bytes
            file_content = file
            file_name = "uploaded_file"
            file_type = None
        
        # Ensure we have bytes
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')
        
        file_tuple = (file_name, file_content, file_type)
        
        # Form data - business_id must be sent as form field (not query param)
        data = {"business_id": business_id}
        files = {"file": file_tuple}
        
        # Don't include business_id in query string - it's in form data
        response = api_request("POST", "/api/v1/documents/upload", files=files, data=data)
        if response and response.status_code == 200:
            return response.json()
        elif response:
            # Log the error for debugging
            error_text = response.text
            logger.error(f"Upload failed: {response.status_code} - {error_text}")
            # Try to extract error message from response and return it
            try:
                error_json = response.json()
                if 'detail' in error_json:
                    error_detail = error_json['detail']
                    logger.error(f"Error detail: {error_detail}")
                    # Return error dict so frontend can display it
                    return {"error": error_detail, "status_code": response.status_code}
            except:
                # If not JSON, return the text
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
    """Delete a conversation (NOT the GPT)."""
    response = api_request("DELETE", f"/api/v1/conversations/{conversation_id}")
    return response and response.status_code == 200


def get_user_initials():
    """Get user initials for avatar."""
    if st.session_state.user_logged_in and st.session_state.user_name:
        name = st.session_state.user_name
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif len(parts) == 1:
            return parts[0][:2].upper()
    # Show user icon when not logged in
    return "👤"


def handle_login():
    """Handle login - redirect to OAuth or show login form."""
    with st.form("login_form"):
        st.markdown("### Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Login", use_container_width=True):
                if email and password:
                    # Call real auth endpoint
                    data = {"email": email, "password": password}
                    response = api_request("POST", "/api/v1/auth/login", json=data)
                    if response and response.status_code == 200:
                        result = response.json()
                        if result.get("success"):
                            st.session_state.user_logged_in = True
                            st.session_state.user_name = result.get("user_name", email.split("@")[0].title())
                            st.session_state.user_email = result.get("user_email", email)
                            st.session_state.show_auth_dropdown = False
                            st.success("Logged in!")
                            st.rerun()
                        else:
                            st.error(result.get("message", "Login failed"))
                    else:
                        # Login failed - show specific error
                        error_msg = "Login failed. Please check your credentials."
                        if response:
                            try:
                                error_data = response.json()
                                if "detail" in error_data:
                                    error_msg = error_data["detail"]
                                elif "message" in error_data:
                                    error_msg = error_data["message"]
                            except:
                                # If response is not JSON, check status code
                                if response.status_code == 401:
                                    error_msg = "Invalid email or password."
                                elif response.status_code == 403:
                                    error_msg = "Access denied. Please check your credentials."
                                elif response.status_code >= 500:
                                    error_msg = "Server error. Please try again later."
                        st.error(error_msg)
                else:
                    st.error("Please enter email and password")
        with col2:
            if st.form_submit_button("Cancel", use_container_width=True):
                st.session_state.show_auth_dropdown = False
                st.rerun()
    
    st.markdown("---")
    st.markdown("**Or sign in with:**")
    if st.button("🔵 Google", key="google_login", use_container_width=True):
        # Redirect to Google OAuth (simplified - in production would use proper OAuth flow)
        google_oauth_url = "https://accounts.google.com/o/oauth2/v2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&response_type=code&scope=email profile"
        st.markdown(f'<a href="{google_oauth_url}" target="_blank">Click here to sign in with Google</a>', unsafe_allow_html=True)
        st.info("⚠️ Google OAuth requires backend configuration. For now, please use email/password above.")
    
    if st.button("🔷 Microsoft", key="microsoft_login", use_container_width=True):
        # Redirect to Microsoft OAuth (simplified)
        microsoft_oauth_url = "https://login.microsoftonline.com/oauth2/v2.0/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&response_type=code&scope=openid email profile"
        st.markdown(f'<a href="{microsoft_oauth_url}" target="_blank">Click here to sign in with Microsoft</a>', unsafe_allow_html=True)
        st.info("⚠️ Microsoft OAuth requires backend configuration. For now, please use email/password above.")


def render_settings():
    """Render tabbed settings panel."""
    if not st.session_state.show_settings:
        return
    
    # Header with back button
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("←", key="back_to_chat", help="Back to Chat"):
            st.session_state.show_settings = False
            st.rerun()
    with col2:
        st.markdown("## ⚙️ Settings")
    
    # Settings tabs
    tabs = ["General", "Notifications", "Personalization", "App Connectors", "Data Control", "Security", "Account"]
    selected_tab = st.radio("", tabs, horizontal=True, key="settings_tabs_radio", label_visibility="collapsed")
    
    st.markdown("---")
    
    # Tab content
    if selected_tab == "General":
        st.subheader("General Settings")
        st.text_input("Default Language", value="English", key="setting_lang")
        st.selectbox("Theme", ["Dark", "Light", "Auto"], key="setting_theme")
        st.slider("Font Size", 12, 20, 14, key="setting_font")
        
    elif selected_tab == "Notifications":
        st.subheader("Notification Settings")
        st.checkbox("Email notifications", value=True, key="notif_email")
        st.checkbox("Browser notifications", value=False, key="notif_browser")
        st.checkbox("Desktop notifications", value=False, key="notif_desktop")
        
    elif selected_tab == "Personalization":
        st.subheader("Personalization")
        st.text_area("Custom Instructions", key="setting_instructions", height=100)
        st.selectbox("Response Style", ["Professional", "Casual", "Technical"], key="setting_style")
        
    elif selected_tab == "App Connectors":
        st.subheader("App Connectors")
        st.info("Connect your apps to enhance AI capabilities")
        st.checkbox("Gmail", value=False, key="connector_gmail")
        st.checkbox("Outlook", value=False, key="connector_outlook")
        st.checkbox("Slack", value=False, key="connector_slack")
        
    elif selected_tab == "Data Control":
        st.subheader("Data Control")
        st.button("Export All Data", key="export_data")
        st.button("Delete All Data", key="delete_data", type="secondary")
        st.info("⚠️ This action cannot be undone")
        
    elif selected_tab == "Security":
        st.subheader("Security Settings")
        st.text_input("Change Password", type="password", key="setting_password")
        st.checkbox("Two-Factor Authentication", value=False, key="setting_2fa")
        st.checkbox("Session Timeout", value=True, key="setting_timeout")
        
    elif selected_tab == "Account":
        st.subheader("Account Settings")
        st.text_input("Name", value=st.session_state.user_name or "Guest", key="setting_name")
        st.text_input("Email", value=st.session_state.user_email or "", key="setting_email")
        st.button("Save Changes", key="save_account")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Chat", key="settings_to_chat", use_container_width=True):
            st.session_state.show_settings = False
            st.rerun()
    with col2:
        if st.button("Close Settings", key="close_settings", use_container_width=True):
            st.session_state.show_settings = False
            st.rerun()


def render_edit_gpt_panel():
    """Render Edit GPT side panel."""
    if not st.session_state.show_edit_gpt or not st.session_state.editing_gpt_id:
        return
    
    gpt = get_business(st.session_state.editing_gpt_id)
    if not gpt:
        st.error("GPT not found")
        st.session_state.show_edit_gpt = False
        return
    
    with st.container():
        st.markdown("### Edit GPT")
        
        # GPT Name
        new_name = st.text_input("Name", value=gpt.get("name", ""), key="edit_gpt_name")
        
        # GPT Description
        new_description = st.text_area("Description", value=gpt.get("description", ""), key="edit_gpt_desc", height=100)
        
        # Instructions
        gpt_settings = gpt.get("settings", {})
        instructions = gpt_settings.get("instructions", "")
        new_instructions = st.text_area("Instructions", value=instructions, key="edit_gpt_instructions", height=150, 
                                       help="How should this GPT behave? What is its role?")
        
        st.markdown("---")
        st.markdown("### Knowledge Base")
        
        # List existing documents
        documents = get_documents(st.session_state.editing_gpt_id)
        if documents:
            st.markdown("**Uploaded Documents:**")
            for doc in documents:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text(doc.get("filename", "Unknown"))
                with col2:
                    if st.button("🗑️", key=f"del_doc_{doc.get('id')}", help="Delete"):
                        if delete_document(st.session_state.editing_gpt_id, doc.get("id")):
                            st.success("Deleted!")
                            st.rerun()
        else:
            st.info("No documents uploaded yet")
        
        # File upload
        st.markdown("**Upload New Document:**")
        uploaded_file = st.file_uploader(
            "Choose file",
            type=["pdf", "docx", "txt", "xlsx", "doc", "xls", "pptx", "csv"],
            key="edit_gpt_upload",
            help="Supported: PDF, DOCX, TXT, XLSX"
        )
        
        if uploaded_file:
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                result = upload_document(st.session_state.editing_gpt_id, uploaded_file)
                if result:
                    st.success(f"✅ {uploaded_file.name} uploaded!")
                    st.rerun()
                else:
                    error_msg = f"❌ Failed to upload {uploaded_file.name}\n\nPossible reasons:\n- File format not supported\n- File is corrupted\n- Backend processing error\n\nPlease try again or check backend logs."
                    st.error(error_msg)
        
        st.markdown("---")
        
        # Save button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", key="save_gpt_edit", use_container_width=True):
                new_settings = gpt_settings.copy()
                new_settings["instructions"] = new_instructions
                
                updated = update_business(
                    st.session_state.editing_gpt_id,
                    name=new_name,
                    description=new_description,
                    settings=new_settings
                )
                if updated:
                    st.success("GPT updated!")
                    st.session_state.show_edit_gpt = False
                    st.rerun()
        
        with col2:
            if st.button("✕ Close", key="close_gpt_edit", use_container_width=True):
                st.session_state.show_edit_gpt = False
                st.rerun()


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
    
    # Load and display GPTs with dropdown menus
    try:
        gpts = get_businesses()
        st.session_state.gpts = gpts
        
        if gpts:
            for gpt in gpts:
                gpt_id = gpt.get('id')
                gpt_name = gpt.get('name', 'Untitled')
                display_name = gpt_name[:30] + "..." if len(gpt_name) > 30 else gpt_name
                is_selected = st.session_state.selected_gpt == gpt_id
                
                # GPT row with button and dropdown
                col1, col2 = st.columns([8, 1])
                
                with col1:
                    button_style = "primary" if is_selected else "secondary"
                    if st.button(display_name, key=f"gpt_{gpt_id}", use_container_width=True, type=button_style):
                        # Only clear chat if switching to a different GPT
                        if st.session_state.selected_gpt != gpt_id:
                            st.session_state.selected_gpt = gpt_id
                            # Preserve conversation if it belongs to this GPT, otherwise clear
                            if st.session_state.current_conversation_id:
                                # Check if current conversation belongs to this GPT
                                # If not, clear it
                                st.session_state.chat_history = []
                                st.session_state.current_conversation_id = None
                            else:
                                # No active conversation, just clear chat
                                st.session_state.chat_history = []
                        st.rerun()
                
                with col2:
                    # Dropdown trigger button (⋮)
                    if st.button("⋮", key=f"gpt_dd_{gpt_id}", help="GPT options"):
                        # Toggle dropdown for this GPT
                        if gpt_id in st.session_state.gpt_dropdown_open:
                            st.session_state.gpt_dropdown_open[gpt_id] = not st.session_state.gpt_dropdown_open[gpt_id]
                        else:
                            st.session_state.gpt_dropdown_open[gpt_id] = True
                        st.rerun()
                
                # Show dropdown menu if open
                if st.session_state.gpt_dropdown_open.get(gpt_id, False):
                    if st.button("💬 New chat", key=f"gpt_new_{gpt_id}", use_container_width=True):
                        # CRITICAL: Clear everything for this GPT
                        st.session_state.selected_gpt = gpt_id
                        st.session_state.chat_history = []
                        st.session_state.current_conversation_id = None
                        st.session_state.gpt_dropdown_open[gpt_id] = False
                        
                        # Create new conversation on backend
                        new_conv = create_conversation(gpt_id, title=f"New Chat {datetime.now().strftime('%I:%M %p')}")
                        if new_conv:
                            st.session_state.current_conversation_id = new_conv.get('id')
                        
                        st.rerun()
                    
                    if st.button("ℹ️ About", key=f"gpt_about_{gpt_id}", use_container_width=True):
                        st.info(f"**{gpt.get('name')}**\n\n{gpt.get('description', 'No description')}")
                        st.session_state.gpt_dropdown_open[gpt_id] = False
                        st.rerun()
                    
                    if st.button("✏️ Edit GPT", key=f"gpt_edit_{gpt_id}", use_container_width=True):
                        st.session_state.editing_gpt_id = gpt_id
                        st.session_state.show_edit_gpt = True
                        st.session_state.gpt_dropdown_open[gpt_id] = False
                        st.rerun()
                    
                    if st.button("👁️ Hide", key=f"gpt_hide_{gpt_id}", use_container_width=True):
                        st.info("Hide feature coming soon!")
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
        
        # Also clear any cached messages
        for key in list(st.session_state.keys()):
            if key.startswith("processed_") or key.startswith("show_menu_") or key.startswith("renaming_"):
                del st.session_state[key]
        
        # Create a new conversation on the backend (starts empty)
        business_id = st.session_state.selected_gpt or "temp_chat"
        new_conv_title = f"New Chat {datetime.now().strftime('%I:%M %p')}"
        
        try:
            new_conv = create_conversation(business_id, title=new_conv_title)
            if new_conv:
                st.session_state.current_conversation_id = new_conv.get('id')
                st.success("✅ New chat started!")
            else:
                st.warning("Could not create conversation on server, continuing locally")
        except Exception as e:
            logger.error(f"Error creating new conversation: {e}")
            st.warning("Continuing with local chat (not saved to server)")
        
        st.rerun()
    
    # Load and display conversations
    try:
        conversations = get_conversations(
            business_id=st.session_state.selected_gpt,
            archived=False
        )
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
                        # Only reload if this is a different conversation
                        if st.session_state.current_conversation_id != conv.get('id'):
                            # CRITICAL: Clear chat history FIRST to prevent bleeding
                            st.session_state.chat_history = []
                            
                            # Load conversation from backend
                            response = api_request("GET", f"/api/v1/conversations/{conv.get('id')}")
                            if response and response.status_code == 200:
                                loaded_conv = response.json()
                                # REPLACE (not append) chat history with loaded messages
                                st.session_state.chat_history = [
                                    {
                                        "role": msg.get("role"),
                                        "content": msg.get("content"),
                                        "sources": msg.get("sources", [])
                                    }
                                    for msg in loaded_conv.get("messages", [])
                                ]
                                st.session_state.current_conversation_id = conv.get('id')
                                logger.info(f"✅ Loaded conversation {conv.get('id')} with {len(st.session_state.chat_history)} messages")
                            else:
                                logger.error(f"❌ Failed to load conversation {conv.get('id')}")
                                st.session_state.current_conversation_id = conv.get('id')
                        else:
                            # Same conversation - just ensure it's set
                            st.session_state.current_conversation_id = conv.get('id')
                        st.rerun()
                
                with col2:
                    if st.button("⋯", key=f"menu_{conv.get('id')}", help="More options"):
                        st.session_state[f"show_menu_{conv.get('id')}"] = True
                        st.rerun()
                
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
    avatar_display = initials
    button_type = "primary" if st.session_state.user_logged_in else "secondary"
    
    # Style the button to look like a circular avatar - make it visible
    st.markdown(f"""
    <style>
        /* Avatar button styling - make it clearly visible */
        button[data-testid="baseButton-secondary"][key="sidebar_avatar"],
        button[data-testid="baseButton-primary"][key="sidebar_avatar"] {{
            border-radius: 50% !important;
            width: 40px !important;
            height: 40px !important;
            min-width: 40px !important;
            padding: 0 !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            border: 2px solid #565869 !important;
            background-color: {'#10a37f' if st.session_state.user_logged_in else '#565869'} !important;
            color: #ffffff !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}
        button[data-testid="baseButton-secondary"][key="sidebar_avatar"]:hover,
        button[data-testid="baseButton-primary"][key="sidebar_avatar"]:hover {{
            background-color: {'#0d8a6b' if st.session_state.user_logged_in else '#6e6e80'} !important;
            border-color: #8e8ea0 !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
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
            # Show login form
            handle_login()


# Main content area
if st.session_state.show_settings:
    render_settings()
elif st.session_state.show_edit_gpt:
    render_edit_gpt_panel()
    # Show chat in background (dimmed)
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
                file_key = f"processed_{uploaded_file.name}_{uploaded_file.size}"
                if file_key not in st.session_state:
                    st.session_state[file_key] = True
                    with st.spinner(f"Processing {uploaded_file.name}..."):
                        result = upload_document(business_id, uploaded_file)
                        if result:
                            st.success(f"✅ {uploaded_file.name} processed!")
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": f"I've processed '{uploaded_file.name}'. You can now ask me questions about it!",
                                "sources": []
                            })
                            st.session_state.upload_counter = st.session_state.get("upload_counter", 0) + 1
                            st.session_state.show_file_upload = False
                            st.rerun()
                        else:
                            # Get detailed error from response
                            error_msg = f"❌ Failed to process {uploaded_file.name}"
                            if isinstance(result, dict) and "error" in result:
                                error_detail = result["error"]
                                error_msg += f"\n\nError: {error_detail}\n\nPossible reasons:\n- File format not supported\n- File is corrupted\n- Backend processing error\n- Vector database not available\n\nPlease check backend logs for details."
                            else:
                                error_msg += "\n\nPossible reasons:\n- File format not supported\n- File is corrupted\n- Backend processing error\n- Vector database not available\n\nPlease try again or check backend logs."
                            st.error(error_msg)
                            if file_key in st.session_state:
                                del st.session_state[file_key]
            
            col1, col2 = st.columns([1, 10])
            with col1:
                if st.button("✕", key="close_file_upload_btn", help="Close"):
                    st.session_state.show_file_upload = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input with attachment button (ChatGPT style - button next to input)
    # Create a row with attachment button and chat input
    input_row = st.columns([0.04, 0.96])
    with input_row[0]:
        if st.button("➕", key="attach_file_btn", help="Attach file", use_container_width=True):
            st.session_state.show_file_upload = not st.session_state.show_file_upload
            st.rerun()
    with input_row[1]:
        user_query = st.chat_input("Message...")
    
    # Handle chat input
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
                # Use same business_id logic as file upload: selected_gpt or "temp_chat"
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

