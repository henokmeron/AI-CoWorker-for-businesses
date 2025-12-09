"""
Chat/Query API routes.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from ...models.chat import ChatRequest, ChatResponse
from ...core.security import verify_api_key
from ...api.dependencies import get_rag

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
        logger.info(f"Chat request for business {request.business_id}: {request.query[:100]}")
        
        result = rag_service.query(
            business_id=request.business_id,
            query=request.query,
            conversation_history=request.conversation_history,
            max_sources=request.max_sources
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


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


