"""
Document data models.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Document metadata."""
    filename: str
    file_type: str
    file_size: int
    page_count: Optional[int] = None
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    business_id: str
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Document model."""
    id: str = Field(..., description="Unique document identifier")
    business_id: str = Field(..., description="Business this document belongs to")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type/extension")
    file_size: int = Field(..., description="File size in bytes")
    file_path: str = Field(..., description="Storage path")
    status: str = Field(default="processing", description="Processing status")
    chunk_count: int = Field(0, description="Number of text chunks")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""
    document_id: str
    filename: str
    status: str
    message: str

