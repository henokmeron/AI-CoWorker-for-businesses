# 🚂 Railway Deployment Guide

## ✅ Fixed Issues

1. **Syntax Error Fixed:** Fixed indentation error in `backend/app/services/rag_service.py` line 576
2. **Storage:** Railway supports persistent volumes (similar to Fly.io)

---

## 📦 Railway Storage

**Yes, Railway has persistent storage!** It's called **Railway Volumes**.

### How Railway Storage Works:
- ✅ **Persistent volumes** - Data survives deployments
- ✅ **Automatic backups** - Railway backs up volumes
- ✅ **Easy to set up** - Just add a volume in Railway dashboard
- ✅ **Similar to Fly.io** - Mounts to `/app/data` or custom path

### Setting Up Storage in Railway:

1. **In Railway Dashboard:**
   - Go to your service
   - Click "Settings" → "Volumes"
   - Click "Add Volume"
   - **Mount Path:** `/app/data`
   - **Size:** 10GB (or more if needed)
   - Click "Create"

2. **That's it!** Railway will automatically mount the volume to `/app/data`

---

## 🔐 Environment Variables for Railway

### **REQUIRED Variables** (You must set these):

#### 1. **OPENAI_API_KEY** (You provide the value)
```
Name: OPENAI_API_KEY
Value: sk-your-actual-openai-api-key-here
```
**Note:** This is your OpenAI API key. Get it from: https://platform.openai.com/api-keys

---

#### 2. **API_KEY** (You provide the value)
```
Name: API_KEY
Value: ai-coworker-secret-key-2024
```
**Note:** This is the secret key for API authentication. Use any secure random string.

---

#### 3. **SECRET_KEY** (You provide the value)
```
Name: SECRET_KEY
Value: your-super-secret-key-change-this-in-production-2024
```
**Note:** This is for JWT token signing. Use a long random string (at least 32 characters).

---

### **OPTIONAL Variables** (Set these for better performance):

#### 4. **CHROMA_PERSIST_DIR** (For persistent vector database)
```
Name: CHROMA_PERSIST_DIR
Value: /app/data/chromadb
```
**Note:** This stores your vector database in the Railway volume (persists across deployments).

---

#### 5. **DATA_DIR** (For document storage)
```
Name: DATA_DIR
Value: /app/data
```
**Note:** This is where uploaded documents are stored (in the Railway volume).

---

#### 6. **UPLOAD_DIR** (For uploaded files)
```
Name: UPLOAD_DIR
Value: /app/data/businesses
```
**Note:** This is where business-specific documents are stored.

---

#### 7. **VECTOR_DB_TYPE** (Database type)
```
Name: VECTOR_DB_TYPE
Value: chromadb
```
**Note:** Use `chromadb` for Railway (works great with persistent volumes).

---

#### 8. **DEBUG** (For logging)
```
Name: DEBUG
Value: false
```
**Note:** Set to `false` in production, `true` for debugging.

---

#### 9. **ALLOWED_ORIGINS** (CORS settings)
```
Name: ALLOWED_ORIGINS
Value: https://your-frontend-url.streamlit.app,https://your-frontend-url.railway.app
```
**Note:** Add your frontend URL(s) here. Separate multiple URLs with commas.

---

## 🚀 Step-by-Step Railway Deployment

### Step 1: Fix the Code (Already Done ✅)
- Fixed syntax error in `rag_service.py`
- Code is ready to deploy

### Step 2: Push to GitHub
```bash
git add .
git commit -m "FIX: Syntax error in rag_service.py for Railway deployment"
git push origin main
```

### Step 3: Deploy on Railway

1. **Go to Railway:** https://railway.app
2. **Sign in** with GitHub
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Choose your repo:** `AI-CoWorker-for-businesses`
6. **Railway auto-detects Docker** ✅

### Step 4: Configure Service

1. **Click on the service** that Railway created
2. **Go to "Settings" tab**
3. **Set Root Directory:** `backend` (if not auto-detected)
4. **Set Dockerfile Path:** `backend/Dockerfile` (if not auto-detected)

### Step 5: Add Persistent Volume

1. **In service settings, click "Volumes"**
2. **Click "Add Volume"**
3. **Mount Path:** `/app/data`
4. **Size:** 10GB (or more)
5. **Click "Create"**

### Step 6: Add Environment Variables

1. **Click "Variables" tab**
2. **Add each variable** from the list above:

**Click "New Variable" for each:**

```
OPENAI_API_KEY = sk-your-actual-key-here
API_KEY = ai-coworker-secret-key-2024
SECRET_KEY = your-super-secret-key-change-this-in-production-2024
CHROMA_PERSIST_DIR = /app/data/chromadb
DATA_DIR = /app/data
UPLOAD_DIR = /app/data/businesses
VECTOR_DB_TYPE = chromadb
DEBUG = false
ALLOWED_ORIGINS = https://your-frontend-url.streamlit.app
```

**Note:** Replace `your-frontend-url` with your actual Streamlit Cloud URL.

### Step 7: Deploy

1. **Railway will automatically deploy** when you push to GitHub
2. **Or click "Deploy"** in Railway dashboard
3. **Wait 3-5 minutes** for build to complete

### Step 8: Get Your Backend URL

1. **After deployment, Railway gives you a URL** like:
   ```
   https://your-app-name.up.railway.app
   ```
2. **Copy this URL** - you'll need it for the frontend

---

## 🔍 Verify Deployment

### Test Backend Health:
```bash
curl https://your-app-name.up.railway.app/health
```

Should return:
```json
{"status": "healthy"}
```

### Test API Docs:
Visit: `https://your-app-name.up.railway.app/docs`

---

## 📝 Complete Environment Variables List

Here's the **complete list** of all environment variables you need to set in Railway:

### **Required (You Must Provide Values):**

| Variable Name | Value (You Provide) | Description |
|--------------|---------------------|-------------|
| `OPENAI_API_KEY` | `sk-...` | Your OpenAI API key |
| `API_KEY` | `ai-coworker-secret-key-2024` | API authentication key |
| `SECRET_KEY` | `your-long-random-string` | JWT signing key (32+ chars) |

### **Recommended (Set These Too):**

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `CHROMA_PERSIST_DIR` | `/app/data/chromadb` | Vector DB storage path |
| `DATA_DIR` | `/app/data` | General data storage |
| `UPLOAD_DIR` | `/app/data/businesses` | Document upload path |
| `VECTOR_DB_TYPE` | `chromadb` | Vector database type |
| `DEBUG` | `false` | Debug mode (false for production) |
| `ALLOWED_ORIGINS` | `https://your-frontend-url` | CORS allowed origins |

### **Optional (Only if needed):**

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `OPENAI_MODEL` | `gpt-4-turbo-preview` | OpenAI model to use |
| `LLM_PROVIDER` | `openai` | LLM provider (openai/anthropic/ollama) |
| `MAX_FILE_SIZE_MB` | `50` | Max file upload size |
| `CHUNK_SIZE` | `1000` | Document chunk size |
| `CHUNK_OVERLAP` | `200` | Chunk overlap |

---

## 🎯 Quick Setup Checklist

- [ ] Code fixed (syntax error resolved) ✅
- [ ] Code pushed to GitHub
- [ ] Railway project created
- [ ] Service configured (root directory: `backend`)
- [ ] Persistent volume added (`/app/data`, 10GB)
- [ ] Environment variables added:
  - [ ] `OPENAI_API_KEY` (your value)
  - [ ] `API_KEY` (your value)
  - [ ] `SECRET_KEY` (your value)
  - [ ] `CHROMA_PERSIST_DIR` = `/app/data/chromadb`
  - [ ] `DATA_DIR` = `/app/data`
  - [ ] `UPLOAD_DIR` = `/app/data/businesses`
  - [ ] `VECTOR_DB_TYPE` = `chromadb`
  - [ ] `DEBUG` = `false`
  - [ ] `ALLOWED_ORIGINS` = your frontend URL
- [ ] Deployment successful
- [ ] Health check passes (`/health` endpoint)
- [ ] Backend URL copied for frontend

---

## 🆘 Troubleshooting

### **Error: "SyntaxError: invalid syntax"**
- ✅ **Fixed!** The syntax error in `rag_service.py` has been corrected
- Make sure you've pulled the latest code from GitHub

### **Error: "No such file or directory: /app/data"**
- **Solution:** Add a Railway Volume with mount path `/app/data`
- Go to Settings → Volumes → Add Volume

### **Error: "OPENAI_API_KEY not found"**
- **Solution:** Add `OPENAI_API_KEY` environment variable in Railway
- Go to Variables tab → New Variable

### **Error: "Collection not found"**
- **Solution:** This is normal on first deployment
- Upload documents through the frontend to create collections

### **Backend not responding**
- Check Railway logs: Service → Deployments → View Logs
- Verify all environment variables are set
- Check that the volume is mounted correctly

---

## 📊 Railway vs Fly.io Storage

| Feature | Fly.io | Railway |
|---------|--------|---------|
| **Persistent Storage** | ✅ Yes (Volumes) | ✅ Yes (Volumes) |
| **Auto-backup** | ✅ Yes | ✅ Yes |
| **Easy Setup** | ⚠️ Manual | ✅ Dashboard |
| **Cost** | Free tier | $5-20/month |
| **Auto-stop** | ⚠️ Yes (can stop) | ❌ No (stays running) |

**Railway is better** because:
- ✅ Never auto-stops (unlike Fly.io)
- ✅ Easier volume setup (dashboard vs config file)
- ✅ Better for production

---

## 🎉 Next Steps

1. **Deploy backend to Railway** (follow steps above)
2. **Deploy frontend to Streamlit Cloud:**
   - Go to https://streamlit.io/cloud
   - Connect GitHub repo
   - Set `BACKEND_URL` = your Railway backend URL
   - Deploy!

3. **Test your app!** 🚀

---

## 📞 Need Help?

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **Check logs:** Railway Dashboard → Service → Deployments → View Logs

---

**You're all set!** The syntax error is fixed, and Railway has persistent storage just like Fly.io (but better because it never stops). 🎉
