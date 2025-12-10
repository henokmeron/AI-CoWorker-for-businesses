"""
Embedding service supporting multiple providers.
"""
import logging
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings

from ..core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings.
    
    Supports multiple providers:
    - OpenAI (text-embedding-3-small, text-embedding-3-large, etc.)
    - Local models via Ollama
    """
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize embedding service.
        
        Args:
            provider: Embedding provider (openai, ollama, or None for default)
            model: Model name (or None for default)
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.model = model or settings.EMBEDDING_MODEL
        self.embeddings = self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize embedding model based on provider."""
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not configured")
            
            logger.info(f"Initializing OpenAI embeddings with model: {self.model}")
            return OpenAIEmbeddings(
                model=self.model,
                openai_api_key=settings.OPENAI_API_KEY
            )
        
        elif self.provider == "ollama":
            logger.info(f"Initializing Ollama embeddings with model: {self.model}")
            return OllamaEmbeddings(
                base_url=settings.OLLAMA_BASE_URL,
                model=self.model
            )
        
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as e:
            logger.error(f"Error generating document embeddings: {str(e)}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query.
        
        Args:
            text: Query text
            
        Returns:
            Embedding vector
        """
        try:
            return self.embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise


# Global embedding service instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """
    Get global embedding service instance (singleton).
    
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


class ChromaEmbeddingFunction:
    """
    Wrapper for LangChain embeddings to work with ChromaDB.
    This avoids ChromaDB's default onnxruntime dependency.
    """
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for ChromaDB."""
        return self.embedding_service.embed_documents(input)


