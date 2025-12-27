"""
RAG (Retrieval Augmented Generation) service for intelligent Q&A.
"""
import logging
import time
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

from ..core.config import settings
from .vector_store import get_vector_store
from ..models.chat import ChatMessage, Source

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for document-based question answering.
    
    Features:
    - Multi-provider LLM support (OpenAI, Anthropic, Ollama)
    - Hybrid retrieval (semantic + keyword)
    - Source citation tracking
    - Conversation history support
    """
    
    def __init__(self, llm_provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize RAG service.
        
        Args:
            llm_provider: LLM provider (openai, anthropic, ollama, or None for default)
            model: Model name (or None for default)
        """
        self.provider = llm_provider or settings.LLM_PROVIDER
        self.model = model or self._get_default_model()
        self.llm = self._initialize_llm()
        self.vector_store = get_vector_store()
    
    def _get_default_model(self) -> str:
        """Get default model for provider."""
        if self.provider == "openai":
            return settings.OPENAI_MODEL
        elif self.provider == "anthropic":
            return settings.ANTHROPIC_MODEL
        elif self.provider == "ollama":
            return settings.OLLAMA_MODEL
        return "gpt-4-turbo-preview"
    
    def _initialize_llm(self):
        """Initialize LLM based on provider."""
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not configured")
            
            logger.info(f"Initializing OpenAI LLM with model: {self.model}")
            return ChatOpenAI(
                model=self.model,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1,  # Lower temperature for more factual responses
                streaming=True
            )
        
        elif self.provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                
                if not settings.ANTHROPIC_API_KEY:
                    raise ValueError("Anthropic API key not configured")
                
                logger.info(f"Initializing Anthropic LLM with model: {self.model}")
                return ChatAnthropic(
                    model=self.model,
                    anthropic_api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.1
                )
            except ImportError:
                raise ImportError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
        
        elif self.provider == "ollama":
            logger.info(f"Initializing Ollama LLM with model: {self.model}")
            return ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=self.model,
                temperature=0.1
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def query(
        self,
        business_id: str,
        query: str,
        conversation_history: List[ChatMessage] = None,
        max_sources: int = 5,
        reply_as_me: bool = False
    ) -> Dict[str, Any]:
        """
        Answer a query using RAG.
        
        Args:
            business_id: Business identifier
            query: User question
            conversation_history: Previous conversation messages
            max_sources: Maximum number of source documents to retrieve
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        start_time = time.time()
        
        try:
            # 1. Try to retrieve relevant documents (optional - not required)
            retrieved_docs = []
            context = ""
            
            try:
                logger.info(f"🔍 Searching vector database for business_id='{business_id}', query: {query[:100]}...")
                
                # First check if collection exists and has documents
                try:
                    collection = self.vector_store.get_collection(business_id)
                    if collection and hasattr(collection, 'count'):
                        doc_count = collection.count()
                        logger.info(f"   📊 Collection 'business_{business_id}' has {doc_count} documents")
                        if doc_count == 0:
                            logger.warning(f"   ⚠️  Collection exists but is empty - documents may not have been indexed")
                except Exception as e:
                    logger.warning(f"   Could not check collection stats: {e}")
                
                retrieved_docs = self.vector_store.search(
                    business_id=business_id,
                    query=query,
                    k=max_sources
                )
                if retrieved_docs:
                    context = self._format_context(retrieved_docs)
                    logger.info(f"✅ Found {len(retrieved_docs)} relevant document chunks for business_id='{business_id}'")
                else:
                    logger.warning(f"⚠️  No documents found in vector database for business_id='{business_id}'")
                    logger.warning(f"   This could mean:")
                    logger.warning(f"   1. No documents have been uploaded for this business_id")
                    logger.warning(f"   2. Documents were uploaded but not indexed properly")
                    logger.warning(f"   3. business_id mismatch between upload and query")
                    logger.warning(f"   4. Vector database was cleared or not persisted")
                    # Still continue - will answer as general AI but with warning in prompt
            except Exception as e:
                logger.error(f"❌ Vector store search failed for business_id='{business_id}': {e}", exc_info=True)
                # Continue without documents - can still answer general questions
                retrieved_docs = []
            
            # 2. Build prompt with or without context
            messages = self._build_messages(query, context, conversation_history, has_documents=len(retrieved_docs) > 0, reply_as_me=reply_as_me)
            
            # 3. Generate response with LLM (always call OpenAI, even without documents)
            logger.info(f"Generating response with LLM (provider: {self.provider}, model: {self.model})")
            
            # Double-check API key before calling
            if self.provider == "openai" and not settings.OPENAI_API_KEY:
                raise RuntimeError("OpenAI API key is missing. Please set OPENAI_API_KEY environment variable.")
            
            try:
                response = self.llm.invoke(messages)
                answer = response.content if hasattr(response, 'content') else str(response)
                logger.info(f"LLM response generated successfully: {len(answer)} characters")
            except Exception as e:
                logger.error(f"LLM invocation failed: {e}", exc_info=True)
                error_msg = str(e)
                if "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                    raise RuntimeError(f"OpenAI API key error: {error_msg}. Please check your OPENAI_API_KEY in Render environment variables.")
                raise RuntimeError(f"Failed to generate response from OpenAI: {str(e)}")
            
            # 5. Format sources
            sources = self._format_sources(retrieved_docs)
            
            # 6. Calculate metrics
            response_time = time.time() - start_time
            tokens_used = self._estimate_tokens(messages, answer)
            
            logger.info(f"Query completed in {response_time:.2f}s with {len(sources)} sources")
            
            return {
                "answer": answer,
                "sources": sources,
                "tokens_used": tokens_used,
                "response_time": response_time,
                "metadata": {
                    "model": self.model,
                    "provider": self.provider,
                    "retrieved_docs": len(retrieved_docs)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {str(e)}")
            raise RuntimeError(f"Failed to process query: {str(e)}")
    
    def _format_context(self, docs: List[Dict[str, Any]]) -> str:
        """
        Format retrieved documents into context string.
        
        Args:
            docs: Retrieved documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(docs, 1):
            metadata = doc.get("metadata", {})
            filename = metadata.get("filename", "Unknown")
            page = metadata.get("page_number", "")
            
            page_info = f" (Page {page})" if page else ""
            context_parts.append(
                f"[Source {i}: {filename}{page_info}]\n{doc['text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_messages(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        has_documents: bool = False,
        reply_as_me: bool = False
    ) -> List:
        """
        Build message list for LLM.
        
        Args:
            query: User question
            context: Retrieved context (empty if no documents)
            conversation_history: Previous messages
            has_documents: Whether documents were found
            
        Returns:
            List of messages for LLM
        """
        # System prompt adapts based on whether we have documents and reply mode
        if reply_as_me:
            # Reply as the user (personalized responses)
            if has_documents and context:
                system_prompt = """You are helping the user craft personalized responses based on provided documents.

When answering:
- Write responses as if the user is writing them
- Use information from the provided documents when available
- Maintain a natural, personal tone
- Cite sources when referencing documents
- Be concise and accurate"""
            else:
                system_prompt = """You are helping the user craft personalized responses. Write as if the user is writing, maintaining a natural and personal tone."""
        else:
            # Categorize only mode (default)
            if has_documents and context:
                system_prompt = """You are a helpful AI assistant that answers questions based on uploaded documents.

CRITICAL: The user has uploaded documents. You MUST use the document content provided below to answer their questions.

When answering:
- ALWAYS check the provided documents first before answering
- Use information from the provided documents to answer the user's questions
- Cite sources when referencing documents (e.g., "According to Source 1...")
- If the user asks about "attached file", "uploaded document", or mentions a file name, the information is in the documents below
- Be accurate and specific, using the document content to answer
- If information isn't in the documents, say so clearly
- DO NOT say you can't access documents - the documents are provided below"""
            else:
                from datetime import datetime
                current_date = datetime.now().strftime("%B %d, %Y")
                system_prompt = f"""You are a helpful AI assistant powered by GPT-4o. Answer questions clearly and accurately based on your knowledge as of {current_date}.

IMPORTANT: The user may have uploaded documents, but no documents were found in the vector database for this conversation. This could mean:
1. The document upload failed or is still processing
2. The document was uploaded to a different conversation/business_id
3. The vector database search failed

If the user asks about a specific file or document they mentioned uploading, please inform them that you cannot find that document in the system. Suggest they:
- Check if the upload completed successfully
- Try uploading the document again
- Verify they are asking questions in the same conversation where they uploaded the file

Be helpful, concise, and informative. When providing information, use current knowledge and avoid referencing outdated dates like "as of 2023" unless specifically asked about historical events. Always use the current date ({current_date}) as your knowledge cutoff."""

        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                # Handle both dict and object formats
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                elif hasattr(msg, 'role'):
                    role = msg.role
                    content = msg.content
                else:
                    continue
                
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        
        # Add current query with or without context
        if has_documents and context:
            user_message = f"""Context from business documents:

{context}

Question: {query}

Please provide a helpful answer, citing sources when relevant."""
        else:
            # No documents - just answer the question directly
            user_message = query

        messages.append(HumanMessage(content=user_message))
        
        return messages
    
    def _format_sources(self, docs: List[Dict[str, Any]]) -> List[Source]:
        """
        Format documents as source citations.
        
        Args:
            docs: Retrieved documents
            
        Returns:
            List of Source objects
        """
        sources = []
        
        for doc in docs:
            metadata = doc.get("metadata", {})
            
            # Extract document info
            document_id = metadata.get("document_id", "unknown")
            filename = metadata.get("filename", "Unknown Document")
            page = metadata.get("page_number")
            
            # Create preview of chunk text (first 200 chars)
            chunk_text = doc['text'][:200]
            if len(doc['text']) > 200:
                chunk_text += "..."
            
            sources.append(Source(
                document_id=document_id,
                document_name=filename,
                page=page,
                chunk_text=chunk_text,
                relevance_score=doc.get("score", 0.0)
            ))
        
        return sources
    
    def _estimate_tokens(self, messages: List, response: str) -> int:
        """
        Estimate token usage (rough approximation).
        
        Args:
            messages: Input messages
            response: Generated response
            
        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token
        total_chars = sum(len(str(msg.content)) for msg in messages)
        total_chars += len(response)
        return total_chars // 4
    
    async def query_stream(
        self,
        business_id: str,
        query: str,
        conversation_history: List[ChatMessage] = None,
        max_sources: int = 5
    ):
        """
        Answer a query with streaming response.
        
        Args:
            business_id: Business identifier
            query: User question
            conversation_history: Previous conversation messages
            max_sources: Maximum number of source documents to retrieve
            
        Yields:
            Response chunks
        """
        # Retrieve documents
        retrieved_docs = self.vector_store.search(
            business_id=business_id,
            query=query,
            k=max_sources
        )
        
        if not retrieved_docs:
            yield {"type": "answer", "content": "No documents found to answer this question."}
            return
        
        # Build messages
        context = self._format_context(retrieved_docs)
        messages = self._build_messages(query, context, conversation_history)
        
        # Stream response
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                yield {"type": "answer", "content": chunk.content}
        
        # Send sources at the end
        sources = self._format_sources(retrieved_docs)
        yield {"type": "sources", "content": [s.dict() for s in sources]}


# Global RAG service instance
_rag_service = None


def get_rag_service() -> RAGService:
    """
    Get global RAG service instance (singleton).
    
    Returns:
        RAGService instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


