# 🔧 FIX: Railway PORT Environment Variable

## 🚨 **The Problem**

Your backend is crashing because Railway is passing `PORT` as the literal string `"$PORT"` instead of a number. This happens when someone manually sets a `PORT` environment variable in Railway to `"$PORT"`.

**Railway automatically injects `PORT` as an integer** - you must NOT override it!

---

## ✅ **The Fix**

### **Step 1: Remove PORT from Railway Variables**

1. **Go to Railway Dashboard:** https://railway.app
2. **Click on your backend service**
3. **Click "Variables" tab**
4. **Look for a variable named `PORT`**
5. **If it exists, DELETE it** (or set it to a real integer, but best: delete it)
6. **Railway will automatically inject the correct PORT value**

### **Step 2: Redeploy**

1. **In Railway Dashboard → Your Service**
2. **Click "Redeploy"** (or wait for auto-deploy)
3. **Wait 2-3 minutes** for deployment to complete

### **Step 3: Verify**

1. **Test backend health:**
   ```
   https://your-railway-url.up.railway.app/health
   ```
   Should return: `{"status":"healthy"}`

2. **Check Railway logs:**
   - Should see: "Starting uvicorn on port [number]"
   - Should NOT see: "FATAL: PORT env var must be an integer"

3. **Frontend should connect:**
   - No more "backend connection failed" error
   - Can create GPTs and chats

---

## 🛡️ **Protection Added**

The startup script now validates that `PORT` is a number:

- ✅ If `PORT` is a valid integer → starts normally
- ❌ If `PORT` is `"$PORT"` or any non-number → **fails loudly with clear error message**

**Error message will tell you exactly what to fix:**
```
FATAL: PORT env var must be an integer. Got: '$PORT'.
Fix: Railway → Service → Variables → remove any custom PORT value (Railway sets it automatically).
```

---

## 📋 **Railway Environment Variables - What to Set**

### **✅ DO Set These:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `API_KEY` - API authentication key
- `SECRET_KEY` - JWT signing key
- `CHROMA_PERSIST_DIR` - `/app/data/chromadb`
- `DATA_DIR` - `/app/data`
- `UPLOAD_DIR` - `/app/data/businesses`
- `VECTOR_DB_TYPE` - `chromadb`
- `DEBUG` - `false`
- `ALLOWED_ORIGINS` - Your frontend URL(s)

### **❌ DO NOT Set:**
- `PORT` - **Railway sets this automatically!** Do not override it!

---

## 🎯 **Quick Checklist**

- [ ] Removed `PORT` from Railway Variables (if it exists)
- [ ] Redeployed Railway service
- [ ] Tested `/health` endpoint (returns `{"status":"healthy"}`)
- [ ] Frontend connects successfully
- [ ] No more "backend connection failed" error

---

## 🎉 **After Fix**

Once `PORT` is removed from Railway Variables:
- ✅ Backend starts successfully
- ✅ Health endpoint works
- ✅ Frontend connects automatically
- ✅ All features work

**The code now fails loudly if someone breaks PORT again, making it easy to diagnose!** 🚀
