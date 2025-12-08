# Architecture Documentation

## Overview

The AI Assistant Coworker is a production-ready RAG (Retrieval Augmented Generation) system built with modern Python technologies. It allows businesses to upload documents and query them using natural language.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Streamlit)                      │
│  - Document Upload UI                                        │
│  - Chat Interface                                            │
│  - Business Management                                       │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP/REST API
                 │
┌────────────────▼────────────────────────────────────────────┐
│              Backend (FastAPI)                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Layer                                            │  │
│  │  - /api/v1/chat (Query endpoint)                      │  │
│  │  - /api/v1/documents (Upload/manage)                  │  │
│  │  - /api/v1/businesses (Tenant management)             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Service Layer                                        │  │
│  │  - RAG Service (Question answering)                   │  │
│  │  - Document Processor (File handling)                 │  │
│  │  - Embedding Service (Vector generation)              │  │
│  │  - Vector Store (Search & retrieval)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  File Handler System (Plugin Architecture)            │  │
│  │  - Base Handler (Interface)                           │  │
│  │  - Unstructured Handler (30+ file types)              │  │
│  │  - Custom Handlers (Extensible)                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────┬──────────────────────┘
                  │                   │
         ┌────────▼────────┐ ┌───────▼────────┐
         │   Vector DB     │ │   LLM Provider │
         │   (ChromaDB/    │ │   (OpenAI/     │
         │    Qdrant)      │ │    Anthropic/  │
         │                 │ │    Ollama)     │
         └─────────────────┘ └────────────────┘
```

## Key Components

### 1. Document Processing Pipeline

**Flow:**
1. User uploads file → FastAPI endpoint
2. File saved to business directory
3. File handler system processes file:
   - Detects file type
   - Routes to appropriate handler (Unstructured.io)
   - Extracts text, tables, images (OCR)
   - Chunks content into semantic blocks
4. Chunks embedded and stored in vector database
5. Metadata saved to JSON storage

**Supported File Types:**
- Documents: PDF, DOCX, PPTX, ODT, RTF
- Spreadsheets: XLSX, CSV, ODS
- Text: TXT, Markdown, HTML, XML, JSON
- Images: PNG, JPG, TIFF (with OCR)
- Code: Python, JS, Java, etc.
- Emails: EML, MSG

### 2. RAG (Retrieval Augmented Generation)

**Query Flow:**
1. User submits question → Chat endpoint
2. Question embedded into vector
3. Semantic search in vector DB:
   - Find top-k most similar document chunks
   - Filter by business ID (multi-tenant isolation)
4. Relevant chunks + question → LLM
5. LLM generates answer with citations
6. Response returned with source documents

**Features:**
- Semantic search using embeddings
- Context-aware responses
- Source citation tracking
- Conversation history support
- Streaming responses (optional)

### 3. Multi-Tenant Architecture

**Business Isolation:**
- Each business has unique ID
- Separate vector collections per business
- Isolated document storage directories
- Business-specific configurations

**Duplication Strategies:**

**Method 1: Full Copy**
```bash
cp -r project/ business-name-assistant/
cd business-name-assistant/
# Edit .env with business settings
# Run as independent instance
```

**Method 2: Single Instance**
- One deployment serves all businesses
- Tenant ID in API requests
- Data isolated by business_id
- More scalable, requires authentication

### 4. Plugin Architecture

**File Handler System:**
```python
# Custom handler example
class MyHandler(BaseFileHandler):
    def can_handle(self, file_path: str, file_type: str) -> bool:
        return file_type == 'custom'
    
    def process(self, file_path: str) -> Dict[str, Any]:
        # Your logic here
        return {"text": content, "metadata": {}}
    
    def get_supported_types(self) -> List[str]:
        return ['custom']

# Register handler
processor = get_document_processor()
processor.register_handler(MyHandler())
```

### 5. Vector Database

**ChromaDB (Default - Local):**
- Embedded database (no setup needed)
- Perfect for prototypes and small deployments
- Persistent storage to disk
- Good for <1M documents

**Qdrant (Production - Cloud):**
- Scalable cloud-ready vector DB
- Better performance for large datasets
- Supports distributed deployment
- Good for 1M+ documents

**Switching:**
```env
# In .env file
VECTOR_DB_TYPE=qdrant  # or chromadb
QDRANT_URL=http://your-qdrant-server:6333
QDRANT_API_KEY=your-key
```

### 6. LLM Provider Support

**OpenAI (Default):**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4-turbo-preview
```

**Anthropic (Claude):**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

**Ollama (Local, No API Key):**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

## Data Flow Examples

### Document Upload Flow

```
User → Frontend → POST /api/v1/documents/upload
                        ↓
                  Save to disk
                        ↓
                  Document Processor
                        ↓
                  File Handler (Unstructured)
                        ↓
                  Extract text + chunks
                        ↓
                  Embedding Service
                        ↓
                  Vector Store (ChromaDB)
                        ↓
                  Save metadata
                        ↓
                  Return success
```

### Query Flow

```
User → Frontend → POST /api/v1/chat
                        ↓
                  RAG Service
                        ↓
                  Vector Store (search)
                        ↓
                  Retrieve relevant chunks
                        ↓
                  Build prompt with context
                        ↓
                  LLM (OpenAI/Anthropic/Ollama)
                        ↓
                  Generate answer
                        ↓
                  Format with sources
                        ↓
                  Return to user
```

## Storage

### File System Structure

```
data/
├── businesses/
│   ├── business_1/
│   │   ├── uuid1.pdf
│   │   ├── uuid2.docx
│   │   └── uuid3.xlsx
│   └── business_2/
│       └── uuid4.pdf
├── chromadb/
│   └── [ChromaDB files]
├── businesses.json
└── documents.json
```

### Metadata Storage

Simple JSON files for prototype (easily upgradeable to PostgreSQL/MongoDB):
- `businesses.json`: Business metadata
- `documents.json`: Document metadata

## Security

1. **API Key Authentication**: Required for all endpoints
2. **File Validation**: Type and size checks
3. **Input Sanitization**: Query validation
4. **CORS Protection**: Configurable origins
5. **Environment Secrets**: All sensitive data in .env

## Scalability Considerations

### Current Setup (Good for 1-100 businesses)
- JSON metadata storage
- ChromaDB embedded
- Single server deployment

### Scaling Up (100-1000+ businesses)
- PostgreSQL for metadata
- Qdrant/Pinecone for vectors
- Redis for caching
- Load balancer + multiple servers
- S3/Cloud storage for files

### Optimization Points
- Add caching layer (Redis)
- Implement batch processing
- Add CDN for file downloads
- Implement rate limiting
- Add monitoring (Prometheus/Grafana)

## Extension Points

1. **New File Types**: Add custom handlers in `file_handlers/custom_handlers/`
2. **New LLM Providers**: Extend `rag_service.py`
3. **Advanced Retrieval**: Add hybrid search, re-ranking
4. **Analytics**: Track queries, response quality
5. **Voice Interface**: Add speech-to-text/text-to-speech
6. **Real-time Collaboration**: WebSocket support

## Deployment Options

### 1. Local Development
```bash
python backend/main.py
streamlit run frontend/streamlit_app.py
```

### 2. Docker
```bash
docker-compose up -d
```

### 3. Cloud (Railway/Render/Fly.io)
- Push to GitHub
- Connect repository
- Set environment variables
- Auto-deploy

### 4. VPS (AWS/GCP/Azure)
- Use Docker deployment
- Configure nginx reverse proxy
- Set up SSL (Let's Encrypt)
- Configure firewall

## Performance

**Typical Response Times:**
- Document upload: 2-10 seconds (depends on file size)
- Query response: 1-3 seconds
- Embedding generation: 0.5-1 second
- Vector search: 0.1-0.5 seconds

**Optimization Tips:**
- Use smaller embedding models for speed
- Reduce chunk size for faster search
- Enable caching for common queries
- Use streaming for better UX

