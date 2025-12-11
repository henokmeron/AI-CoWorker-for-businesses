"""
Conversation and chat history models.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: List[Dict[str, Any]] = Field(default_factory=list)


class Conversation(BaseModel):
    """Conversation/chat session."""
    id: str = Field(..., description="Conversation ID")
    business_id: str = Field(..., description="Business ID")
    title: str = Field(..., description="Conversation title")
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived: bool = Field(default=False)
    tags: List[str] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    """Request to create a conversation."""
    business_id: str
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    """Request to update a conversation."""
    title: Optional[str] = None
    archived: Optional[bool] = None
    tags: Optional[List[str]] = None

