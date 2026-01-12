# 🚀 Complete Fly.io Setup Guide

## ✅ **You've Redeployed to Fly.io - Great Choice!**

Fly.io is more reliable than Railway for environment variables. Let's get everything configured.

---

## 🔧 **Step 1: Install Fly.io CLI (If Not Already Installed)**

**On Windows (PowerShell):**
```powershell
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

**Verify installation:**
```powershell
flyctl version
```

---

## 🔐 **Step 2: Set Required Environment Variables (Secrets)**

Fly.io uses **secrets** for environment variables. These are secure and always passed to containers.

### **Set OPENAI_API_KEY (REQUIRED - App won't start without this!)**

```powershell
flyctl secrets set OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here -a ai-coworker-for-businesses
```

**Replace `sk-proj-your-actual-openai-api-key-here` with your actual OpenAI API key from: https://platform.openai.com/api-keys**

### **Set API_KEY (REQUIRED - For API authentication)**

```powershell
flyctl secrets set API_KEY=ai-coworker-secret-key-2024 -a ai-coworker-for-businesses
```

### **Set SECRET_KEY (REQUIRED - For JWT tokens)**

```powershell
flyctl secrets set SECRET_KEY=your-super-secret-key-change-this-in-production-2024 -a ai-coworker-for-businesses
```

### **Set Recommended Variables**

```powershell
# Vector database storage
flyctl secrets set CHROMA_PERSIST_DIR=/app/data/chromadb -a ai-coworker-for-businesses

# Data directory (uses mounted volume)
flyctl secrets set DATA_DIR=/app/data -a ai-coworker-for-businesses

# Upload directory
flyctl secrets set UPLOAD_DIR=/app/data/businesses -a ai-coworker-for-businesses

# Vector DB type
flyctl secrets set VECTOR_DB_TYPE=chromadb -a ai-coworker-for-businesses
```

---

## ✅ **Step 3: Verify Secrets Are Set**

```powershell
flyctl secrets list -a ai-coworker-for-businesses
```

**You should see:**
- `OPENAI_API_KEY` ✅
- `API_KEY` ✅
- `SECRET_KEY` ✅
- And any others you set

---

## 🚀 **Step 4: Deploy/Redeploy**

If you haven't deployed yet, or need to redeploy with new secrets:

```powershell
flyctl deploy -a ai-coworker-for-businesses
```

**Or if already deployed, just restart:**
```powershell
flyctl apps restart -a ai-coworker-for-businesses
```

---

## 🔍 **Step 5: Check Deployment Status**

```powershell
# Check app status
flyctl status -a ai-coworker-for-businesses

# View logs (watch for startup messages)
flyctl logs -a ai-coworker-for-businesses
```

**Look for:**
- ✅ `✅ Found OpenAI/API related variables:` (in logs)
- ✅ `✅ ALL STARTUP VALIDATIONS PASSED`
- ✅ `Application started successfully`

**NOT:**
- ❌ `❌ OPENAI_API_KEY is not set`
- ❌ `⚠️ No OpenAI/API related variables found`

---

## 🌐 **Step 6: Test Your Backend**

**Get your Fly.io URL:**
```powershell
flyctl status -a ai-coworker-for-businesses
```

**Test health endpoint:**
```powershell
Invoke-WebRequest -Uri "https://ai-coworker-for-businesses.fly.dev/health" -UseBasicParsing
```

**Should return:**
```json
{"status":"healthy"}
```

**Test API docs:**
Visit: `https://ai-coworker-for-businesses.fly.dev/docs`

---

## 🔗 **Step 7: Update Frontend to Use Fly.io Backend**

**In Streamlit Cloud:**

1. Go to: https://share.streamlit.io
2. Click your app → Settings → Secrets
3. Add/Update:
   ```
   BACKEND_URL = https://ai-coworker-for-businesses.fly.dev
   API_KEY = ai-coworker-secret-key-2024
   ```
4. Save and restart

**Or update in code:**
- Edit `frontend/streamlit_app.py`
- Set `BACKEND_URL = "https://ai-coworker-for-businesses.fly.dev"`

---

## 📊 **Complete List of All Secrets**

Here's everything you might want to set:

```powershell
# REQUIRED - App won't start without these
flyctl secrets set OPENAI_API_KEY=sk-proj-your-key-here -a ai-coworker-for-businesses
flyctl secrets set API_KEY=ai-coworker-secret-key-2024 -a ai-coworker-for-businesses
flyctl secrets set SECRET_KEY=your-super-secret-key-2024 -a ai-coworker-for-businesses

# RECOMMENDED - For better functionality
flyctl secrets set CHROMA_PERSIST_DIR=/app/data/chromadb -a ai-coworker-for-businesses
flyctl secrets set DATA_DIR=/app/data -a ai-coworker-for-businesses
flyctl secrets set UPLOAD_DIR=/app/data/businesses -a ai-coworker-for-businesses
flyctl secrets set VECTOR_DB_TYPE=chromadb -a ai-coworker-for-businesses

# OPTIONAL - LLM Configuration
flyctl secrets set LLM_PROVIDER=openai -a ai-coworker-for-businesses
flyctl secrets set OPENAI_MODEL=gpt-4-turbo-preview -a ai-coworker-for-businesses

# OPTIONAL - Database (if using PostgreSQL)
flyctl secrets set DATABASE_URL=postgresql://user:pass@host:port/dbname -a ai-coworker-for-businesses
```

---

## 🛠️ **Troubleshooting**

### **If app won't start:**

1. **Check logs:**
   ```powershell
   flyctl logs -a ai-coworker-for-businesses
   ```

2. **Verify secrets:**
   ```powershell
   flyctl secrets list -a ai-coworker-for-businesses
   ```

3. **Check if secrets are being read:**
   - Look for diagnostic output in logs
   - Should show: `📊 Total environment variables Fly.io passed: [number]`
   - Should show: `✅ Found OpenAI/API related variables:`

### **If secrets aren't being read:**

1. **Restart the app:**
   ```powershell
   flyctl apps restart -a ai-coworker-for-businesses
   ```

2. **Redeploy:**
   ```powershell
   flyctl deploy -a ai-coworker-for-businesses
   ```

3. **Check secret names:**
   - Must be exact: `OPENAI_API_KEY` (not `openai_api_key`)

---

## 📋 **Quick Command Reference**

```powershell
# Set a secret
flyctl secrets set KEY=value -a ai-coworker-for-businesses

# List all secrets
flyctl secrets list -a ai-coworker-for-businesses

# Remove a secret
flyctl secrets unset KEY -a ai-coworker-for-businesses

# Deploy
flyctl deploy -a ai-coworker-for-businesses

# View logs
flyctl logs -a ai-coworker-for-businesses

# Check status
flyctl status -a ai-coworker-for-businesses

# Restart app
flyctl apps restart -a ai-coworker-for-businesses
```

---

## ✅ **Why Fly.io is Better Than Railway**

1. ✅ **Reliable secrets** - Always passed to containers
2. ✅ **Better Docker support** - No variable passing bugs
3. ✅ **Persistent volumes** - Already configured in `fly.toml`
4. ✅ **Fast deployments** - Usually 2-3 minutes
5. ✅ **Better logging** - Clear error messages

---

**After setting secrets and redeploying, your app should start successfully!** 🚀

Check the logs to confirm: `flyctl logs -a ai-coworker-for-businesses`
