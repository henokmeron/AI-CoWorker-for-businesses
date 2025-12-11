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
        max_sources: int = 5
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
            # 1. Retrieve relevant documents
            logger.info(f"Retrieving documents for query: {query[:100]}...")
            try:
                retrieved_docs = self.vector_store.search(
                    business_id=business_id,
                    query=query,
                    k=max_sources
                )
            except Exception as e:
                logger.warning(f"Error searching vector store: {e}. Returning empty results.")
                retrieved_docs = []
            
            if not retrieved_docs:
                return {
                    "answer": "I don't have any documents uploaded yet to answer this question. Please upload relevant documents first using the Documents tab.",
                    "sources": [],
                    "tokens_used": 0,
                    "response_time": time.time() - start_time
                }
            
            # 2. Format context from retrieved documents
            if retrieved_docs:
                context = self._format_context(retrieved_docs)
            else:
                context = "No relevant documents found."
            
            # 3. Build prompt with context and conversation history
            messages = self._build_messages(query, context, conversation_history)
            
            # 4. Generate response
            logger.info("Generating response with LLM")
            try:
                response = self.llm.invoke(messages)
                answer = response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error(f"LLM invocation failed: {e}")
                raise RuntimeError(f"Failed to generate response: {str(e)}")
            
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
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> List:
        """
        Build message list for LLM.
        
        Args:
            query: User question
            context: Retrieved context
            conversation_history: Previous messages
            
        Returns:
            List of messages for LLM
        """
        system_prompt = """You are an AI assistant that helps answer questions based on business documents.

Your task is to:
1. Answer questions accurately using ONLY the information in the provided context
2. Cite your sources by mentioning the source number (e.g., "According to Source 1...")
3. If the answer is not in the context, clearly state that you don't have that information
4. Be concise and direct, but provide enough detail to be helpful
5. If there are multiple relevant pieces of information, synthesize them into a coherent answer
6. Maintain a professional and helpful tone

Remember: Only use information from the provided sources. Do not make up information."""

        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
        
        # Add current query with context
        user_message = f"""Context from business documents:

{context}

Question: {query}

Please answer the question using the information from the context above. Cite your sources."""

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


