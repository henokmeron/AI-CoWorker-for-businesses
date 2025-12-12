"""
Business/Tenant management API routes.
"""
import json
import logging
from typing import List
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from ...models.business import Business, BusinessCreate, BusinessUpdate
from ...core.config import settings
from ...core.security import verify_api_key
from ...utils.file_utils import ensure_directory
from ...api.dependencies import get_vector_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/businesses", tags=["businesses"])

# Simple JSON file storage for businesses (for prototype)
BUSINESS_DB_PATH = Path(settings.DATA_DIR) / "businesses.json"


def load_businesses() -> List[Business]:
    """Load businesses from JSON file."""
    if not BUSINESS_DB_PATH.exists():
        return []
    
    try:
        with open(BUSINESS_DB_PATH, 'r') as f:
            data = json.load(f)
            return [Business(**b) for b in data]
    except Exception as e:
        logger.error(f"Error loading businesses: {str(e)}")
        return []


def save_businesses(businesses: List[Business]):
    """Save businesses to JSON file."""
    ensure_directory(str(BUSINESS_DB_PATH.parent))
    
    with open(BUSINESS_DB_PATH, 'w') as f:
        data = [b.dict() for b in businesses]
        json.dump(data, f, indent=2, default=str)


@router.post("", response_model=Business)
async def create_business(
    business: BusinessCreate,
    api_key: str = Depends(verify_api_key)
):
    """Create a new business."""
    try:
        businesses = load_businesses()
        
        # Generate ID from name (sanitize)
        business_id = business.name.lower().replace(' ', '_').replace('-', '_')
        # Remove special characters
        business_id = ''.join(c for c in business_id if c.isalnum() or c == '_')
        if not business_id:
            business_id = "business_" + str(len(businesses) + 1)
        
        # Check if already exists
        if any(b.id == business_id for b in businesses):
            raise HTTPException(status_code=400, detail="Business with this name already exists")
        
        # Create business
        new_business = Business(
            id=business_id,
            **business.dict()
        )
        
        businesses.append(new_business)
        
        # Ensure data directory exists before saving
        try:
            ensure_directory(str(BUSINESS_DB_PATH.parent))
            save_businesses(businesses)
        except Exception as e:
            logger.error(f"Error saving businesses: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save business: {str(e)}")
        
        # Create business directory
        try:
            business_dir = Path(settings.UPLOAD_DIR) / business_id
            ensure_directory(str(business_dir))
        except Exception as e:
            logger.warning(f"Could not create business directory: {e}")
            # Continue anyway - directory will be created when needed
        
        logger.info(f"Created business: {business_id}")
        return new_business
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating business: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("", response_model=List[Business])
async def list_businesses(api_key: str = Depends(verify_api_key)):
    """List all businesses."""
    businesses = load_businesses()
    
    # Update document counts (ignore errors if vector DB not available)
    try:
        vector_db = get_vector_db()
        for business in businesses:
            try:
                if vector_db and vector_db.client:
                    stats = vector_db.get_collection_stats(business.id)
                    business.document_count = stats.get("total_chunks", 0)
                else:
                    business.document_count = 0
            except Exception as e:
                logger.warning(f"Could not get stats for business {business.id}: {e}")
                business.document_count = 0
    except Exception as e:
        logger.warning(f"Vector DB not available, skipping document counts: {e}")
        # Continue without document counts
    
    return businesses


@router.get("/{business_id}", response_model=Business)
async def get_business(
    business_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get a specific business."""
    businesses = load_businesses()
    
    for business in businesses:
        if business.id == business_id:
            # Update document count
            try:
                vector_db = get_vector_db()
                if vector_db and vector_db.client:
                    stats = vector_db.get_collection_stats(business.id)
                    business.document_count = stats.get("total_chunks", 0)
                else:
                    business.document_count = 0
            except Exception:
                business.document_count = 0
            
            return business
    
    raise HTTPException(status_code=404, detail="Business not found")


@router.put("/{business_id}", response_model=Business)
async def update_business(
    business_id: str,
    business_update: BusinessUpdate,
    api_key: str = Depends(verify_api_key)
):
    """Update a business."""
    businesses = load_businesses()
    
    for i, business in enumerate(businesses):
        if business.id == business_id:
            # Update fields
            update_data = business_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(business, key, value)
            
            businesses[i] = business
            save_businesses(businesses)
            
            logger.info(f"Updated business: {business_id}")
            return business
    
    raise HTTPException(status_code=404, detail="Business not found")


@router.delete("/{business_id}")
async def delete_business(
    business_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete a business (WARNING: This will delete all documents)."""
    businesses = load_businesses()
    
    for i, business in enumerate(businesses):
        if business.id == business_id:
            # Remove from list
            businesses.pop(i)
            save_businesses(businesses)
            
            logger.info(f"Deleted business: {business_id}")
            return {"message": "Business deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Business not found")


