"""
Chat/Query API routes.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from ...models.chat import ChatRequest, ChatResponse
from ...core.security import verify_api_key
from ...core.config import settings
from ...api.dependencies import get_rag
from ...services.conversation_service import get_conversation_service
from ...models.conversation import Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
    rag_service = Depends(get_rag)
):
    """
    Answer a question using RAG.
    
    The AI will search through all documents uploaded for the specified business
    and provide an answer with source citations.
    """
    try:
        business_id = request.business_id or "default"
        logger.info(f"Chat request for business {business_id}: {request.query[:100]}")
        
        # Validate OpenAI API key
        if not settings.OPENAI_API_KEY:
            logger.error("OpenAI API key not configured")
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable in Render settings."
            )
        
        logger.info(f"Processing query with OpenAI (model: {settings.OPENAI_MODEL})")
        
        result = rag_service.query(
            business_id=business_id,
            query=request.query,
            conversation_history=request.conversation_history or [],
            max_sources=request.max_sources
        )
        
        logger.info(f"Query completed successfully. Response length: {len(result.get('answer', ''))}")
        
        # Save to conversation history if conversation_id provided
        if request.conversation_id:
            try:
                conversation_service = get_conversation_service()
                # Save user message
                user_msg = Message(
                    role="user",
                    content=request.query,
                    sources=[]
                )
                conversation_service.add_message(request.conversation_id, user_msg)
                
                # Save assistant message
                assistant_msg = Message(
                    role="assistant",
                    content=result.get("answer", ""),
                    sources=result.get("sources", [])
                )
                conversation_service.add_message(request.conversation_id, assistant_msg)
                logger.info(f"Saved messages to conversation {request.conversation_id}")
            except Exception as e:
                logger.warning(f"Failed to save messages to conversation history: {e}")
                # Don't fail the request if saving history fails
        
        return ChatResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        # Return a helpful error message
        error_detail = str(e)
        if "api key" in error_detail.lower() or "authentication" in error_detail.lower():
            error_detail = "OpenAI API key not configured or invalid. Please check your OPENAI_API_KEY in Render environment variables."
        elif "rate limit" in error_detail.lower():
            error_detail = "OpenAI rate limit exceeded. Please try again in a moment."
        elif "vector" in error_detail.lower() or "collection" in error_detail.lower():
            # This shouldn't happen anymore, but just in case
            error_detail = "Error accessing documents, but trying to answer anyway..."
        raise HTTPException(status_code=500, detail=f"Failed to process query: {error_detail}")


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
    rag_service = Depends(get_rag)
):
    """
    Answer a question with streaming response.
    
    Returns a stream of response chunks as they are generated.
    """
    try:
        async def generate():
            async for chunk in rag_service.query_stream(
                business_id=request.business_id,
                query=request.query,
                conversation_history=request.conversation_history,
                max_sources=request.max_sources
            ):
                import json
                yield json.dumps(chunk) + "\n"
        
        return StreamingResponse(generate(), media_type="application/x-ndjson")
        
    except Exception as e:
        logger.error(f"Error processing streaming chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


