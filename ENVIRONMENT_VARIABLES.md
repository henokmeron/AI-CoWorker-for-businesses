# Environment Variables & Secrets for Fly.io

## How to Set Secrets in Fly.io

Use the `flyctl secrets set` command:

```bash
flyctl secrets set KEY=value -a ai-coworker-for-businesses
```

To view current secrets:
```bash
flyctl secrets list -a ai-coworker-for-businesses
```

---

## 🔴 REQUIRED Secrets (Must Set)

### 1. OPENAI_API_KEY
**Purpose:** Used for embeddings and LLM responses  
**Critical:** Without this, vector store and chat will not work  
**How to get:** https://platform.openai.com/api-keys

```bash
flyctl secrets set OPENAI_API_KEY=sk-your-actual-key-here -a ai-coworker-for-businesses
```

### 2. API_KEY
**Purpose:** API authentication key for backend requests  
**Default:** `change-this-in-production` (INSECURE - must change!)  
**Generate:** Use a long random string (e.g., `openssl rand -hex 32`)

```bash
flyctl secrets set API_KEY=your-secure-random-key-here -a ai-coworker-for-businesses
```

---

## 🟡 OPTIONAL but Recommended

### 3. SECRET_KEY
**Purpose:** JWT token signing (for future auth features)  
**Default:** `change-this-secret-key-in-production` (INSECURE)  
**Generate:** Use a long random string

```bash
flyctl secrets set SECRET_KEY=your-secure-random-key-here -a ai-coworker-for-businesses
```

### 4. DATABASE_URL
**Purpose:** PostgreSQL connection for conversation history  
**Format:** `postgresql://user:password@host:port/database?sslmode=require`  
**Example (Neon):** `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require`

```bash
flyctl secrets set DATABASE_URL=your-postgres-connection-string -a ai-coworker-for-businesses
```

**Note:** If not set, conversations are stored in JSON file on persistent volume (works fine for most cases)

---

## 🟢 OPTIONAL Configuration

### LLM Settings
```bash
# Change LLM provider (default: openai)
flyctl secrets set LLM_PROVIDER=openai -a ai-coworker-for-businesses

# Change OpenAI model (default: gpt-4-turbo-preview)
flyctl secrets set OPENAI_MODEL=gpt-4-turbo-preview -a ai-coworker-for-businesses

# If using Anthropic instead
flyctl secrets set ANTHROPIC_API_KEY=your-key -a ai-coworker-for-businesses
flyctl secrets set LLM_PROVIDER=anthropic -a ai-coworker-for-businesses
```

### Vector Database
```bash
# Use Qdrant instead of ChromaDB (default: chromadb)
flyctl secrets set VECTOR_DB_TYPE=qdrant -a ai-coworker-for-businesses
flyctl secrets set QDRANT_URL=https://your-qdrant-url -a ai-coworker-for-businesses
flyctl secrets set QDRANT_API_KEY=your-key -a ai-coworker-for-businesses
```

### Cloud Storage (AWS S3)
```bash
# Enable cloud storage (default: false, uses Fly.io volume)
flyctl secrets set USE_CLOUD_STORAGE=true -a ai-coworker-for-businesses
flyctl secrets set AWS_S3_BUCKET=your-bucket-name -a ai-coworker-for-businesses
flyctl secrets set AWS_ACCESS_KEY_ID=your-key -a ai-coworker-for-businesses
flyctl secrets set AWS_SECRET_ACCESS_KEY=your-secret -a ai-coworker-for-businesses
flyctl secrets set AWS_S3_REGION=us-east-1 -a ai-coworker-for-businesses
```

**Note:** By default, documents are stored on Fly.io persistent volume (no S3 needed)

---

## 📋 Quick Setup Commands

### Minimum Required Setup:
```bash
flyctl secrets set OPENAI_API_KEY=sk-your-key -a ai-coworker-for-businesses
flyctl secrets set API_KEY=$(openssl rand -hex 32) -a ai-coworker-for-businesses
flyctl secrets set SECRET_KEY=$(openssl rand -hex 32) -a ai-coworker-for-businesses
```

### With PostgreSQL (Neon):
```bash
flyctl secrets set OPENAI_API_KEY=sk-your-key -a ai-coworker-for-businesses
flyctl secrets set API_KEY=$(openssl rand -hex 32) -a ai-coworker-for-businesses
flyctl secrets set SECRET_KEY=$(openssl rand -hex 32) -a ai-coworker-for-businesses
flyctl secrets set DATABASE_URL=postgresql://user:pass@host/db?sslmode=require -a ai-coworker-for-businesses
```

---

## 🔍 Check Your Current Secrets

```bash
flyctl secrets list -a ai-coworker-for-businesses
```

---

## ⚠️ Important Notes

1. **OPENAI_API_KEY is REQUIRED** - The app will start but vector store and chat won't work without it
2. **API_KEY should be changed** - Default value is insecure
3. **SECRET_KEY should be changed** - Default value is insecure
4. **DATABASE_URL is optional** - JSON file storage works fine for most cases
5. **Cloud storage is optional** - Fly.io persistent volume is used by default

---

## 🚨 Troubleshooting

### App won't start?
- Check logs: `flyctl logs -a ai-coworker-for-businesses`
- Verify OPENAI_API_KEY is set: `flyctl secrets list -a ai-coworker-for-businesses`
- Check if storage directory is writable (should be automatic on Fly.io)

### Vector store not working?
- Verify OPENAI_API_KEY is set correctly
- Check logs for vector store initialization errors
- App will start with warnings if vector store fails (check logs)

### Documents not saving?
- Check if persistent volume is mounted (should be automatic)
- Verify storage directory exists: `/app/data/businesses`
- Check logs for storage errors

