"""
API dependencies and dependency injection.
"""
from ..services.document_processor import get_document_processor
from ..services.vector_store import get_vector_store
from ..services.rag_service import get_rag_service


def get_doc_processor():
    """Get document processor instance."""
    return get_document_processor()


def get_vector_db():
    """Get vector store instance."""
    return get_vector_store()


def get_rag():
    """Get RAG service instance."""
    return get_rag_service()


