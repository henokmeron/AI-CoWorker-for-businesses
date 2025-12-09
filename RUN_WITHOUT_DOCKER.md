# ✅ Run Without Docker (Easiest Method)

## Why This is Better Right Now
- ✅ No Docker login needed
- ✅ Works immediately
- ✅ Same functionality
- ✅ Easier to test

---

## Step-by-Step Instructions

### Step 1: Open First Terminal (Backend)

**Copy and paste these commands:**
```bash
cd "C:\Henok\Co-Worker AI Assistant\backend"
pip install -r requirements.txt
python main.py
```

**Wait for this message:**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**✅ Backend is running!** Keep this terminal open.

---

### Step 2: Open Second Terminal (Frontend)

**Open a NEW PowerShell window, then:**
```bash
cd "C:\Henok\Co-Worker AI Assistant\frontend"
pip install -r requirements.txt
streamlit run streamlit_app.py
```

**Wait for this message:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

**✅ Frontend is running!**

---

### Step 3: Open Your Browser

**Go to:** http://localhost:8501

**🎉 Your app is now running!**

---

## What You'll See

1. **Create a Business** - Click "Business Settings" → Create your first business
2. **Upload Documents** - Go to "Documents" → Upload PDFs, Word docs, etc.
3. **Ask Questions** - Go to "Chat" → Ask questions about your documents!

---

## To Stop the App

**In both terminals, press:** `Ctrl + C`

---

## Troubleshooting

**"pip is not recognized"**
→ Install Python from python.org (make sure to check "Add to PATH")

**"Module not found"**
→ Make sure you're in the correct folder and ran `pip install -r requirements.txt`

**"Port already in use"**
→ Close other applications using ports 8000 or 8501

---

## This Works Exactly Like Docker!

- Same functionality
- Same features
- Same API
- Just no Docker needed!

**Try it now - it's the fastest way to get started!** 🚀

