# 🚨 QUICK FIX: Railway Backend Not Starting

## **The Problem**

Your Railway backend is crashing with:
```
❌ OPENAI_API_KEY is not set. This is REQUIRED for embeddings and LLM.
```

## **The Solution (2 Minutes)**

### **Step 1: Get Your OpenAI API Key**

1. Go to: https://platform.openai.com/api-keys
2. Sign in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### **Step 2: Set It in Railway**

1. Go to: https://railway.app
2. Click your backend service
3. Click "Variables" tab
4. Click "New Variable"
5. Set:
   - **Name:** `OPENAI_API_KEY`
   - **Value:** `sk-your-actual-key-here` (paste your key)
6. Click "Save"

### **Step 3: Wait for Redeploy**

Railway will auto-redeploy (takes 2-3 minutes).

### **Step 4: Verify**

1. Check Railway logs - should see "✅ ALL STARTUP VALIDATIONS PASSED"
2. Test: `https://your-railway-url.up.railway.app/health`
3. Should return: `{"status":"healthy"}`

---

## **That's It!**

Once `OPENAI_API_KEY` is set, your backend will start successfully.

**For complete setup, see:** `RAILWAY_ENV_VARS_COMPLETE.md`
