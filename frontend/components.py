"""
Reusable UI components for the Streamlit app.
"""
import streamlit as st
from typing import Optional, Callable


def chat_menu_button(conversation_id: str, title: str, is_current: bool = False):
    """
    Create a chat item with three-dot menu.
    Returns the action selected (None, 'load', 'rename', 'archive', 'delete', 'share')
    """
    col1, col2 = st.columns([5, 1])
    
    with col1:
        button_label = f"▶️ {title}" if is_current else f"💬 {title}"
        if st.button(button_label, key=f"chat_btn_{conversation_id}", use_container_width=True):
            return 'load'
    
    with col2:
        menu_key = f"menu_{conversation_id}"
        if menu_key not in st.session_state:
            st.session_state[menu_key] = False
        
        if st.button("⋯", key=f"menu_btn_{conversation_id}", help="More options"):
            st.session_state[menu_key] = not st.session_state[menu_key]
    
    # Show menu if opened
    if st.session_state.get(menu_key, False):
        with st.container():
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📝 Rename", key=f"rename_{conversation_id}"):
                    st.session_state[menu_key] = False
                    return 'rename'
            
            with col2:
                if st.button("📦 Archive", key=f"archive_{conversation_id}"):
                    st.session_state[menu_key] = False
                    return 'archive'
            
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{conversation_id}"):
                    st.session_state[menu_key] = False
                    return 'delete'
            
            with col4:
                if st.button("📤 Share", key=f"share_{conversation_id}"):
                    st.session_state[menu_key] = False
                    return 'share'
            
            st.markdown("---")
    
    return None

