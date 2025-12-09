# 🔧 Fix Everything - Step by Step

## Issues Fixed:
✅ Dependency conflicts resolved
✅ PATH issues fixed
✅ Installation guide updated

---

## Step 1: Fix Dependencies (Backend)

**Open PowerShell in backend folder:**
```bash
cd "C:\Henok\Co-Worker AI Assistant\backend"
```

**Uninstall old packages:**
```bash
pip uninstall -y langchain langchain-community langchain-openai
```

**Install fixed requirements:**
```bash
pip install -r requirements.txt
```

**If still errors, install one by one:**
```bash
pip install fastapi uvicorn python-multipart python-dotenv
pip install langchain==0.1.5
pip install langchain-openai==0.0.5
pip install langchain-community==0.0.17
pip install openai==1.10.0
pip install chromadb
```

---

## Step 2: Fix Streamlit PATH Issue (Frontend)

**Option A: Use Python -m (Easiest)**
```bash
cd "C:\Henok\Co-Worker AI Assistant\frontend"
python -m streamlit run streamlit_app.py
```

**Option B: Add to PATH**
1. Find where streamlit is installed (from the warning):
   `C:\Users\henok\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts`

2. Add to PATH:
   - Press `Win + X` → System → Advanced system settings
   - Environment Variables → Path → Edit → New
   - Paste the Scripts path above
   - OK all dialogs

---

## Step 3: Test Backend

```bash
cd "C:\Henok\Co-Worker AI Assistant\backend"
python main.py
```

**Should see:**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**If you see errors, tell me which ones!**

---

## Step 4: Test Frontend

**In a NEW terminal:**
```bash
cd "C:\Henok\Co-Worker AI Assistant\frontend"
python -m streamlit run streamlit_app.py
```

**Should see:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

---

## Quick Fix Commands (Copy All)

**Terminal 1 - Backend:**
```bash
cd "C:\Henok\Co-Worker AI Assistant\backend"
pip uninstall -y langchain langchain-community langchain-openai
pip install -r requirements.txt
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd "C:\Henok\Co-Worker AI Assistant\frontend"
python -m streamlit run streamlit_app.py
```

---

## If Still Not Working

**Tell me:**
1. What error message you see
2. Which step failed
3. Copy the full error text

I'll fix it immediately!

