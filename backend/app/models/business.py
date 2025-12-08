"""
Business/Tenant data models.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class BusinessBase(BaseModel):
    """Base business model."""
    name: str = Field(..., description="Business name")
    description: Optional[str] = Field(None, description="Business description")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Business-specific settings")


class BusinessCreate(BusinessBase):
    """Model for creating a new business."""
    pass


class Business(BusinessBase):
    """Complete business model with ID and timestamps."""
    id: str = Field(..., description="Unique business identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    document_count: int = Field(0, description="Number of documents uploaded")
    
    class Config:
        from_attributes = True


class BusinessUpdate(BaseModel):
    """Model for updating a business."""
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

