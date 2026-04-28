# 🚀 START HERE - AI Assistant Coworker

Welcome! You now have a complete, production-ready AI Assistant Coworker system.

## What You've Built

A professional RAG (Retrieval Augmented Generation) system that:
- ✅ Supports **30+ file types** (PDF, DOCX, XLSX, images with OCR, and more)
- ✅ Uses **plugin architecture** for easy extensibility
- ✅ Supports **multiple businesses** with isolated data
- ✅ Works with **OpenAI, Anthropic, or local LLMs** (Ollama)
- ✅ Includes **FastAPI backend** with full REST API
- ✅ Has **Streamlit frontend** for easy use
- ✅ Ready for **Docker deployment**
- ✅ Can be **duplicated** for each business easily

## Quick Start (5 Minutes)

### Option 1: Local Development

```bash
# 1. Set up environment
cp env.example.txt .env
# Edit .env and add your OPENAI_API_KEY

# 2. Install backend
cd backend
pip install -r requirements.txt

# 3. Install frontend (new terminal)
cd frontend
pip install -r requirements.txt

# 4. Run backend
cd backend
python main.py
# API available at http://localhost:8000

# 5. Run frontend (new terminal)
cd frontend
streamlit run streamlit_app.py
# UI available at http://localhost:8501
```

### Option 2: Docker (Recommended)

```bash
# 1. Set up environment
cp env.example.txt .env
# Edit .env and add your OPENAI_API_KEY

# 2. Start everything
docker-compose up -d

# 3. Open browser
# Frontend: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

## First Steps After Starting

1. **Open Frontend**: http://localhost:8501
2. **Create Business**: Go to "Business Settings" → Create your first business
3. **Upload Documents**: Go to "Documents" → Upload PDFs, Word docs, spreadsheets, etc.
4. **Ask Questions**: Go to "Chat" → Start asking questions about your documents!

## Example Usage

### For a Care Agency:
- Upload: policies.pdf, fee_schedule.xlsx, procedures.docx
- Ask: "What is the weekend overtime rate?"
- Ask: "What are the steps for client onboarding?"

### For a Consulting Firm:
- Upload: contracts.pdf, rate_card.xlsx, proposals.docx
- Ask: "What is the hourly rate for senior consultants?"
- Ask: "What are the deliverables in the XYZ contract?"

## Key Features

### Universal File Support
Upload any of these file types:
- **Documents**: PDF, DOCX, PPTX, ODT, RTF
- **Spreadsheets**: XLSX, CSV, ODS
- **Text**: TXT, Markdown, HTML, XML, JSON
- **Images**: PNG, JPG, TIFF (with OCR)
- **Code**: Python, JavaScript, Java, etc.
- **Emails**: EML, MSG

### Multi-Business Support
Each business gets:
- Isolated document storage
- Separate vector database collection
- Independent configuration
- Secure data separation

### API Access
Full REST API at http://localhost:8000/docs with endpoints for:
- Document upload
- Chat/query
- Business management
- Document management

## Project Structure

```
AI-Assistant-Coworker/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # REST API routes
│   │   ├── core/        # Configuration & security
│   │   ├── models/      # Data models
│   │   ├── services/    # Business logic
│   │   │   └── file_handlers/  # Plugin system
│   │   └── utils/       # Helper functions
│   └── main.py          # Application entry
│
├── frontend/            # Streamlit UI
│   └── streamlit_app.py
│
├── data/                # Document & database storage
│   └── businesses/      # Per-business files
│
└── Documentation:
    ├── QUICKSTART.md    # Quick start guide
    ├── ARCHITECTURE.md  # System architecture
    ├── DEPLOYMENT.md    # Deployment guide
    ├── EXAMPLES.md      # Usage examples
    └── README.md        # Full documentation
```

## How to Duplicate for New Business

### Method 1: Full Copy (Simplest)
```bash
# Copy entire project
cp -r Co-Worker-AI-Assistant Business-Name-Assistant

# Configure for new business
cd Business-Name-Assistant
cp env.example.txt .env
# Edit .env with business-specific settings

# Run as independent instance
docker-compose up -d
```

### Method 2: Single Instance (Scalable)
- Use the existing deployment
- Create new business via UI or API
- All data automatically isolated by business_id

## Configuration Options

### LLM Providers

**OpenAI (Default):**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini
```

**Anthropic (Claude):**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
```

**Ollama (Local, Free):**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Vector Database

**ChromaDB (Default - Local):**
```env
VECTOR_DB_TYPE=chromadb
CHROMA_PERSIST_DIR=./data/chromadb
```

**Qdrant (Production - Cloud):**
```env
VECTOR_DB_TYPE=qdrant
QDRANT_URL=https://your-instance.qdrant.io
QDRANT_API_KEY=your-key
```

## Adding Custom File Handlers

Create a new handler in `backend/app/services/file_handlers/custom_handlers/`:

```python
from ..base_handler import BaseFileHandler

class MyCustomHandler(BaseFileHandler):
    def can_handle(self, file_path: str, file_type: str) -> bool:
        return file_type == 'custom'
    
    def process(self, file_path: str) -> Dict[str, Any]:
        # Your processing logic
        return {"text": content, "metadata": {}}
    
    def get_supported_types(self) -> List[str]:
        return ['custom']
```

## Deployment Options

1. **Local**: Run on your computer (development)
2. **Docker**: Containerized deployment (production-ready)
3. **Railway/Render**: One-click cloud deployment (easiest)
4. **VPS**: Full control on AWS/DigitalOcean/etc.

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)**: Quick setup guide
- **[README.md](README.md)**: Complete documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System architecture details
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Deployment options & guides
- **[EXAMPLES.md](EXAMPLES.md)**: Usage examples & code samples

## API Documentation

Interactive API docs with try-it-out features:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Common Questions

### How do I add more documents?
Go to Documents tab → Upload files → The AI will automatically process and index them.

### Can I use this without an API key?
Yes! Use Ollama for local LLMs (no API key needed):
```bash
# Install Ollama
# Download a model: ollama pull llama2
# Set in .env: LLM_PROVIDER=ollama
```

### How much does it cost?
- **Development**: Free (use Ollama for local LLM)
- **Production with OpenAI**: ~$10-50/month depending on usage
- **Hosting**: $5-20/month (Docker on VPS or Railway)

### Is my data secure?
Yes! All data is stored locally or in your cloud account. No data is sent to third parties except LLM providers (OpenAI/Anthropic) for generating responses.

### Can I customize the AI's responses?
Yes! Edit the system prompt in `backend/app/services/rag_service.py`

## Troubleshooting

### Backend won't start
- Check .env file has OPENAI_API_KEY
- Ensure port 8000 is available
- Run: `pip install -r backend/requirements.txt`

### Frontend won't start
- Ensure backend is running first
- Check port 8501 is available
- Run: `pip install -r frontend/requirements.txt`

### OCR not working
Install Tesseract:
- **macOS**: `brew install tesseract`
- **Ubuntu**: `sudo apt-get install tesseract-ocr`
- **Windows**: Download from GitHub

### "No documents found" when asking questions
- Make sure you've uploaded documents
- Check they finished processing (status: "completed")
- Verify you're in the correct business

## Next Steps

1. ✅ **Test with sample documents**: Upload a few PDFs or Word docs
2. ✅ **Try different questions**: See how the AI responds
3. ✅ **Customize for your business**: Upload your actual documents
4. ✅ **Share with team**: Deploy to cloud for team access
5. ✅ **Extend functionality**: Add custom file handlers or features

## Support & Contribution

- Check API docs: http://localhost:8000/docs
- Review examples: [EXAMPLES.md](EXAMPLES.md)
- Read architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

## License

MIT License - Free for commercial use. See [LICENSE](LICENSE) file.

---

**You're all set! Start by opening http://localhost:8501 and creating your first business.** 🎉


