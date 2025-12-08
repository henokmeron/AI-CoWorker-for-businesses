# AI Assistant Coworker Prototype

A professional, scalable AI Assistant that learns from your business documents and acts as a 24/7 intelligent coworker. Upload your policies, procedures, fee structures, contracts, and any business documents - the AI will answer questions accurately with source citations.

## Features

- **Universal File Support**: 30+ file types including PDF, DOCX, PPTX, XLSX, CSV, images (with OCR), emails, code files, and more
- **Plugin Architecture**: Easily extensible for custom file formats
- **Multi-Tenant**: Support multiple businesses with isolated data
- **RAG (Retrieval Augmented Generation)**: Accurate answers backed by your documents
- **Source Citations**: Every answer includes references to source documents
- **Modern Tech Stack**: FastAPI backend, Streamlit frontend, LangChain for AI
- **Multiple Deployment Options**: Local, Docker, or Cloud

## Quick Start

### Option 1: Local Development

1. **Clone and Setup**
```bash
cd co-worker-ai-assistant
cp .env.example .env
# Edit .env with your API keys
```

2. **Install Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Install Frontend**
```bash
cd ../frontend
pip install -r requirements.txt
```

4. **Run Backend**
```bash
cd ../backend
uvicorn main:app --reload
# API available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

5. **Run Frontend** (in new terminal)
```bash
cd frontend
streamlit run streamlit_app.py
# UI available at http://localhost:8501
```

### Option 2: Docker (Recommended)

1. **Setup**
```bash
cp .env.example .env
# Edit .env with your API keys
```

2. **Run**
```bash
docker-compose up -d
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

3. **Stop**
```bash
docker-compose down
```

## Configuration

Edit `.env` file with your settings:

### Required Settings
- `OPENAI_API_KEY`: Your OpenAI API key (or configure another LLM provider)

### Optional Settings
- `ANTHROPIC_API_KEY`: Use Claude instead of GPT
- `OLLAMA_BASE_URL`: Use local LLMs via Ollama (no API key needed)
- `MAX_FILE_SIZE_MB`: Maximum upload file size (default: 50MB)
- `CHUNK_SIZE`: Text chunk size for processing (default: 1000)

## Usage

1. **Create a Business**
   - Open the frontend UI
   - Create a new business profile

2. **Upload Documents**
   - Drag and drop files (PDF, DOCX, XLSX, etc.)
   - AI processes and indexes them automatically

3. **Ask Questions**
   - Type questions about your documents
   - Get instant answers with source citations

## Supported File Types

- **Documents**: PDF, DOCX, PPTX, ODT, RTF
- **Spreadsheets**: XLSX, CSV, ODS
- **Text**: TXT, Markdown, HTML, XML, JSON
- **Images**: PNG, JPG, TIFF (with OCR)
- **Emails**: EML, MSG
- **Code**: Python, JavaScript, Java, etc.
- **Archives**: ZIP (auto-extracts contents)

## Architecture

```
Backend (FastAPI)
├── Document Processing (Unstructured.io)
├── Vector Database (ChromaDB)
├── RAG Service (LangChain)
└── REST API

Frontend (Streamlit)
└── Chat Interface + Document Upload
```

## Duplication for New Business

### Method 1: Copy Entire Project
```bash
cp -r co-worker-ai-assistant business-name-assistant
cd business-name-assistant
# Edit .env with business-specific settings
# Run as normal
```

### Method 2: Multi-Tenant (Single Instance)
- Keep one deployment
- Create new business via UI
- All data automatically isolated

## API Documentation

Interactive API docs available at `http://localhost:8000/docs`

### Key Endpoints
- `POST /api/v1/documents/upload` - Upload documents
- `POST /api/v1/chat` - Chat with AI
- `GET /api/v1/businesses` - List businesses
- `POST /api/v1/businesses` - Create business

## Extending the System

### Add Custom File Handler
```python
# backend/app/services/file_handlers/custom_handlers/my_handler.py
from ..base_handler import BaseFileHandler

class MyCustomHandler(BaseFileHandler):
    def can_handle(self, file_path: str) -> bool:
        return file_path.endswith('.custom')
    
    def process(self, file_path: str) -> str:
        # Your processing logic
        return processed_text
```

### Add New LLM Provider
Edit `backend/app/core/config.py` and add provider configuration.

## Cloud Deployment

### Railway / Render / Fly.io
1. Connect your GitHub repo
2. Add environment variables from `.env`
3. Deploy automatically

### AWS / GCP / Azure
Use Docker image:
```bash
docker build -t ai-assistant-backend ./backend
docker build -t ai-assistant-frontend ./frontend
# Push to container registry
# Deploy to your cloud provider
```

## Security

- API key authentication enabled by default
- File validation and size limits
- Input sanitization
- Environment-based secrets
- CORS protection

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### OCR not working
Install Tesseract:
- **Mac**: `brew install tesseract`
- **Ubuntu**: `sudo apt-get install tesseract-ocr`
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki

### ChromaDB issues
Delete and reinitialize:
```bash
rm -rf data/chromadb
# Restart application
```

## License

MIT License - Free for commercial use

## Support

For issues or questions, check the API documentation at `/docs` or review the code comments.

