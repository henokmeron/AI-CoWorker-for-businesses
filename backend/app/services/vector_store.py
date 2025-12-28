"""
Vector store service for document storage and retrieval.
Supports ChromaDB (local) and Qdrant (cloud).
"""
import logging
from typing import List, Dict, Any, Optional

# Import ChromaDB with error handling
# Try to import chromadb with fallback
CHROMADB_AVAILABLE = False
chromadb = None
ChromaSettings = None

try:
    # Import chromadb 0.4.14 (before onnxruntime became hard dependency)
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
    logging.info("✅ ChromaDB imported successfully")
except ImportError as e:
    logging.error(f"❌ ChromaDB import failed (ImportError): {e}")
    logging.error("Install with: pip install chromadb==0.4.14")
    CHROMADB_AVAILABLE = False
except Exception as e:
    logging.error(f"❌ ChromaDB import failed: {e}")
    CHROMADB_AVAILABLE = False

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
        
        # STEP 1: Initialize embedding service - REQUIRED
        try:
            self.embedding_service = get_embedding_service()
            logger.info("✅ Embedding service initialized successfully")
        except Exception as e:
            error_msg = f"Could not initialize embedding service: {e}"
            logger.error(f"❌ {error_msg}")
            raise RuntimeError(
                f"{error_msg}. "
                "Set OPENAI_API_KEY environment variable in Render."
            ) from e
        
        # STEP 2: Initialize vector database client - REQUIRED
        self.client = self._initialize_client()
        
        # STEP 3: Validate client exists (should never be None after _initialize_client)
        if self.client is None:
            error_msg = "Vector store client is None after initialization - this should never happen"
            logger.error(f"❌ CRITICAL: {error_msg}")
            raise RuntimeError(error_msg)
        
        logger.info("✅ Vector store client initialized successfully")
    
    def _initialize_client(self):
        """Initialize vector database client. REQUIRED - raises RuntimeError if fails."""
        if self.db_type == "chromadb":
            if not CHROMADB_AVAILABLE:
                error_msg = "ChromaDB is not available - cannot initialize vector store"
                logger.error(error_msg)
                raise RuntimeError(
                    f"{error_msg}. "
                    "Install with: pip install chromadb==0.4.14"
                )
            
            try:
                import os
                # Use persistent directory - /app/data/chromadb in production (Fly.io volume)
                persist_dir = settings.CHROMA_PERSIST_DIR
                
                # Convert relative paths to absolute (for local dev)
                if persist_dir.startswith("./"):
                    persist_dir = os.path.abspath(persist_dir)
                
                # Ensure directory exists and is writable
                os.makedirs(persist_dir, exist_ok=True)
                
                # Verify directory is writable
                test_file = os.path.join(persist_dir, ".test_write")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                except Exception as e:
                    raise RuntimeError(f"ChromaDB directory not writable: {persist_dir} - {e}")
                
                logger.info(f"✅ Initializing ChromaDB at {persist_dir} (persistent volume)")
                
                # Create persistent ChromaDB client
                # Using OpenAI embeddings, not onnxruntime
                client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                
                # Verify client works by listing collections
                try:
                    collections = client.list_collections()
                    logger.info(f"✅ ChromaDB client verified ({len(collections)} collections)")
                    # Log existing collections for debugging
                    if collections:
                        collection_names = [c.name for c in collections]
                        logger.info(f"   Existing collections: {', '.join(collection_names)}")
                    else:
                        logger.info("   No existing collections found (this is OK for first run)")
                except Exception as verify_error:
                    error_msg = f"ChromaDB client verification failed: {verify_error}"
                    logger.error(f"❌ {error_msg}")
                    raise RuntimeError(error_msg) from verify_error
                
                return client
                
            except RuntimeError:
                raise  # Re-raise RuntimeError
            except Exception as e:
                error_msg = f"ChromaDB initialization failed: {e}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                raise RuntimeError(error_msg) from e
        
        elif self.db_type == "qdrant":
            try:
                from qdrant_client import QdrantClient
                
                # If Qdrant URL is localhost and we're in production, fall back to ChromaDB
                if settings.QDRANT_URL and "localhost" in settings.QDRANT_URL:
                    logger.warning("Qdrant URL is localhost, but we're in production. Falling back to ChromaDB.")
                    self.db_type = "chromadb"
                    return self._initialize_client()  # Recursive call with chromadb
                
                qdrant_url = settings.QDRANT_URL or "http://localhost:6333"
                logger.info(f"Initializing Qdrant at {qdrant_url}")
                
                client = QdrantClient(
                    url=qdrant_url,
                    api_key=settings.QDRANT_API_KEY
                )
                return client
            except ImportError:
                logger.warning("qdrant-client not installed. Falling back to ChromaDB.")
                self.db_type = "chromadb"
                return self._initialize_client()  # Recursive call with chromadb
            except Exception as e:
                logger.warning(f"Failed to connect to Qdrant: {e}. Falling back to ChromaDB.")
                self.db_type = "chromadb"
                return self._initialize_client()  # Recursive call with chromadb
        
        else:
            raise ValueError(f"Unsupported vector DB type: {self.db_type}")
    
    def get_collection(self, business_id: str):
        """
        Get or create collection for a business.
        
        Args:
            business_id: Business identifier
        
        Returns:
            Collection object
        
        Raises:
            RuntimeError: If client or embedding service is not available
        """
        if self.client is None:
            error_msg = "Vector store client not initialized. Cannot perform vector operations."
            logger.error(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
        
        if self.embedding_service is None:
            error_msg = "Embedding service not initialized. Cannot create collection without embeddings."
            logger.error(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
        
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
                # Log collection stats for debugging
                count = collection.count()
                logger.info(f"✅ Retrieved existing collection '{collection_name}' with {count} documents (persistent)")
            except Exception:
                # Create new collection with OpenAI embeddings
                collection = self.client.create_collection(
                    name=collection_name,
                    embedding_function=embedding_fn,
                    metadata={"business_id": business_id}
                )
                logger.info(f"✅ Created new collection '{collection_name}' with OpenAI embeddings (persistent)")
            
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
        if self.client is None:
            logger.error("Vector store client not available, skipping document addition")
            raise ValueError("Vector store client not initialized. Cannot add documents.")
        
        if self.embedding_service is None:
            logger.error("Embedding service not available, skipping document addition")
            raise ValueError("Embedding service not initialized. Cannot generate embeddings.")
        
        collection = self.get_collection(business_id)
        if collection is None:
            logger.error(f"Could not get/create collection for business {business_id}")
            raise ValueError(f"Could not get/create collection for business {business_id}")
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} chunks")
        try:
            embeddings = self.embedding_service.embed_documents(texts)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise ValueError(f"Failed to generate embeddings: {e}")
        
        # Create IDs for chunks - MUST be unique across all documents
        # Use document_id + chunk index to ensure uniqueness
        chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(texts))]
        
        # CRITICAL: Check if any chunk IDs already exist (shouldn't happen, but safety check)
        if self.db_type == "chromadb":
            try:
                existing = collection.get(ids=chunk_ids)
                if existing and len(existing['ids']) > 0:
                    logger.warning(f"⚠️  Some chunk IDs already exist - this document may have been uploaded before")
                    # Generate new unique IDs by adding timestamp
                    import time
                    timestamp = int(time.time() * 1000)
                    chunk_ids = [f"{document_id}_{timestamp}_chunk_{i}" for i in range(len(texts))]
                    logger.info(f"Generated new unique chunk IDs with timestamp")
            except Exception:
                # No existing chunks - this is expected for new documents
                pass
        
        # Add document_id to all metadatas
        for meta in metadatas:
            meta["document_id"] = document_id
            meta["business_id"] = business_id
        
        if self.db_type == "chromadb":
            # Get count BEFORE adding to verify accumulation
            count_before = collection.count()
            
            # Add to ChromaDB (persistent storage) - this ADDS, doesn't replace
            collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            # Verify documents were added and accumulated
            count_after = collection.count()
            added_count = count_after - count_before
            logger.info(f"✅ Added {len(chunk_ids)} chunks to collection '{collection.name}'")
            logger.info(f"   Before: {count_before} documents, After: {count_after} documents (added {added_count})")
            logger.info(f"   Document ID: {document_id}, Business ID: {business_id}")
            
            if added_count != len(chunk_ids):
                logger.warning(f"⚠️  Expected to add {len(chunk_ids)} chunks but only {added_count} were added - some may have been duplicates")
        
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
        if self.client is None:
            logger.error("Vector store not available - cannot search")
            return []
        
        try:
            collection = self.get_collection(business_id)
        except RuntimeError as e:
            logger.error(f"Cannot get collection for search: {e}")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_query(query)
        
        if self.db_type == "chromadb":
            # Search in ChromaDB
            try:
                # Check if collection has any documents first
                doc_count = collection.count()
                logger.info(f"   🔍 Searching collection 'business_{business_id}' with {doc_count} documents")
                
                if doc_count == 0:
                    logger.warning(f"   ⚠️  Collection 'business_{business_id}' is empty - no documents to search")
                    return []
                
                # CRITICAL: Filter by business_id to ensure document isolation
                # Even though collection is per business_id, add explicit filter for safety
                search_filter = {"business_id": business_id}
                if filter_metadata:
                    search_filter.update(filter_metadata)
                
                logger.info(f"   🔍 Search filter: {search_filter}")
                
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(k, doc_count),  # Don't ask for more than available
                    where=search_filter
                )
                
                # Format results
                formatted_results = []
                if results and 'ids' in results and len(results['ids']) > 0 and len(results['ids'][0]) > 0:
                    for i in range(len(results['ids'][0])):
                        formatted_results.append({
                            "id": results['ids'][0][i],
                            "text": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "score": 1 - results['distances'][0][i]  # Convert distance to similarity
                        })
                    logger.info(f"   ✅ Found {len(formatted_results)} results from search")
                else:
                    logger.warning(f"   ⚠️  Search returned no results (collection has {doc_count} docs but query matched none)")
                
                return formatted_results
            except Exception as e:
                logger.error(f"   ❌ Error during ChromaDB search: {e}", exc_info=True)
                return []
        
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
        if self.client is None:
            logger.warning("Vector store not available, skipping document deletion")
            return False
        
        collection = self.get_collection(business_id)
        if collection is None:
            return False
        
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
        if not self.client:
            logger.warning("Vector store client not initialized, returning empty stats")
            return {"document_count": 0, "total_chunks": 0}
        
        try:
            collection = self.get_collection(business_id)
            
            if self.db_type == "chromadb":
                count = collection.count()
                return {
                    "document_count": count,
                    "total_chunks": count,
                    "collection_name": f"business_{business_id}"
                }
            elif self.db_type == "qdrant":
                info = self.client.get_collection(collection_name=collection)
                return {
                    "document_count": info.points_count,
                    "total_chunks": info.points_count,
                    "collection_name": collection
                }
        except Exception as e:
            logger.error(f"Error in get_collection_stats: {e}", exc_info=True)
        
        return {"document_count": 0, "total_chunks": 0}


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


