"""
Application configuration management using Pydantic settings.
"""
import os
import logging
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "AI Assistant Coworker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_KEY: str = "change-this-in-production"
    
    # LLM Settings
    # CRITICAL: Check both os.getenv and BaseSettings for Railway compatibility
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key from environment variable"
    )
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    
    # Default LLM provider (openai, anthropic, or ollama)
    LLM_PROVIDER: str = "openai"
    
    # Vector Database
    # Use chromadb by default (works everywhere)
    # Use qdrant for production if configured
    VECTOR_DB_TYPE: str = "chromadb"  # chromadb, qdrant, or pinecone
    # Use persistent volume path in production (/app/data is mounted from fly.toml)
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "/app/data/chromadb")
    
    # Qdrant settings (use Qdrant Cloud free tier or self-hosted)
    QDRANT_URL: Optional[str] = "http://localhost:6333"  # Default to local, override with env var
    QDRANT_API_KEY: Optional[str] = None
    
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    
    # Embeddings
    EMBEDDING_PROVIDER: str = "openai"  # openai or local
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Document Processing
    MAX_FILE_SIZE_MB: int = 50
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    OCR_ENABLED: bool = True
    
    # Multi-tenant
    MULTI_TENANT_ENABLED: bool = True
    DEFAULT_BUSINESS_ID: str = "demo_business"
    
    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8501", "http://localhost:3000"]
    
    # Storage - Use Fly.io persistent volume at /app/data
    # This is mounted from fly.toml: [[mounts]] destination = "/app/data"
    DATA_DIR: str = os.getenv("DATA_DIR", "/app/data")  # Persistent volume on Fly.io
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/data/businesses")  # Documents stored here
    
    # Cloud Storage (for permanent document storage)
    USE_CLOUD_STORAGE: bool = os.getenv("USE_CLOUD_STORAGE", "false").lower() == "true"
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "s3")  # s3, gcs, azure
    
    # AWS S3 Settings
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_REGION: str = os.getenv("AWS_S3_REGION", "us-east-1")
    
    # Database for conversation history (PostgreSQL/Neon)
    DATABASE_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # CRITICAL: Ensure Railway environment variables are read
        env_file_encoding = 'utf-8'
        # Allow reading from os.environ directly (Railway compatibility)
        extra = "ignore"


# Global settings instance
# CRITICAL: After instantiation, check os.environ directly for Railway compatibility
settings = Settings()

# RAILWAY FIX: Pydantic Settings may not always pick up Railway env vars
# Check os.environ directly and override if needed
if not settings.OPENAI_API_KEY:
    # Try multiple possible variable names (Railway might set it differently)
    openai_key = (
        os.getenv("OPENAI_API_KEY") or 
        os.getenv("openai_api_key") or 
        os.getenv("OpenAI_API_Key")
    )
    
    # RAILWAY WORKAROUND: Check if Railway is using a different mechanism
    # Sometimes Railway variables are available but not in os.environ immediately
    # Try reading from Railway's internal variable system
    if not openai_key:
        # Railway might expose variables via different mechanisms
        # Check all environment variables for anything that looks like an OpenAI key
        all_env = dict(os.environ)
        for key, value in all_env.items():
            if "OPENAI" in key.upper() and value and value.startswith("sk-"):
                logger.info(f"✅ Found OpenAI key in variable: {key} (Railway workaround)")
                openai_key = value
                break
    
    if openai_key:
        logger.info("✅ Found OPENAI_API_KEY via os.environ fallback (Railway compatibility)")
        settings.OPENAI_API_KEY = openai_key
    else:
        logger.error("❌ OPENAI_API_KEY not found in environment variables")
        logger.error("   Checked: OPENAI_API_KEY, openai_api_key, OpenAI_API_Key")
        logger.error("   Scanned all env vars for OpenAI-related keys")
        logger.error("   Railway Variables must have exact name: OPENAI_API_KEY")
        logger.error("   ACTION REQUIRED: In Railway, try:")
        logger.error("   1. Delete the variable and re-add it")
        logger.error("   2. Use 'Raw Editor' to set it")
        logger.error("   3. Set it at PROJECT level (not just service level)")
        logger.error("   4. Force a full redeploy after setting")


