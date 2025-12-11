"""
Document management API routes.
"""
import logging
import os
import json
from typing import List
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from ...models.document import Document, DocumentUploadResponse
from ...core.config import settings
from ...core.security import verify_api_key
from ...utils.file_utils import get_file_extension, get_file_size, is_file_allowed, ensure_directory
from ...api.dependencies import get_doc_processor, get_vector_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Simple JSON file storage for documents metadata
DOCS_DB_PATH = Path(settings.DATA_DIR) / "documents.json"


def load_documents() -> List[Document]:
    """Load documents from JSON file."""
    if not DOCS_DB_PATH.exists():
        return []
    
    try:
        with open(DOCS_DB_PATH, 'r') as f:
            data = json.load(f)
            return [Document(**d) for d in data]
    except Exception as e:
        logger.error(f"Error loading documents: {str(e)}")
        return []


def save_documents(documents: List[Document]):
    """Save documents to JSON file."""
    ensure_directory(str(DOCS_DB_PATH.parent))
    
    with open(DOCS_DB_PATH, 'w') as f:
        data = [d.dict() for d in documents]
        json.dump(data, f, indent=2, default=str)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    business_id: str = Form(...),
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
    doc_processor = Depends(get_doc_processor),
    vector_db = Depends(get_vector_db)
):
    """
    Upload and process a document.
    
    Steps:
    1. Validate file
    2. Save to business directory
    3. Process and extract content
    4. Generate embeddings and store in vector DB
    5. Save metadata
    """
    try:
        # Validate file size
        contents = await file.read()
        file_size = len(contents)
        
        is_allowed, error_msg = is_file_allowed(
            file.filename,
            settings.MAX_FILE_SIZE_MB,
            file_size
        )
        
        if not is_allowed:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Save to temp file first (use /tmp in production, tempfile in local)
        import tempfile
        import os
        from pathlib import Path
        
        # Use /tmp in Docker/production, system temp in local
        if os.path.exists("/tmp"):
            temp_dir = "/tmp"
        else:
            temp_dir = tempfile.gettempdir()
        
        os.makedirs(temp_dir, exist_ok=True)
        # Sanitize filename for cross-platform compatibility
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
        temp_path = os.path.join(temp_dir, safe_filename)
        
        logger.info(f"Saving temp file to: {temp_path}")
        with open(temp_path, "wb") as f:
            f.write(contents)
        
        # Save to business directory
        saved_path = doc_processor.save_document(
            temp_path,
            business_id,
            file.filename
        )
        
        # Process document
        logger.info(f"Processing document: {file.filename}")
        result = doc_processor.process_document(
            saved_path,
            business_id,
            metadata={"original_filename": file.filename}
        )
        
        # Store in vector database
        logger.info(f"Storing {len(result['chunks'])} chunks in vector database")
        chunk_texts = [chunk["text"] for chunk in result["chunks"]]
        chunk_metadatas = [
            {
                **chunk.get("metadata", {}),
                "filename": file.filename,
                "chunk_index": i
            }
            for i, chunk in enumerate(result["chunks"])
        ]
        
        vector_db.add_documents(
            business_id=business_id,
            texts=chunk_texts,
            metadatas=chunk_metadatas,
            document_id=result["document_id"]
        )
        
        # Save document metadata
        doc = Document(
            id=result["document_id"],
            business_id=business_id,
            filename=file.filename,
            file_type=get_file_extension(file.filename),
            file_size=file_size,
            file_path=saved_path,
            status="completed",
            chunk_count=len(result["chunks"]),
            metadata=result.get("metadata", {})
        )
        
        documents = load_documents()
        documents.append(doc)
        save_documents(documents)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        logger.info(f"Successfully uploaded and processed: {file.filename}")
        
        return DocumentUploadResponse(
            document_id=doc.id,
            filename=doc.filename,
            status=doc.status,
            message=f"Document processed successfully with {doc.chunk_count} chunks"
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.get("", response_model=List[Document])
async def list_documents(
    business_id: str,
    api_key: str = Depends(verify_api_key)
):
    """List all documents for a business."""
    documents = load_documents()
    return [doc for doc in documents if doc.business_id == business_id]


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get a specific document."""
    documents = load_documents()
    
    for doc in documents:
        if doc.id == document_id:
            return doc
    
    raise HTTPException(status_code=404, detail="Document not found")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    api_key: str = Depends(verify_api_key),
    vector_db = Depends(get_vector_db)
):
    """Delete a document."""
    documents = load_documents()
    
    for i, doc in enumerate(documents):
        if doc.id == document_id:
            # Delete from vector store
            vector_db.delete_document(doc.business_id, document_id)
            
            # Delete file
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
            
            # Remove from metadata
            documents.pop(i)
            save_documents(documents)
            
            logger.info(f"Deleted document: {document_id}")
            return {"message": "Document deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Document not found")


