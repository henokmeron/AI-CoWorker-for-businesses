"""
Streamlit frontend for AI Assistant Coworker - ChatGPT-style interface with enhanced features.
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

# Initialize session state for auth
if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Custom CSS - ChatGPT-style with Auth UI
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Fixed bottom-left avatar button */
    .auth-avatar-container {
        position: fixed;
        left: 16px;
        bottom: 16px;
        z-index: 9999;
    }
    .auth-avatar-button {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #343541;
        border: 2px solid #565869;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: white;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.2s;
    }
    .auth-avatar-button:hover {
        background: #40414f;
        border-color: #8e8ea0;
    }
    .auth-avatar-button.logged-in {
        background: #10a37f;
        border-color: #10a37f;
    }
    
    /* Dropdown menu */
    .auth-dropdown {
        position: absolute;
        bottom: 50px;
        left: 0;
        background: #202123;
        border: 1px solid #565869;
        border-radius: 8px;
        min-width: 200px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        display: none;
    }
    .auth-dropdown.show {
        display: block;
    }
    .auth-dropdown-item {
        padding: 12px 16px;
        color: #ececf1;
        cursor: pointer;
        border-bottom: 1px solid #343541;
        font-size: 14px;
    }
    .auth-dropdown-item:hover {
        background: #343541;
    }
    .auth-dropdown-item:last-child {
        border-bottom: none;
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
    
    /* GPT header with kebab menu */
    .gpt-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem;
        margin-bottom: 0.25rem;
    }
    .gpt-kebab {
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 18px;
        color: #8e8ea0;
    }
    .gpt-kebab:hover {
        background: #343541;
        color: #ececf1;
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
    
    /* Settings tabs */
    .settings-tabs {
        display: flex;
        border-bottom: 1px solid #343541;
        margin-bottom: 1rem;
    }
    .settings-tab {
        padding: 12px 24px;
        cursor: pointer;
        color: #8e8ea0;
        border-bottom: 2px solid transparent;
    }
    .settings-tab.active {
        color: #10a37f;
        border-bottom-color: #10a37f;
    }
    .settings-tab:hover {
        color: #ececf1;
    }
    
    /* Edit GPT panel */
    .edit-gpt-panel {
        position: fixed;
        right: 0;
        top: 0;
        width: 400px;
        height: 100vh;
        background: #202123;
        border-left: 1px solid #343541;
        z-index: 1000;
        overflow-y: auto;
        padding: 20px;
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
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "settings_tab" not in st.session_state:
    st.session_state.settings_tab = "General"
if "show_edit_gpt" not in st.session_state:
    st.session_state.show_edit_gpt = False
if "editing_gpt_id" not in st.session_state:
    st.session_state.editing_gpt_id = None
if "reply_as_me" not in st.session_state:
    st.session_state.reply_as_me = False
if "show_auth_dropdown" not in st.session_state:
    st.session_state.show_auth_dropdown = False


def get_user_initials():
    """Get user initials for avatar."""
    if st.session_state.user_logged_in and st.session_state.user_name:
        name = st.session_state.user_name
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif len(parts) == 1:
            return parts[0][:2].upper()
    return "?"


def render_auth_avatar():
    """Render fixed bottom-left avatar button."""
    initials = get_user_initials()
    logged_in_class = "logged-in" if st.session_state.user_logged_in else ""
    
    st.markdown(f"""
    <div class="auth-avatar-container">
        <div class="auth-avatar-button {logged_in_class}" id="auth-avatar-btn">
            {initials}
        </div>
    </div>
    <script>
        document.getElementById('auth-avatar-btn').addEventListener('click', function() {{
            // Toggle dropdown via Streamlit
            window.parent.postMessage({{type: 'streamlit:setComponentValue', value: 'toggle_auth'}}, '*');
        }});
    </script>
    """, unsafe_allow_html=True)
    
    # Handle avatar click
    if st.button("", key="auth_avatar_click", help="", use_container_width=False):
        st.session_state.show_auth_dropdown = not st.session_state.show_auth_dropdown
        st.rerun()


def render_auth_dropdown():
    """Render auth dropdown menu."""
    if not st.session_state.show_auth_dropdown:
        return
    
    with st.container():
        st.markdown('<div class="auth-dropdown show">', unsafe_allow_html=True)
        
        if st.session_state.user_logged_in:
            st.markdown(f"**{st.session_state.user_name or 'User'}**")
            st.markdown("---")
            if st.button("⚙️ Settings", key="auth_settings", use_container_width=True):
                st.session_state.show_settings = True
                st.session_state.show_auth_dropdown = False
                st.rerun()
            if st.button("⬆️ Upgrade", key="auth_upgrade", use_container_width=True):
                st.info("Upgrade feature coming soon!")
                st.session_state.show_auth_dropdown = False
                st.rerun()
            if st.button("❓ Help", key="auth_help", use_container_width=True):
                st.info("Help center coming soon!")
                st.session_state.show_auth_dropdown = False
                st.rerun()
            if st.button("🚪 Log out", key="auth_logout", use_container_width=True):
                st.session_state.user_logged_in = False
                st.session_state.user_name = None
                st.session_state.user_email = None
                st.session_state.show_auth_dropdown = False
                st.success("Logged out!")
                st.rerun()
        else:
            if st.button("🔐 Login", key="auth_login", use_container_width=True):
                # Simple login (can be extended with real auth)
                st.session_state.user_logged_in = True
                st.session_state.user_name = "Demo User"
                st.session_state.user_email = "demo@example.com"
                st.session_state.show_auth_dropdown = False
                st.success("Logged in!")
                st.rerun()
            if st.button("📝 Sign up", key="auth_signup", use_container_width=True):
                st.info("Sign up feature coming soon!")
                st.session_state.show_auth_dropdown = False
                st.rerun()
            if st.button("⚙️ Settings", key="auth_settings_guest", use_container_width=True):
                st.session_state.show_settings = True
                st.session_state.show_auth_dropdown = False
                st.rerun()
            if st.button("❓ Help", key="auth_help_guest", use_container_width=True):
                st.info("Help center coming soon!")
                st.session_state.show_auth_dropdown = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


def render_settings():
    """Render tabbed settings panel."""
    if not st.session_state.show_settings:
        return
    
    st.markdown("## ⚙️ Settings")
    
    # Settings tabs
    tabs = ["General", "Notifications", "Personalization", "App Connectors", "Data Control", "Security", "Account"]
    selected_tab = st.radio("", tabs, horizontal=True, key="settings_tabs_radio", label_visibility="collapsed")
    st.session_state.settings_tab = selected_tab
    
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
    if st.button("Close Settings", key="close_settings"):
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
                    st.error(f"❌ Failed to upload {uploaded_file.name}")
        
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
    
    # Load and display GPTs
    try:
        gpts = get_businesses()
        st.session_state.gpts = gpts
        
        if gpts:
            for gpt in gpts:
                gpt_name = gpt.get('name', 'Untitled')
                display_name = gpt_name[:30] + "..." if len(gpt_name) > 30 else gpt_name
                is_selected = st.session_state.selected_gpt == gpt.get('id')
                
                # GPT header with kebab menu
                col1, col2 = st.columns([8, 1])
                
                with col1:
                    button_style = "primary" if is_selected else "secondary"
                    if st.button(display_name, key=f"gpt_{gpt.get('id')}", use_container_width=True, type=button_style):
                        st.session_state.selected_gpt = gpt.get('id')
                        st.session_state.chat_history = []
                        st.session_state.current_conversation_id = None
                        st.rerun()
                
                with col2:
                    if st.button("⋮", key=f"gpt_menu_{gpt.get('id')}", help="GPT options"):
                        st.session_state[f"gpt_menu_{gpt.get('id')}"] = True
                        st.rerun()
                
                # GPT menu
                if st.session_state.get(f"gpt_menu_{gpt.get('id')}", False):
                    if st.button("💬 New chat", key=f"gpt_new_chat_{gpt.get('id')}"):
                        st.session_state.selected_gpt = gpt.get('id')
                        st.session_state.chat_history = []
                        st.session_state.current_conversation_id = None
                        st.session_state[f"gpt_menu_{gpt.get('id')}"] = False
                        st.rerun()
                    
                    if st.button("ℹ️ About", key=f"gpt_about_{gpt.get('id')}"):
                        st.info(f"**{gpt.get('name')}**\n\n{gpt.get('description', 'No description')}")
                        st.session_state[f"gpt_menu_{gpt.get('id')}"] = False
                        st.rerun()
                    
                    if st.button("✏️ Edit GPT", key=f"gpt_edit_{gpt.get('id')}"):
                        st.session_state.editing_gpt_id = gpt.get('id')
                        st.session_state.show_edit_gpt = True
                        st.session_state[f"gpt_menu_{gpt.get('id')}"] = False
                        st.rerun()
                    
                    if st.button("👁️ Hide", key=f"gpt_hide_{gpt.get('id')}"):
                        st.info("Hide feature coming soon!")
                        st.session_state[f"gpt_menu_{gpt.get('id')}"] = False
                        st.rerun()
                    
                    if st.button("✕ Close", key=f"gpt_close_{gpt.get('id')}"):
                        st.session_state[f"gpt_menu_{gpt.get('id')}"] = False
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
    
    # Reply as me toggle
    st.checkbox("Reply as me", value=st.session_state.reply_as_me, key="reply_as_me_toggle", 
                help="Toggle between personalized replies and categorization mode")
    st.session_state.reply_as_me = st.session_state.get("reply_as_me_toggle", False)
    
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
    
    # File upload with drag zone support
    if st.session_state.selected_gpt:
        uploaded_file = st.file_uploader(
            "➕ Attach file (PDF, DOCX, TXT, XLSX)",
            type=["pdf", "docx", "txt", "xlsx", "doc", "xls", "pptx", "csv"],
            key="gpt_file_uploader",
            help="Upload a document to this GPT. Supported: PDF, DOCX, TXT, XLSX"
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
                    st.error(f"❌ Failed to process {uploaded_file.name}. Please check file format and try again.")
    else:
        uploaded_file = st.file_uploader(
            "➕ Attach file (PDF, DOCX, TXT, XLSX)",
            type=["pdf", "docx", "txt", "xlsx", "doc", "xls", "pptx", "csv"],
            key="chat_file_uploader",
            help="Attach a temporary file to this chat"
        )
        
        if uploaded_file:
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
                    st.error(f"❌ Failed to process {uploaded_file.name}. Please check file format and try again.")
    
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


# Render auth UI (fixed bottom-left)
render_auth_avatar()
if st.session_state.show_auth_dropdown:
    render_auth_dropdown()

