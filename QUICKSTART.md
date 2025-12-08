# Quick Start Guide

Get your AI Assistant Coworker running in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- OpenAI API key (or Anthropic/Ollama for alternatives)

## Method 1: Local Development (Fastest for Testing)

### Step 1: Install Dependencies

```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy env.example.txt to .env in the project root
cp env.example.txt .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
```

### Step 3: Start Backend

```bash
cd backend
python main.py
```

Backend will start at http://localhost:8000
- API Docs: http://localhost:8000/docs

### Step 4: Start Frontend (New Terminal)

```bash
cd frontend
streamlit run streamlit_app.py
```

Frontend will start at http://localhost:8501

### Step 5: Use the App

1. **Create a Business**: Go to "Business Settings" tab and create your first business
2. **Upload Documents**: Switch to "Documents" tab and upload your files (PDF, DOCX, etc.)
3. **Ask Questions**: Go to "Chat" tab and start asking questions!

## Method 2: Docker (Easiest for Deployment)

### Step 1: Install Docker

Make sure you have Docker and Docker Compose installed.

### Step 2: Configure Environment

```bash
# Copy env.example.txt to .env
cp env.example.txt .env

# Edit .env and add your OpenAI API key
```

### Step 3: Start Everything

```bash
docker-compose up -d
```

This starts:
- Backend at http://localhost:8000
- Frontend at http://localhost:8501
- ChromaDB at http://localhost:8001

### Step 4: Use the App

Open http://localhost:8501 in your browser!

### Stop Everything

```bash
docker-compose down
```

## Common Issues

### "OpenAI API key not configured"
- Make sure you've set `OPENAI_API_KEY` in your `.env` file

### "Module not found"
- Run `pip install -r requirements.txt` in both backend and frontend directories

### "Port already in use"
- Change `API_PORT` in `.env` to use a different port

### OCR not working
Install Tesseract:
- **macOS**: `brew install tesseract`
- **Ubuntu**: `sudo apt-get install tesseract-ocr`
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki

## Next Steps

- **Try different file types**: Upload PDFs, Word docs, spreadsheets, images
- **Add more businesses**: Each business has isolated document storage
- **Customize prompts**: Edit `backend/app/services/rag_service.py`
- **Deploy to cloud**: See README.md for deployment options

## Support

For issues or questions, check the API documentation at http://localhost:8000/docs

