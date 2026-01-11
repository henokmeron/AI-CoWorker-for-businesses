# 🔧 COMPLETE Railway Environment Variables Setup

## 🚨 **CRITICAL: Your Backend is Failing Because OPENAI_API_KEY is Missing**

The logs show:
```
❌ OPENAI_API_KEY is not set. This is REQUIRED for embeddings and LLM.
```

**This is a Railway configuration issue, not a code issue.** You must set environment variables in Railway.

---

## ✅ **STEP-BY-STEP: Set All Required Environment Variables in Railway**

### **Step 1: Go to Railway Dashboard**

1. **Open:** https://railway.app
2. **Sign in**
3. **Click on your backend service**

### **Step 2: Open Variables Tab**

1. **Click "Variables" tab** (in the service settings)
2. **You'll see a list of environment variables**

### **Step 3: Add REQUIRED Variables (MUST HAVE)**

**Click "New Variable" for each of these:**

#### **1. OPENAI_API_KEY (REQUIRED - Backend won't start without this!)**

```
Name: OPENAI_API_KEY
Value: sk-your-actual-openai-api-key-here
```

**How to get your OpenAI API key:**
1. Go to: https://platform.openai.com/api-keys
2. Sign in to your OpenAI account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Paste it as the value in Railway

**⚠️ CRITICAL:** Without this, your backend will NOT start!

---

#### **2. API_KEY (REQUIRED - For API authentication)**

```
Name: API_KEY
Value: ai-coworker-secret-key-2024
```

**Or generate a secure one:**
```bash
openssl rand -hex 32
```

---

#### **3. SECRET_KEY (REQUIRED - For JWT tokens)**

```
Name: SECRET_KEY
Value: your-super-secret-key-change-this-in-production-2024
```

**Or generate a secure one:**
```bash
openssl rand -hex 32
```

---

### **Step 4: Add RECOMMENDED Variables (Set These Too)**

#### **4. CHROMA_PERSIST_DIR**

```
Name: CHROMA_PERSIST_DIR
Value: /app/data/chromadb
```

---

#### **5. DATA_DIR**

```
Name: DATA_DIR
Value: /app/data
```

---

#### **6. UPLOAD_DIR**

```
Name: UPLOAD_DIR
Value: /app/data/businesses
```

---

#### **7. VECTOR_DB_TYPE**

```
Name: VECTOR_DB_TYPE
Value: chromadb
```

---

#### **8. DEBUG**

```
Name: DEBUG
Value: false
```

---

#### **9. ALLOWED_ORIGINS**

```
Name: ALLOWED_ORIGINS
Value: https://your-streamlit-app.streamlit.app
```

**Replace `your-streamlit-app` with your actual Streamlit Cloud app name.**

**If you have multiple frontends, separate with commas:**
```
https://app1.streamlit.app,https://app2.streamlit.app
```

---

### **Step 5: Verify All Variables Are Set**

**Your Railway Variables tab should show:**

| Variable Name | Value |
|--------------|-------|
| `OPENAI_API_KEY` | `sk-...` (your actual key) |
| `API_KEY` | `ai-coworker-secret-key-2024` |
| `SECRET_KEY` | `your-secret-key` |
| `CHROMA_PERSIST_DIR` | `/app/data/chromadb` |
| `DATA_DIR` | `/app/data` |
| `UPLOAD_DIR` | `/app/data/businesses` |
| `VECTOR_DB_TYPE` | `chromadb` |
| `DEBUG` | `false` |
| `ALLOWED_ORIGINS` | `https://your-app.streamlit.app` |

---

### **Step 6: Make Sure PORT is NOT Set**

**⚠️ IMPORTANT:** Railway automatically sets `PORT`. 

**DO NOT create a `PORT` variable in Railway!**

If you see a `PORT` variable:
1. **Delete it** (Railway sets it automatically)
2. **Or set it to a number** (but best: delete it)

---

### **Step 7: Redeploy**

1. **After setting all variables, Railway will auto-redeploy**
2. **Or click "Redeploy"** manually
3. **Wait 3-5 minutes** for deployment

---

## 🔍 **Verify Deployment**

### **Check Railway Logs:**

1. **Go to Railway Dashboard → Your Service**
2. **Click "Deployments" tab**
3. **Click latest deployment**
4. **Check "Logs"**

**You should see:**
- ✅ "Starting uvicorn on port [number]"
- ✅ "✅ ALL STARTUP VALIDATIONS PASSED"
- ✅ "Application started successfully"

**You should NOT see:**
- ❌ "OPENAI_API_KEY is not set"
- ❌ "CRITICAL STARTUP FAILURES"
- ❌ "Application startup failed"

---

### **Test Backend Health:**

1. **Get your Railway backend URL** (from Railway Dashboard → Settings → Networking)
2. **Test:** `https://your-railway-url.up.railway.app/health`
3. **Should return:** `{"status":"healthy"}`

---

## 📋 **Complete Checklist**

- [ ] `OPENAI_API_KEY` set (your actual OpenAI key starting with `sk-`)
- [ ] `API_KEY` set
- [ ] `SECRET_KEY` set
- [ ] `CHROMA_PERSIST_DIR` = `/app/data/chromadb`
- [ ] `DATA_DIR` = `/app/data`
- [ ] `UPLOAD_DIR` = `/app/data/businesses`
- [ ] `VECTOR_DB_TYPE` = `chromadb`
- [ ] `DEBUG` = `false`
- [ ] `ALLOWED_ORIGINS` = your frontend URL
- [ ] `PORT` variable does NOT exist (or is deleted)
- [ ] Railway volume mounted at `/app/data`
- [ ] Redeployed after setting variables
- [ ] Backend health check passes: `/health` returns `{"status":"healthy"}`

---

## 🚨 **Common Mistakes**

### **❌ Mistake 1: OPENAI_API_KEY Not Set**
**Error:** `OPENAI_API_KEY is not set. This is REQUIRED`
**Fix:** Set `OPENAI_API_KEY` in Railway Variables

### **❌ Mistake 2: PORT Set to "$PORT"**
**Error:** `PORT env var must be an integer. Got: '$PORT'`
**Fix:** Delete `PORT` variable from Railway (Railway sets it automatically)

### **❌ Mistake 3: Wrong Variable Names**
**Error:** Variables not being read
**Fix:** Make sure variable names are EXACT (case-sensitive):
- `OPENAI_API_KEY` (not `openai_api_key`)
- `API_KEY` (not `api_key`)

### **❌ Mistake 4: Variables Set But Not Saved**
**Error:** Changes not taking effect
**Fix:** Make sure to click "Save" after adding each variable

---

## 🎯 **Quick Reference: All Variables**

**Copy-paste this list to Railway Variables:**

```
OPENAI_API_KEY=sk-your-actual-key-here
API_KEY=ai-coworker-secret-key-2024
SECRET_KEY=your-super-secret-key-change-this-in-production-2024
CHROMA_PERSIST_DIR=/app/data/chromadb
DATA_DIR=/app/data
UPLOAD_DIR=/app/data/businesses
VECTOR_DB_TYPE=chromadb
DEBUG=false
ALLOWED_ORIGINS=https://your-streamlit-app.streamlit.app
```

**⚠️ Replace:**
- `sk-your-actual-key-here` with your real OpenAI API key
- `your-streamlit-app` with your actual Streamlit Cloud app name

---

## 🎉 **After Setting All Variables**

Once all variables are set correctly:
- ✅ Backend starts successfully
- ✅ Health endpoint works: `/health`
- ✅ API docs work: `/docs`
- ✅ Frontend can connect
- ✅ All features work

---

**The backend code is correct. You just need to set the environment variables in Railway!** 🚀
