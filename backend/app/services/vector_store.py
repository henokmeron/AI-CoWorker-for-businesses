"""
Vector store service for document storage and retrieval.
Supports ChromaDB (local) and Qdrant (cloud).
"""
import logging
from typing import List, Dict, Any, Optional

# Import ChromaDB with error handling
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except Exception as e:
    logging.warning(f"ChromaDB import failed: {e}. Some features may not work.")
    CHROMADB_AVAILABLE = False
    chromadb = None
    ChromaSettings = None

from ..core.config import settings
from .embedding_service import get_embedding_service, ChromaEmbeddingFunction

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector store for document embeddings and retrieval.
    
    Supports multiple backends:
    - ChromaDB (local, embedded)
    - Qdrant (cloud-ready, scalable)
    """
    
    def __init__(self, db_type: Optional[str] = None):
        """
        Initialize vector store.
        
        Args:
            db_type: Database type (chromadb, qdrant, or None for default)
        """
        self.db_type = db_type or settings.VECTOR_DB_TYPE
        self.embedding_service = get_embedding_service()
        self.client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize vector database client."""
        if self.db_type == "chromadb":
            if not CHROMADB_AVAILABLE:
                raise RuntimeError(
                    "ChromaDB is not available. Please install it or use Qdrant instead."
                )
            
            logger.info(f"Initializing ChromaDB at {settings.CHROMA_PERSIST_DIR}")
            
            # Create persistent ChromaDB client
            # We'll use OpenAI embeddings, not default onnxruntime
            client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            return client
        
        elif self.db_type == "qdrant":
            try:
                from qdrant_client import QdrantClient
                logger.info(f"Initializing Qdrant at {settings.QDRANT_URL}")
                
                client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )
                return client
            except ImportError:
                raise ImportError("qdrant-client not installed. Run: pip install qdrant-client")
        
        else:
            raise ValueError(f"Unsupported vector DB type: {self.db_type}")
    
    def get_collection(self, business_id: str):
        """
        Get or create collection for a business.
        
        Args:
            business_id: Business identifier
            
        Returns:
            Collection object
        """
        collection_name = f"business_{business_id}"
        
        if self.db_type == "chromadb":
            # Create embedding function wrapper for ChromaDB
            embedding_fn = ChromaEmbeddingFunction(self.embedding_service)
            
            try:
                # Try to get existing collection
                collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=embedding_fn
                )
                logger.info(f"Retrieved existing collection: {collection_name}")
            except Exception:
                # Create new collection with OpenAI embeddings
                collection = self.client.create_collection(
                    name=collection_name,
                    embedding_function=embedding_fn,
                    metadata={"business_id": business_id}
                )
                logger.info(f"Created new collection: {collection_name} with OpenAI embeddings")
            
            return collection
        
        elif self.db_type == "qdrant":
            from qdrant_client.models import Distance, VectorParams
            
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == collection_name for c in collections)
            
            if not collection_exists:
                # Create collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI embedding dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created new Qdrant collection: {collection_name}")
            
            return collection_name  # Return collection name for Qdrant
    
    def add_documents(
        self,
        business_id: str,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        document_id: str
    ) -> List[str]:
        """
        Add documents (chunks) to vector store.
        
        Args:
            business_id: Business identifier
            texts: List of text chunks
            metadatas: List of metadata dicts for each chunk
            document_id: Document identifier
            
        Returns:
            List of chunk IDs
        """
        collection = self.get_collection(business_id)
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} chunks")
        embeddings = self.embedding_service.embed_documents(texts)
        
        # Create IDs for chunks
        chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(texts))]
        
        # Add document_id to all metadatas
        for meta in metadatas:
            meta["document_id"] = document_id
            meta["business_id"] = business_id
        
        if self.db_type == "chromadb":
            # Add to ChromaDB
            collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
        
        elif self.db_type == "qdrant":
            from qdrant_client.models import PointStruct
            
            # Add to Qdrant
            points = [
                PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload={"text": text, **metadata}
                )
                for chunk_id, embedding, text, metadata in zip(chunk_ids, embeddings, texts, metadatas)
            ]
            
            self.client.upsert(
                collection_name=collection,
                points=points
            )
        
        logger.info(f"Added {len(chunk_ids)} chunks to vector store")
        return chunk_ids
    
    def search(
        self,
        business_id: str,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            business_id: Business identifier
            query: Search query
            k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of search results with text, metadata, and scores
        """
        collection = self.get_collection(business_id)
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_query(query)
        
        if self.db_type == "chromadb":
            # Search in ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "score": 1 - results['distances'][0][i]  # Convert distance to similarity
                })
            
            return formatted_results
        
        elif self.db_type == "qdrant":
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Build filter
            query_filter = None
            if filter_metadata:
                conditions = [
                    FieldCondition(key=key, match=MatchValue(value=value))
                    for key, value in filter_metadata.items()
                ]
                query_filter = Filter(must=conditions)
            
            # Search in Qdrant
            results = self.client.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=k,
                query_filter=query_filter
            )
            
            # Format results
            formatted_results = [
                {
                    "id": str(result.id),
                    "text": result.payload.get("text", ""),
                    "metadata": {k: v for k, v in result.payload.items() if k != "text"},
                    "score": result.score
                }
                for result in results
            ]
            
            return formatted_results
        
        return []
    
    def delete_document(self, business_id: str, document_id: str) -> bool:
        """
        Delete all chunks for a document.
        
        Args:
            business_id: Business identifier
            document_id: Document identifier
            
        Returns:
            True if successful
        """
        collection = self.get_collection(business_id)
        
        if self.db_type == "chromadb":
            # Delete from ChromaDB using metadata filter
            collection.delete(
                where={"document_id": document_id}
            )
        
        elif self.db_type == "qdrant":
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Delete from Qdrant
            self.client.delete(
                collection_name=collection,
                points_selector=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )
            )
        
        logger.info(f"Deleted document {document_id} from vector store")
        return True
    
    def get_collection_stats(self, business_id: str) -> Dict[str, Any]:
        """
        Get statistics for a collection.
        
        Args:
            business_id: Business identifier
            
        Returns:
            Statistics dictionary
        """
        collection = self.get_collection(business_id)
        
        if self.db_type == "chromadb":
            count = collection.count()
            return {
                "total_chunks": count,
                "collection_name": f"business_{business_id}"
            }
        
        elif self.db_type == "qdrant":
            info = self.client.get_collection(collection_name=collection)
            return {
                "total_chunks": info.points_count,
                "collection_name": collection
            }
        
        return {}


# Global vector store instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """
    Get global vector store instance (singleton).
    
    Returns:
        VectorStore instance
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


