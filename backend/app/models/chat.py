"""
Chat/Query data models.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source citation for an answer."""
    document_id: str
    document_name: str
    page: Optional[int] = None
    chunk_text: str
    relevance_score: float


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Request for chat/query."""
    business_id: Optional[str] = Field(None, description="Business ID for context")
    query: str = Field(..., description="User question")
    conversation_history: List[ChatMessage] = Field(default_factory=list, description="Previous messages")
    conversation_id: Optional[str] = Field(None, description="Conversation ID to save messages to")
    max_sources: int = Field(5, description="Maximum number of source citations")
    stream: bool = Field(False, description="Enable streaming response")
    reply_as_me: bool = Field(False, description="Reply as user vs categorize only")


class ChatResponse(BaseModel):
    """Response from chat/query."""
    answer: str = Field(..., description="AI-generated answer")
    sources: List[Source] = Field(default_factory=list, description="Source citations")
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


