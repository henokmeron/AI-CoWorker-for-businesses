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
from ...services.table_reasoning_service import get_table_reasoning_service
from ...api.routes.documents import load_documents
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
        # CRITICAL: Reject missing business_id - no fallback to "temp_chat"
        if not request.business_id:
            raise HTTPException(
                status_code=400,
                detail="business_id is required. Each conversation must have its own document collection."
            )
        business_id = request.business_id
        logger.info(f"💬 Chat request for business_id='{business_id}': {request.query[:100]}")
        
        # Validate OpenAI API key
        if not settings.OPENAI_API_KEY:
            logger.error("OpenAI API key not configured")
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable in Render settings."
            )
        
        logger.info(f"Processing query with OpenAI (model: {settings.OPENAI_MODEL})")
        
        # Check if we should use table reasoning
        # First, check if user has uploaded tabular files
        # CRITICAL: Filter documents by business_id AND conversation_id (if provided)
        documents = load_documents()
        docs = [d for d in documents if d.business_id == business_id and d.status == "processed"]
        
        if request.conversation_id:
            docs = [
                d for d in docs
                if (d.metadata or {}).get("conversation_id") == request.conversation_id
            ]
        
        tabular_docs = [d for d in docs if d.filename.lower().endswith(('.xlsx', '.xls', '.csv'))]
        has_tabular_uploads = len(tabular_docs) > 0
        
        # Try table reasoning first if appropriate
        table_result = None
        if has_tabular_uploads:
            try:
                table_service = get_table_reasoning_service()
                if table_service.should_use_table(request.query, has_tabular_uploads):
                    logger.info("📊 Query matches table reasoning triggers, attempting table reasoning...")
                    try:
                        table_result = table_service.answer_from_tables(business_id, request.query)
                    except Exception as table_error:
                        logger.error(f"Table reasoning service error: {table_error}", exc_info=True)
                        table_result = None  # Force fallback to RAG
                    
                    # ✅ If table reasoning needs clarification, return it immediately (NO RAG fallback)
                    if table_result and table_result.get("needs_clarification", False):
                        logger.info("📋 Table reasoning needs clarification, returning clarification")
                        result = {
                            "answer": table_result.get("answer", ""),
                            "sources": table_result.get("sources", []),
                            "tokens_used": 0,
                            "response_time": 0,
                            "metadata": {
                                "model": "table_reasoning",
                                "provider": "pandas",
                                "confidence": table_result.get("confidence", 0),
                                "provenance": table_result.get("provenance", {}),
                                "needs_clarification": True,
                            }
                        }
                        return ChatResponse(**result)
                    
                    # Use table result if confidence is high enough (0.5+)
                    if table_result and table_result.get("confidence", 0) >= 0.5:
                        logger.info("✅ Table reasoning succeeded with high confidence")
                        # Use table result
                        result = {
                            "answer": table_result.get("answer", ""),
                            "sources": table_result.get("sources", []),
                            "tokens_used": 0,  # Table reasoning doesn't use tokens the same way
                            "response_time": 0,
                            "metadata": {
                                "model": "table_reasoning",
                                "provider": "pandas",
                                "retrieved_docs": 0,
                                "confidence": table_result.get("confidence", 0),
                                "provenance": table_result.get("provenance", {})
                            }
                        }
                        
                        # Save to conversation history
                        if request.conversation_id:
                            try:
                                conversation_service = get_conversation_service()
                                user_msg = Message(
                                    role="user",
                                    content=request.query,
                                    sources=[]
                                )
                                conversation_service.add_message(request.conversation_id, user_msg)
                                
                                assistant_msg = Message(
                                    role="assistant",
                                    content=result.get("answer", ""),
                                    sources=result.get("sources", [])
                                )
                                conversation_service.add_message(request.conversation_id, assistant_msg)
                                logger.info(f"✅ Saved table reasoning messages to conversation {request.conversation_id}")
                            except Exception as e:
                                logger.error(f"Failed to save table reasoning to conversation history: {e}", exc_info=True)
                        
                        return ChatResponse(**result)
                    else:
                        if table_result:
                            logger.info(f"⚠️  Table reasoning returned low confidence ({table_result.get('confidence', 0)}), falling back to RAG")
                        else:
                            logger.info("⚠️  Table reasoning returned None, falling back to RAG")
            except Exception as e:
                logger.warning(f"Table reasoning failed, falling back to RAG: {e}", exc_info=True)
                table_result = None  # Ensure we fall back to RAG
        
        # Fall back to normal RAG
        logger.info(f"💬 Falling back to RAG service for business_id='{business_id}'")
        
        # CRITICAL DIAGNOSTIC: Check if documents exist for this business_id
        try:
            from ...services.vector_store import get_vector_store
            vector_store = get_vector_store()
            collection = vector_store.get_collection(business_id)
            if collection:
                doc_count = collection.count()
                logger.info(f"📊 DIAGNOSTIC: Collection 'business_{business_id}' has {doc_count} documents")
                if doc_count == 0:
                    logger.error(f"❌ CRITICAL: Collection 'business_{business_id}' is EMPTY!")
                    logger.error(f"   This means no documents were uploaded for this conversation")
                    logger.error(f"   OR documents were uploaded to a different business_id")
                    logger.error(f"   Check if upload used the same business_id: '{business_id}'")
                    # List all documents to see what business_ids exist
                    try:
                        all_docs = load_documents()
                        matching_docs = [d for d in all_docs if d.business_id == business_id]
                        logger.error(f"   Documents in DB with business_id='{business_id}': {len(matching_docs)}")
                        if len(matching_docs) > 0:
                            logger.error(f"   Document IDs: {[d.id for d in matching_docs[:5]]}")
                            logger.error(f"   ⚠️  Documents exist in DB but NOT in vector store - storage may have failed!")
                        else:
                            logger.error(f"   ⚠️  No documents in DB with business_id='{business_id}' - upload may have failed!")
                    except Exception as e:
                        logger.error(f"   Could not check documents: {e}")
            else:
                logger.error(f"❌ CRITICAL: Could not get collection for business_id='{business_id}'")
        except Exception as e:
            logger.error(f"❌ Could not check collection status: {e}", exc_info=True)
        
        try:
            result = rag_service.query(
                business_id=business_id,
                query=request.query,
                conversation_history=request.conversation_history or [],
                max_sources=request.max_sources,
                reply_as_me=request.reply_as_me
            )
            
            if not result:
                logger.error("RAG service returned None - no answer generated")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate response. Please check if documents are uploaded and try again."
                )
            
            if not result.get("answer"):
                logger.warning(f"RAG service returned result but no answer field. Result keys: {result.keys() if result else 'None'}")
                result["answer"] = "I apologize, but I couldn't generate a response. Please try rephrasing your question."
            
            logger.info(f"✅ Query completed successfully. Response length: {len(result.get('answer', ''))}")
        except HTTPException:
            raise
        except Exception as rag_error:
            logger.error(f"RAG service error: {rag_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process query with RAG service: {str(rag_error)}"
            )
        
        # Save to conversation history if conversation_id provided
        # This is important for persistence - try hard to save
        if request.conversation_id:
            try:
                conversation_service = get_conversation_service()
                # Save user message BEFORE LLM response
                user_msg = Message(
                    role="user",
                    content=request.query,
                    sources=[]
                )
                conversation_service.add_message(request.conversation_id, user_msg)
                
                # Save assistant message AFTER LLM response
                assistant_msg = Message(
                    role="assistant",
                    content=result.get("answer", ""),
                    sources=result.get("sources", [])
                )
                conversation_service.add_message(request.conversation_id, assistant_msg)
                logger.info(f"✅ Saved messages to conversation {request.conversation_id}")
            except Exception as e:
                # Log error but don't fail the request - conversation history is important but not critical
                logger.error(f"Failed to save messages to conversation history: {e}", exc_info=True)
                # Continue - user still gets their answer
        
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


