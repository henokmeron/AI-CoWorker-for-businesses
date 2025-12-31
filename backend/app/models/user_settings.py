"""
User settings data models.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class UserSettingsBase(BaseModel):
    """Base user settings model."""
    # General settings
    language: str = Field("English", description="Preferred language")
    theme: str = Field("Dark", description="UI theme (Dark, Light, Auto)")
    font_size: int = Field(14, description="Font size (12-20)")
    auto_save_conversations: bool = Field(True, description="Auto-save conversations")
    default_model: str = Field("gpt-4-turbo-preview", description="Default AI model")
    
    # Personalization
    custom_instructions: str = Field("", description="Custom instructions for AI")
    response_style: str = Field("Professional", description="Response style (Professional, Casual, Technical)")
    
    # Notifications
    email_notifications: bool = Field(False, description="Enable email notifications")
    browser_notifications: bool = Field(False, description="Enable browser notifications")
    desktop_notifications: bool = Field(False, description="Enable desktop notifications")
    
    # Security
    session_timeout_minutes: int = Field(1440, description="Session timeout in minutes")
    two_factor_auth: bool = Field(False, description="Enable two-factor authentication")
    
    # Data control
    data_retention_days: int = Field(365, description="Data retention period in days")
    auto_delete_old_conversations: bool = Field(False, description="Auto-delete old conversations")
    
    # Integrations
    integrations: Dict[str, Any] = Field(default_factory=dict, description="Connected integrations")
    
    # GPT-specific settings (per GPT)
    gpt_settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Settings per GPT/business")


class UserSettings(UserSettingsBase):
    """Complete user settings model with ID and timestamps."""
    user_id: str = Field(..., description="User identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSettingsUpdate(BaseModel):
    """Model for updating user settings."""
    language: Optional[str] = None
    theme: Optional[str] = None
    font_size: Optional[int] = None
    auto_save_conversations: Optional[bool] = None
    default_model: Optional[str] = None
    custom_instructions: Optional[str] = None
    response_style: Optional[str] = None
    email_notifications: Optional[bool] = None
    browser_notifications: Optional[bool] = None
    desktop_notifications: Optional[bool] = None
    session_timeout_minutes: Optional[int] = None
    two_factor_auth: Optional[bool] = None
    data_retention_days: Optional[int] = None
    auto_delete_old_conversations: Optional[bool] = None
    integrations: Optional[Dict[str, Any]] = None
    gpt_settings: Optional[Dict[str, Dict[str, Any]]] = None

