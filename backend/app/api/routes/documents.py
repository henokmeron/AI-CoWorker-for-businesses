"""
Document management API routes.
"""
import logging
import os
import json
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from ...models.document import Document, DocumentUploadResponse
from ...core.config import settings
from ...core.security import verify_api_key
from ...utils.file_utils import get_file_extension, get_file_size, is_file_allowed, ensure_directory
from ...api.dependencies import get_doc_processor, get_vector_db
from ...services.table_reasoning_service import get_table_reasoning_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# JSON file storage for documents metadata - uses persistent volume
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
    """Save documents to JSON file on persistent volume."""
    ensure_directory(str(DOCS_DB_PATH.parent))
    
    # Verify directory is writable
    try:
        test_file = DOCS_DB_PATH.parent / ".test_write"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        logger.error(f"Cannot write to documents storage: {e}")
        raise RuntimeError(f"Storage directory not writable: {e}")
    
    with open(DOCS_DB_PATH, 'w') as f:
        data = [d.dict() for d in documents]
        json.dump(data, f, indent=2, default=str)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    business_id: str = Form(...),
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    api_key: str = Depends(verify_api_key),
    doc_processor = Depends(get_doc_processor),
    vector_db = Depends(get_vector_db)
):
    """
    Upload and process a document.
    
    Steps:
    1. Validate file
    2. Save to persistent storage
    3. Process and extract content
    4. Generate embeddings and store in vector DB
    5. Save metadata
    
    This endpoint REQUIRES:
    - Vector database to be initialized
    - Document processor with handlers
    - Writable storage directory
    """
    # CRITICAL: Validate vector database is available
    if vector_db.client is None:
        logger.error("Vector store client is not initialized - cannot process documents")
        raise HTTPException(
            status_code=503,
            detail="Vector database is not available. The application cannot process documents without a vector database. Please check server logs."
        )
    
    # CRITICAL: Validate document processor has handlers
    if len(doc_processor.handlers) == 0:
        logger.error("No file handlers available - cannot process documents")
        raise HTTPException(
            status_code=503,
            detail="Document processor has no file handlers. Cannot process uploaded files."
        )
    
    # CRITICAL: Log upload start
    logger.info(f"📤 UPLOAD START: business_id='{business_id}', filename='{file.filename}'")
    
    try:
        # Validate filename is present
        if not file.filename:
            logger.error("❌ Upload rejected: Missing filename")
            raise HTTPException(
                status_code=400,
                detail="File filename is missing. Please ensure the file has a name."
            )
        
        # Validate file size
        contents = await file.read()
        file_size = len(contents)
        logger.info(f"📦 File size: {file_size} bytes")
        
        if file_size == 0:
            logger.error("❌ Upload rejected: Empty file")
            raise HTTPException(
                status_code=400,
                detail="File is empty. Please upload a file with content."
            )
        
        is_allowed, error_msg = is_file_allowed(
            file.filename,
            settings.MAX_FILE_SIZE_MB,
            file_size
        )
        
        if not is_allowed:
            logger.error(f"❌ Upload rejected: {error_msg}")
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
        logger.info(f"💾 Saving document to persistent storage for business_id='{business_id}'")
        saved_path = doc_processor.save_document(
            temp_path,
            business_id,
            file.filename
        )
        logger.info(f"✅ Document saved to: {saved_path}")
        
        # Process document (this generates document_id)
        logger.info(f"🔄 Processing document: {file.filename} for business_id='{business_id}'")
        result = doc_processor.process_document(
            saved_path,
            business_id,
            metadata={"original_filename": file.filename}
        )
        
        if not result or not result.get("document_id"):
            logger.error(f"❌ Document processing failed: No document_id generated")
            raise HTTPException(
                status_code=500,
                detail="Document processing failed: Could not generate document ID"
            )
        
        document_id = result.get("document_id")
        logger.info(f"✅ Document processed: document_id='{document_id}', chunks={len(result.get('chunks', []))}")
        
        # Check if file is tabular (XLSX/CSV) for table reasoning
        # CRITICAL: Table ingestion MUST run for tabular files
        file_ext = get_file_extension(file.filename).lower()
        is_tabular = file_ext in ['xlsx', 'xls', 'csv']
        logger.info(f"📊 File type check: extension='{file_ext}', is_tabular={is_tabular}")
        
        # Ingest table if tabular (in addition to normal processing)
        # CRITICAL: This MUST run - do not skip
        table_ingestion_result = None
        if is_tabular:
            logger.info(f"📊 Starting table ingestion for {file.filename} (business_id='{business_id}', document_id='{document_id}')")
            try:
                table_service = get_table_reasoning_service()
                if file_ext in ['xlsx', 'xls']:
                    logger.info(f"📊 Calling ingest_xlsx for {file.filename}")
                    table_ingestion_result = table_service.ingest_xlsx(
                        business_id=business_id,
                        document_id=document_id,
                        filename=file.filename,
                        filepath=saved_path
                    )
                elif file_ext == 'csv':
                    logger.info(f"📊 Calling ingest_csv for {file.filename}")
                    table_ingestion_result = table_service.ingest_csv(
                        business_id=business_id,
                        document_id=document_id,
                        filename=file.filename,
                        filepath=saved_path
                    )
                
                if table_ingestion_result:
                    if table_ingestion_result.get("success"):
                        sheets_ingested = table_ingestion_result.get('sheets_ingested', 0)
                        logger.info(f"✅ Table ingestion SUCCESS: {sheets_ingested} sheets ingested for business_id='{business_id}'")
                    else:
                        error = table_ingestion_result.get("error", "Unknown error")
                        logger.error(f"❌ Table ingestion FAILED: {error}")
                        # Don't fail the whole upload, but log the error
                else:
                    logger.error(f"❌ Table ingestion returned None for {file.filename}")
            except Exception as e:
                logger.error(f"❌ Table ingestion EXCEPTION: {e}", exc_info=True)
                # Continue with normal processing even if table ingestion fails
                # But log it as an error
        else:
            logger.info(f"📄 File is not tabular, skipping table ingestion")
        
        # Store in vector database - REQUIRED step
        chunks = result.get('chunks', [])
        logger.info(f"💾 Storing {len(chunks)} chunks in vector database for business_id='{business_id}'")
        
        # Validate we have chunks to store
        if not result.get("chunks") or len(result["chunks"]) == 0:
            logger.error(f"No chunks extracted from document {file.filename}")
            # Mark document as failed but keep the file
            doc = Document(
                id=result["document_id"],
                business_id=business_id,
                filename=file.filename,
                file_type=get_file_extension(file.filename),
                file_size=file_size,
                file_path=saved_path,
                status="failed",
                chunk_count=0,
                metadata={"error": "No chunks extracted from document"}
            )
            documents = load_documents()
            documents.append(doc)
            save_documents(documents)
            raise HTTPException(
                status_code=500,
                detail="Document processing failed: No text content could be extracted from the document."
            )
        
        chunk_texts = [chunk["text"] for chunk in result["chunks"]]
        chunk_metadatas = [
            {
                **chunk.get("metadata", {}),
                "filename": file.filename,
                "chunk_index": i
            }
            for i, chunk in enumerate(result["chunks"])
        ]
        
        # CRITICAL: Store in vector database - this MUST succeed
        # Log document details before storing
        logger.info(f"📄 Storing document in vector DB:")
        logger.info(f"   Document ID: {result['document_id']}")
        logger.info(f"   Business ID: {business_id}")
        logger.info(f"   Filename: {file.filename}")
        logger.info(f"   Chunks: {len(chunk_texts)}")
        logger.info(f"   Collection: business_{business_id}")
        
        try:
            # Get collection stats BEFORE adding
            try:
                collection = vector_db.get_collection(business_id)
                if collection:
                    count_before = collection.count()
                    logger.info(f"   📊 Collection has {count_before} documents BEFORE adding this one")
            except Exception as e:
                logger.warning(f"   Could not get pre-add collection count: {e}")
                count_before = 0
            
            chunk_ids = vector_db.add_documents(
                business_id=business_id,
                texts=chunk_texts,
                metadatas=chunk_metadatas,
                document_id=result["document_id"]
            )
            
            # Verify documents were actually added
            if chunk_ids and len(chunk_ids) > 0:
                try:
                    collection = vector_db.get_collection(business_id)
                    if collection:
                        count_after = collection.count()
                        added_count = count_after - count_before
                        logger.info(f"   ✅ Successfully added {len(chunk_ids)} chunks")
                        logger.info(f"   📊 Collection now has {count_after} documents (added {added_count})")
                        
                        # Verify this specific document's chunks are in the collection
                        doc_chunks = [cid for cid in chunk_ids if result["document_id"] in cid]
                        logger.info(f"   🔍 Document {result['document_id']} has {len(doc_chunks)} chunks in collection")
                        
                        # List all document_ids in collection to verify isolation
                        try:
                            all_docs = collection.get()
                            if all_docs and 'metadatas' in all_docs:
                                unique_doc_ids = set()
                                for meta in all_docs['metadatas']:
                                    if meta and 'document_id' in meta:
                                        unique_doc_ids.add(meta['document_id'])
                                logger.info(f"   📚 Collection contains {len(unique_doc_ids)} unique documents: {list(unique_doc_ids)[:5]}")
                        except Exception as e:
                            logger.warning(f"   Could not list document IDs: {e}")
                except Exception as e:
                    logger.warning(f"   Could not verify document addition: {e}")
            
            if not chunk_ids or len(chunk_ids) == 0:
                logger.error("Vector database returned no chunk IDs - storage failed")
                # Mark document as failed but keep the file
                doc = Document(
                    id=result["document_id"],
                    business_id=business_id,
                    filename=file.filename,
                    file_type=get_file_extension(file.filename),
                    file_size=file_size,
                    file_path=saved_path,
                    status="failed",
                    chunk_count=0,
                    metadata={"error": "Vector database storage failed"}
                )
                documents = load_documents()
                documents.append(doc)
                save_documents(documents)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to store document in vector database. Document file was saved but cannot be searched."
                )
            logger.info(f"✅ Successfully stored {len(chunk_ids)} chunks in vector database")
            
            # CRITICAL: Verify documents are actually in the collection
            try:
                collection = vector_db.get_collection(business_id)
                if collection and hasattr(collection, 'count'):
                    verified_count = collection.count()
                    logger.info(f"✅ VERIFIED: Collection 'business_{business_id}' now has {verified_count} documents (persistent)")
                    if verified_count == 0:
                        logger.error(f"❌ CRITICAL: Collection is empty after adding documents - persistence may be broken!")
                else:
                    logger.warning(f"⚠️  Could not verify collection count (collection type: {type(collection)})")
            except Exception as e:
                logger.error(f"❌ Could not verify document storage: {e}", exc_info=True)
        except ValueError as e:
            # Vector store validation error
            logger.error(f"Vector database error: {e}", exc_info=True)
            # Mark document as failed but keep the file
            doc = Document(
                id=result["document_id"],
                business_id=business_id,
                filename=file.filename,
                file_type=get_file_extension(file.filename),
                file_size=file_size,
                file_path=saved_path,
                status="failed",
                chunk_count=0,
                metadata={"error": str(e)}
            )
            documents = load_documents()
            documents.append(doc)
            save_documents(documents)
            raise HTTPException(
                status_code=503,
                detail=f"Vector database is not available: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error storing document in vector database: {e}", exc_info=True)
            # Mark document as failed but keep the file
            doc = Document(
                id=result["document_id"],
                business_id=business_id,
                filename=file.filename,
                file_type=get_file_extension(file.filename),
                file_size=file_size,
                file_path=saved_path,
                status="failed",
                chunk_count=0,
                metadata={"error": str(e)}
            )
            documents = load_documents()
            documents.append(doc)
            save_documents(documents)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store document in vector database: {str(e)}"
            )
        
        # Save document metadata - only if vector storage succeeded
        # Include conversation_id in metadata for chat filtering
        doc_metadata = result.get("metadata", {}) or {}
        if conversation_id:
            doc_metadata["conversation_id"] = conversation_id
        
        doc = Document(
            id=result["document_id"],
            business_id=business_id,
            filename=file.filename,
            file_type=get_file_extension(file.filename),
            file_size=file_size,
            file_path=saved_path,
            status="completed",
            chunk_count=len(result["chunks"]),
            metadata=doc_metadata
        )
        
        documents = load_documents()
        documents.append(doc)
        save_documents(documents)
        
        # Clean up temp file with retry logic (handle EBUSY errors)
        if os.path.exists(temp_path):
            max_retries = 5
            retry_delay = 0.5
            for attempt in range(max_retries):
                try:
                    # Check if file is still in use by waiting a bit
                    if attempt > 0:
                        time.sleep(retry_delay * attempt)
                    os.remove(temp_path)
                    logger.info(f"✅ Cleaned up temp file: {temp_path}")
                    break
                except OSError as e:
                    if attempt == max_retries - 1:
                        logger.warning(f"Could not remove temp file {temp_path} after {max_retries} attempts: {e}")
                    else:
                        logger.debug(f"Temp file still in use, retrying in {retry_delay * (attempt + 1)}s...")
                except Exception as e:
                    logger.warning(f"Could not remove temp file {temp_path}: {e}")
                    break
        
        # CRITICAL: Validate ingestion completed
        # Check if document is actually in the system
        try:
            collection = vector_db.get_collection(business_id)
            if collection:
                doc_count = collection.count()
                logger.info(f"✅ Verified: Collection 'business_{business_id}' now has {doc_count} documents")
        except Exception as e:
            logger.warning(f"Could not verify document in collection: {e}")
        
        # CRITICAL: Log final success with all details
        table_sheets = table_ingestion_result.get('sheets_ingested', 0) if table_ingestion_result and table_ingestion_result.get("success") else 0
        logger.info(f"✅ UPLOAD COMPLETE: business_id='{business_id}', document_id='{doc.id}', filename='{doc.filename}', chunks={doc.chunk_count}, table_sheets={table_sheets}")
        
        message = f"Document processed successfully with {doc.chunk_count} chunks"
        if table_sheets > 0:
            message += f" and {table_sheets} table sheet(s) indexed"
        
        # CRITICAL: If table ingestion was supposed to run but didn't, warn
        if is_tabular and table_sheets == 0:
            logger.warning(f"⚠️  WARNING: Tabular file {file.filename} was processed but table ingestion returned 0 sheets!")
            message += " (Note: Table ingestion may have failed - check logs)"
        
        return DocumentUploadResponse(
            document_id=doc.id,
            filename=doc.filename,
            status=doc.status,
            message=message
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


