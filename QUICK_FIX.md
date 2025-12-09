# ⚡ Quick Fix: Wrong Directory

## Problem
You're in `C:\Users\henok>` but need to be in the project folder.

## Solution

**Run this command:**
```bash
cd "C:\Henok\Co-Worker AI Assistant"
```

**Then deploy:**
```bash
docker-compose up -d
```

---

## Or Run Without Docker (Easier!)

**Terminal 1 - Backend:**
```bash
cd "C:\Henok\Co-Worker AI Assistant\backend"
pip install -r requirements.txt
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd "C:\Henok\Co-Worker AI Assistant\frontend"
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open: **http://localhost:8501**

