"""
Streamlit frontend for AI Assistant Coworker.
"""
import streamlit as st
import requests
import os
from typing import List, Dict, Any
from datetime import datetime

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

# Custom CSS
st.markdown("""
<style>
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
    .source-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 3px solid #1f77b4;
    }
    .stat-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


# Helper functions
def api_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """Make API request with authentication."""
    headers = kwargs.pop("headers", {})
    headers["X-API-Key"] = API_KEY
    
    url = f"{BACKEND_URL}{endpoint}"
    response = requests.request(method, url, headers=headers, **kwargs)
    
    if response.status_code >= 400:
        st.error(f"API Error: {response.text}")
    
    return response


def get_businesses() -> List[Dict[str, Any]]:
    """Get list of businesses."""
    try:
        response = api_request("GET", "/api/v1/businesses")
        if response.status_code == 200:
            return response.json()
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
        return response.status_code == 200
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
        payload = {
            "business_id": business_id,
            "query": query,
            "conversation_history": history or [],
            "max_sources": 5
        }
        
        response = api_request(
            "POST",
            "/api/v1/chat",
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error in chat query: {str(e)}")
        return None


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


# Sidebar
with st.sidebar:
    st.markdown("## 🤖 AI Assistant Coworker")
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["Chat", "Documents", "Business Settings"],
        key="nav_radio"
    )
    st.session_state.current_page = page
    
    st.markdown("---")
    
    # Business selection
    st.markdown("### Select Business")
    businesses = get_businesses()
    
    if businesses:
        business_options = {b["name"]: b["id"] for b in businesses}
        selected_name = st.selectbox(
            "Active Business",
            options=list(business_options.keys()),
            key="business_select"
        )
        st.session_state.selected_business = business_options[selected_name]
        
        # Show business stats
        selected_biz = next(b for b in businesses if b["id"] == st.session_state.selected_business)
        st.markdown("#### Stats")
        st.metric("Documents", selected_biz.get("document_count", 0))
    else:
        st.warning("No businesses found. Create one in Business Settings.")
        st.session_state.selected_business = None
    
    st.markdown("---")
    
    # Create new business (quick action)
    with st.expander("➕ Quick: Create Business"):
        new_biz_name = st.text_input("Business Name", key="quick_new_biz")
        if st.button("Create", key="quick_create_btn"):
            if new_biz_name:
                if create_business(new_biz_name):
                    st.success(f"Created: {new_biz_name}")
                    st.rerun()
            else:
                st.error("Please enter a name")


# Main content
if st.session_state.current_page == "Chat":
    st.markdown('<div class="main-header">💬 Chat with Your Documents</div>', unsafe_allow_html=True)
    
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
        
        # Chat input
        user_query = st.chat_input("Ask a question about your documents...")
        
        if user_query:
            # Add user message
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_query
            })
            
            # Get response
            with st.spinner("Thinking..."):
                response = chat_query(
                    st.session_state.selected_business,
                    user_query,
                    st.session_state.chat_history
                )
                
                if response:
                    # Add assistant message
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response.get("sources", [])
                    })
                    
                    st.rerun()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
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
    st.markdown('<div class="sub-header">Manage businesses and configurations</div>', unsafe_allow_html=True)
    
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
    
    if businesses:
        for biz in businesses:
            with st.expander(f"🏢 {biz['name']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {biz['id']}")
                    st.write(f"**Description:** {biz.get('description', 'N/A')}")
                
                with col2:
                    st.write(f"**Documents:** {biz.get('document_count', 0)}")
                    st.write(f"**Created:** {biz.get('created_at', 'N/A')[:10]}")
    else:
        st.info("No businesses found. Create one above to get started!")
    
    st.markdown("---")
    
    # System info
    st.markdown("### System Information")
    try:
        response = api_request("GET", "/health")
        if response.status_code == 200:
            health = response.json()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="stat-box">
                    <h3>✅ Status</h3>
                    <p>{health.get('status', 'unknown')}</p>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="stat-box">
                    <h3>🔢 Version</h3>
                    <p>{health.get('version', 'unknown')}</p>
                </div>
                """, unsafe_allow_html=True)
    except:
        st.error("Backend not accessible")


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <small>AI Assistant Coworker | Built with FastAPI + Streamlit + LangChain</small>
</div>
""", unsafe_allow_html=True)


