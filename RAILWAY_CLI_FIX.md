# 🚨 CRITICAL FIX: Use Railway CLI to Set Variables

## **The Problem**

Railway Dashboard is **NOT passing environment variables** to your Docker container. This is a known Railway bug with Dockerfile-based deployments.

**Solution: Use Railway CLI instead of the dashboard.**

---

## ✅ **STEP-BY-STEP: Fix Using Railway CLI**

### **Step 1: Install Railway CLI**

**On Windows (PowerShell):**
```powershell
# Install Node.js first if you don't have it: https://nodejs.org/
npm install -g @railway/cli
```

**On Mac/Linux:**
```bash
npm install -g @railway/cli
```

**Verify installation:**
```bash
railway --version
```

---

### **Step 2: Login to Railway**

```bash
railway login
```

This will open your browser to authenticate.

---

### **Step 3: Link to Your Project**

```bash
# Navigate to your project directory
cd "C:\Henok\Co-Worker AI Assistant"

# Link to your Railway project
railway link
```

**If you have multiple projects, select the one with your backend service.**

---

### **Step 4: Set Environment Variables via CLI**

**Set OPENAI_API_KEY:**
```bash
railway variables set OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here
```

**Set other required variables:**
```bash
railway variables set API_KEY=ai-coworker-secret-key-2024
railway variables set SECRET_KEY=your-super-secret-key-change-this-in-production-2024
railway variables set CHROMA_PERSIST_DIR=/app/data/chromadb
railway variables set DATA_DIR=/app/data
railway variables set UPLOAD_DIR=/app/data/businesses
railway variables set VECTOR_DB_TYPE=chromadb
```

---

### **Step 5: Verify Variables Are Set**

```bash
railway variables
```

**You should see all your variables listed.**

---

### **Step 6: Force Redeploy**

```bash
railway up
```

**OR in Railway Dashboard:**
- Go to your service
- Click "Deployments" tab
- Click "Redeploy" → "Full Redeploy"

---

### **Step 7: Check Logs**

After redeploy, check Railway logs. You should now see:

```
✅ Found OpenAI/API related variables:
  OPENAI_API_KEY: sk-proj-... (length: 51)
```

**Instead of:**
```
❌ NO OpenAI/API related variables found in environment!
```

---

## 🔍 **Why This Works**

Railway CLI sets variables at the **platform level**, which are guaranteed to be passed to containers. The dashboard sometimes has bugs with Dockerfile-based deployments.

---

## 📋 **Complete Variable List**

Here are ALL the variables you need to set:

```bash
# REQUIRED - App won't start without these
railway variables set OPENAI_API_KEY=sk-proj-your-actual-key-here
railway variables set API_KEY=ai-coworker-secret-key-2024
railway variables set SECRET_KEY=your-super-secret-key-change-this-in-production-2024

# RECOMMENDED - For better functionality
railway variables set CHROMA_PERSIST_DIR=/app/data/chromadb
railway variables set DATA_DIR=/app/data
railway variables set UPLOAD_DIR=/app/data/businesses
railway variables set VECTOR_DB_TYPE=chromadb
railway variables set DEBUG=false
```

---

## 🚨 **If Railway CLI Doesn't Work Either**

This would indicate a **critical Railway platform bug**. In that case:

1. **Contact Railway Support:**
   - Email: support@railway.app
   - Subject: "Environment variables not passed to Docker container"
   - Include:
     - Screenshot of variables in dashboard
     - Logs showing variables are missing
     - Service name: `ai-coworker-for-businesses`

2. **Consider Alternative Platforms:**
   - **Render.com** - Similar to Railway, better Docker support
   - **Fly.io** - We already have config files
   - **DigitalOcean App Platform** - Reliable Docker deployments

---

## ✅ **After Fixing**

Once variables are set via CLI and the app starts:

1. **Test backend:**
   ```
   https://your-railway-url.up.railway.app/health
   ```
   Should return: `{"status":"healthy"}`

2. **Update frontend:**
   - Set `BACKEND_URL` in Streamlit Cloud to your Railway URL
   - Frontend should now connect successfully

---

**The enhanced diagnostic code will now show ALL environment variables Railway passes, so you can see exactly what's happening.** 🚀
