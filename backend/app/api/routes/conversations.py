"""
Conversation history API routes.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from ...models.conversation import Conversation, ConversationCreate, ConversationUpdate, Message
from ...core.security import verify_api_key
from ...services.conversation_service import get_conversation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=Conversation)
async def create_conversation(
    conversation: ConversationCreate,
    api_key: str = Depends(verify_api_key)
):
    """Create a new conversation."""
    try:
        service = get_conversation_service()
        conv = service.create_conversation(
            business_id=conversation.business_id,
            title=conversation.title
        )
        return conv
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@router.get("", response_model=List[Conversation])
async def list_conversations(
    business_id: str,
    archived: Optional[bool] = None,
    api_key: str = Depends(verify_api_key)
):
    """List conversations for a business."""
    try:
        service = get_conversation_service()
        conversations = service.list_conversations(business_id, archived)
        return conversations
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get a specific conversation."""
    try:
        service = get_conversation_service()
        conversation = service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.post("/{conversation_id}/messages", response_model=Message)
async def add_message(
    conversation_id: str,
    message: Message,
    api_key: str = Depends(verify_api_key)
):
    """Add a message to a conversation."""
    try:
        service = get_conversation_service()
        service.add_message(conversation_id, message)
        return message
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")


@router.post("/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Archive a conversation."""
    try:
        service = get_conversation_service()
        service.archive_conversation(conversation_id)
        return {"message": "Conversation archived successfully"}
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to archive conversation: {str(e)}")

