# Fly.io Environment Variables

## Required Environment Variables

These are the **minimum required** environment variables for the app to run:

### 1. OPENAI_API_KEY (REQUIRED)
- **Purpose**: Used for embeddings and LLM responses
- **Critical**: Without this, the vector store will fail to initialize and the app will crash
- **How to set**:
  ```powershell
  flyctl secrets set OPENAI_API_KEY=your-openai-api-key-here -a ai-coworker-for-businesses
  ```

### 2. API_KEY (REQUIRED)
- **Purpose**: API authentication key for backend requests
- **Default**: `change-this-in-production` (MUST be changed!)
- **How to set**:
  ```powershell
  flyctl secrets set API_KEY=your-secure-api-key-here -a ai-coworker-for-businesses
  ```

### 3. DATABASE_URL (REQUIRED if using PostgreSQL)
- **Purpose**: PostgreSQL connection string for conversation history
- **Format**: `postgresql://user:password@host:port/database`
- **Example (Neon)**: `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require`
- **How to set**:
  ```powershell
  flyctl secrets set DATABASE_URL=your-postgres-connection-string -a ai-coworker-for-businesses
  ```

## Optional Environment Variables

### LLM Configuration
- `LLM_PROVIDER`: Default `openai` (options: `openai`, `anthropic`, `ollama`)
- `OPENAI_MODEL`: Default `gpt-4-turbo-preview`
- `ANTHROPIC_API_KEY`: Required if using Anthropic
- `ANTHROPIC_MODEL`: Default `claude-3-sonnet-20240229`

### Embeddings
- `EMBEDDING_PROVIDER`: Default `openai` (options: `openai`, `local`)
- `EMBEDDING_MODEL`: Default `text-embedding-3-small`

### Vector Database
- `VECTOR_DB_TYPE`: Default `chromadb` (options: `chromadb`, `qdrant`, `pinecone`)
- `CHROMA_PERSIST_DIR`: Default `./data/chromadb` (will use `/app/data/chromadb` in production)

### Security
- `SECRET_KEY`: Default `change-this-secret-key-in-production` (MUST be changed!)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Default `1440` (24 hours)

### Storage Paths (Auto-configured for Fly.io)
- `DATA_DIR`: Default `/app/data` (mounted volume)
- `UPLOAD_DIR`: Default `/app/data/businesses`

## Quick Setup Commands

Run these commands to set all required secrets:

```powershell
# Set OpenAI API Key (REQUIRED)
flyctl secrets set OPENAI_API_KEY=sk-your-key-here -a ai-coworker-for-businesses

# Set API Key (REQUIRED - change from default)
flyctl secrets set API_KEY=your-secure-random-key-here -a ai-coworker-for-businesses

# Set Database URL (REQUIRED if using PostgreSQL)
flyctl secrets set DATABASE_URL=postgresql://user:pass@host:port/dbname -a ai-coworker-for-businesses

# Set Secret Key (REQUIRED - change from default)
flyctl secrets set SECRET_KEY=your-secret-key-here -a ai-coworker-for-businesses
```

## Verify Secrets

To check what secrets are set:
```powershell
flyctl secrets list -a ai-coworker-for-businesses
```

## After Setting Secrets

After setting secrets, restart the app:
```powershell
flyctl apps restart -a ai-coworker-for-businesses
```

Or redeploy:
```powershell
flyctl deploy -a ai-coworker-for-businesses
```



