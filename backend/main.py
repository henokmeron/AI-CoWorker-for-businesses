"""
FastAPI application entry point.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import business, documents, chat, conversations, auth

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
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


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
        "data_dir": settings.DATA_DIR
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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Vector DB: {settings.VECTOR_DB_TYPE}")
    logger.info(f"Embedding Provider: {settings.EMBEDDING_PROVIDER}")
    
    # Force initialization of document processor to register handlers
    try:
        from app.services.document_processor import get_document_processor
        processor = get_document_processor()
        handler_count = len(processor.handlers)
        logger.info(f"✅ Document processor initialized with {handler_count} handler(s)")
        if handler_count == 0:
            logger.error("⚠️ WARNING: No file handlers registered! File uploads will fail!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize document processor: {e}", exc_info=True)
    
    # Force initialization of vector store
    try:
        from app.services.vector_store import get_vector_store
        vector_store = get_vector_store()
        if vector_store.client:
            logger.info("✅ Vector store initialized successfully")
        else:
            logger.warning("⚠️ Vector store client not initialized (may be expected in some environments)")
    except Exception as e:
        logger.error(f"❌ Failed to initialize vector store: {e}", exc_info=True)
    
    logger.info("✅ Startup complete")


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


