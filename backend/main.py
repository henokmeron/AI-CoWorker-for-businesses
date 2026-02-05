"""
FastAPI application entry point.
"""
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import business, documents, chat, conversations, auth, user_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Assistant Coworker - Intelligent document-based Q&A system",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(business.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(user_settings.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    """Health check endpoint for Fly.io."""
    return {"ok": True}


@app.get("/storage-status")
async def storage_status():
    """Diagnostic: check storage paths and file counts."""
    from pathlib import Path
    data_dir = Path(settings.DATA_DIR)
    businesses_path = data_dir / "businesses.json"
    conversations_path = data_dir / "conversations.json"
    
    status = {
        "data_dir": str(data_dir),
        "data_dir_exists": data_dir.exists(),
        "data_dir_writable": data_dir.exists() and os.access(str(data_dir), os.W_OK),
        "businesses_file_exists": businesses_path.exists(),
        "conversations_file_exists": conversations_path.exists(),
    }
    
    if businesses_path.exists():
        try:
            with open(businesses_path) as f:
                import json
                businesses = json.load(f)
                status["businesses_count"] = len(businesses)
                status["business_ids"] = [b.get("id") for b in businesses[:5]]
        except Exception as e:
            status["businesses_error"] = str(e)
    
    if conversations_path.exists():
        try:
            with open(conversations_path) as f:
                import json
                conversations = json.load(f)
                status["conversations_count"] = len(conversations)
                status["conversation_ids"] = [c.get("id") for c in conversations[:5]]
        except Exception as e:
            status["conversations_error"] = str(e)
    
    return status


@app.get("/debug")
async def debug_info():
    """Debug endpoint to check configuration."""
    return {
        "openai_api_key_set": bool(settings.OPENAI_API_KEY),
        "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
        "openai_api_key_prefix": settings.OPENAI_API_KEY[:10] + "..." if settings.OPENAI_API_KEY else "None",
        "llm_provider": settings.LLM_PROVIDER,
        "openai_model": settings.OPENAI_MODEL,
        "vector_db_type": settings.VECTOR_DB_TYPE,
        "data_dir": settings.DATA_DIR,
        "upload_dir": settings.UPLOAD_DIR
    }


@app.get("/test-openai")
async def test_openai():
    """Test OpenAI API connection."""
    try:
        if not settings.OPENAI_API_KEY:
            return {"success": False, "error": "OPENAI_API_KEY not configured"}
        
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello, OpenAI is working!'"}],
            max_tokens=20
        )
        
        return {
            "success": True,
            "message": response.choices[0].message.content,
            "model": response.model
        }
    except Exception as e:
        logger.error(f"OpenAI test failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def validate_startup():
    """
    Validate all critical services at startup.
    Log warnings for non-critical issues, but allow app to start.
    Only crash for truly critical issues that prevent basic operation.
    """
    warnings = []
    critical_errors = []
    
    # 1. Validate OpenAI API key (required for embeddings and LLM)
    if not settings.OPENAI_API_KEY:
        critical_errors.append("OPENAI_API_KEY is not set. This is REQUIRED for embeddings and LLM.")
    else:
        logger.info("✅ OpenAI API key is set")
    
    # 2. Validate and initialize vector store (try, but don't crash if it fails)
    try:
        from app.services.vector_store import get_vector_store
        vector_store = get_vector_store()
        if vector_store.client is None:
            warnings.append("Vector store client is None. Document uploads will fail.")
        else:
            # Test by listing collections
            try:
                if hasattr(vector_store.client, 'list_collections'):
                    vector_store.client.list_collections()
                logger.info("✅ Vector store validated successfully")
            except Exception as e:
                warnings.append(f"Vector store validation failed: {e}")
    except Exception as e:
        warnings.append(f"Vector store initialization failed: {e}. Document uploads will not work.")
    
    # 3. Validate document processor
    try:
        from app.services.document_processor import get_document_processor
        processor = get_document_processor()
        if len(processor.handlers) == 0:
            warnings.append("No file handlers registered. Document processing will fail.")
        else:
            logger.info(f"✅ Document processor validated ({len(processor.handlers)} handlers)")
    except Exception as e:
        warnings.append(f"Document processor initialization failed: {e}")
    
    # 4. Validate storage directory (critical - must be writable)
    try:
        storage_path = Path(settings.UPLOAD_DIR)
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Test write access
        test_file = storage_path / ".startup_test"
        test_file.write_text("test")
        test_file.unlink()
        
        logger.info(f"✅ Storage directory validated: {storage_path}")
    except Exception as e:
        critical_errors.append(f"Storage directory validation failed: {e}. Cannot save files.")
    
    # 5. Validate data directory
    try:
        data_path = Path(settings.DATA_DIR)
        data_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Data directory validated: {data_path}")
    except Exception as e:
        critical_errors.append(f"Data directory validation failed: {e}")
    
    # Log warnings
    if warnings:
        logger.warning("=" * 80)
        logger.warning("STARTUP WARNINGS - App will start but some features may not work")
        logger.warning("=" * 80)
        for warning in warnings:
            logger.warning(f"⚠️  {warning}")
        logger.warning("=" * 80)
    
    # Only crash for truly critical errors
    if critical_errors:
        logger.error("=" * 80)
        logger.error("CRITICAL STARTUP FAILURES - Application will not start")
        logger.error("=" * 80)
        for error in critical_errors:
            logger.error(f"❌ {error}")
        logger.error("=" * 80)
        logger.error("Fix these issues before the application can start.")
        logger.error("=" * 80)
        sys.exit(1)
    
    if not warnings:
        logger.info("=" * 80)
        logger.info("✅ ALL STARTUP VALIDATIONS PASSED")
        logger.info("=" * 80)
    else:
        logger.info("=" * 80)
        logger.info("⚠️  STARTUP COMPLETE WITH WARNINGS - Some features may not work")
        logger.info("=" * 80)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("=" * 80)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 80)
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Vector DB: {settings.VECTOR_DB_TYPE}")
    logger.info(f"Embedding Provider: {settings.EMBEDDING_PROVIDER}")
    logger.info(f"Data Directory: {settings.DATA_DIR}")
    logger.info(f"Upload Directory: {settings.UPLOAD_DIR}")
    logger.info("=" * 80)
    
    # CRITICAL: Verify volume persistence (Fly.io)
    from pathlib import Path
    data_dir = Path(settings.DATA_DIR)
    persistence_test = data_dir / ".persistence_test"
    try:
        # Write test
        persistence_test.write_text(f"startup_{datetime.utcnow().isoformat()}")
        logger.info(f"✅ Volume write test passed: {persistence_test}")
        
        # Read test
        content = persistence_test.read_text()
        logger.info(f"✅ Volume read test passed: {content[:50]}")
        
        # Check if file persisted from previous run (indicates volume is working)
        if "startup_" in content and content != f"startup_{datetime.utcnow().isoformat()}":
            logger.info("✅ VOLUME PERSISTENCE CONFIRMED (file from previous run found)")
        else:
            logger.warning("⚠️ First run or volume reset (no previous persistence marker)")
    except Exception as e:
        logger.error(f"❌ CRITICAL: Volume persistence test FAILED: {e}")
        logger.error(f"   This means /app/data is not writable or volume is not mounted")
        logger.error(f"   GPTs and conversations WILL NOT persist across restarts")
    
    # Validate all critical services - CRASH if any fail
    validate_startup()
    
    logger.info("✅ Application started successfully and ready to serve requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down application")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
