"""
Application configuration management using Pydantic settings.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


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
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    
    # Default LLM provider (openai, anthropic, or ollama)
    LLM_PROVIDER: str = "openai"
    
    # Vector Database
    # Use qdrant for production (cloud-native, no binary dependencies)
    # Use chromadb for local development only
    VECTOR_DB_TYPE: str = "qdrant"  # chromadb, qdrant, or pinecone
    CHROMA_PERSIST_DIR: str = "./data/chromadb"
    
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
    
    # Storage
    DATA_DIR: str = os.getenv("DATA_DIR", "/app/data")  # Use /app/data in production
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/data/businesses")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


