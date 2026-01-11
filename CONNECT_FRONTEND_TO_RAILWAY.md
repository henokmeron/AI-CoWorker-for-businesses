# 🔗 Connect Frontend to Railway Backend - URGENT FIX

## 🚨 **Problem**

Your frontend is trying to connect to:
- ❌ `https://ai-coworker-for-businesses.fly.dev` (Fly.io - not deployed)

But your backend is deployed on:
- ✅ **Railway** (you just deployed it there)

---

## ✅ **Solution: Get Your Railway Backend URL**

### **Step 1: Get Railway Backend URL**

1. **Go to Railway Dashboard:** https://railway.app
2. **Click on your backend service** (the one you just deployed)
3. **Go to "Settings" tab**
4. **Scroll to "Networking" section**
5. **Find "Public Domain"** - it looks like:
   ```
   https://your-app-name.up.railway.app
   ```
6. **Copy this URL** - this is your backend URL!

**Example Railway URL:**
```
https://ai-coworker-backend-production.up.railway.app
```

---

### **Step 2: Set BACKEND_URL in Streamlit Cloud**

1. **Go to Streamlit Cloud:** https://share.streamlit.io/
2. **Click on your app** (or create new one)
3. **Click "⚙️ Settings"** (top right)
4. **Click "Secrets" tab**
5. **Add this secret:**

```toml
BACKEND_URL = "https://your-railway-url.up.railway.app"
API_KEY = "ai-coworker-secret-key-2024"
```

**Replace `your-railway-url.up.railway.app` with your actual Railway URL!**

6. **Click "Save"**
7. **App will automatically restart** (takes 1-2 minutes)

---

## 🎯 **Alternative: If Using Streamlit Cloud Advanced Settings**

If you're deploying a new app:

1. **Go to:** https://share.streamlit.io/deploy
2. **Select your repository:** `henokmeron/AI-CoWorker-for-businesses`
3. **Main file path:** `frontend/streamlit_app.py`
4. **Click "Advanced settings"**
5. **Add environment variables:**

```
BACKEND_URL=https://your-railway-url.up.railway.app
API_KEY=ai-coworker-secret-key-2024
```

6. **Click "Deploy"**

---

## ✅ **Verify It's Working**

After setting `BACKEND_URL`:

1. **Wait 1-2 minutes** for Streamlit to restart
2. **Refresh your Streamlit app**
3. **You should see:**
   - ✅ No "Backend connection check failed" error
   - ✅ Can create GPTs
   - ✅ Can create chats
   - ✅ Everything works!

---

## 🔍 **Test Your Railway Backend First**

Before connecting the frontend, test your Railway backend:

1. **Get your Railway URL** (from Step 1 above)
2. **Test health endpoint:**
   ```
   https://your-railway-url.up.railway.app/health
   ```
   Should return: `{"status":"healthy"}`

3. **Test API docs:**
   ```
   https://your-railway-url.up.railway.app/docs
   ```
   Should show Swagger UI

**If these don't work, your Railway backend isn't running correctly!**

---

## 🚨 **If Railway Backend Isn't Working**

If your Railway backend shows errors:

1. **Check Railway logs:**
   - Railway Dashboard → Your Service → "Deployments" tab
   - Click latest deployment → Check logs

2. **Common issues:**
   - ❌ Missing environment variables
   - ❌ Build failed
   - ❌ Port not exposed correctly

3. **Fix:**
   - See `FORCE_RAILWAY_REBUILD.md` for troubleshooting
   - Make sure all environment variables are set
   - Clear build cache and redeploy

---

## 📋 **Quick Checklist**

- [ ] Got Railway backend URL (from Railway dashboard)
- [ ] Tested Railway backend health endpoint (works)
- [ ] Set `BACKEND_URL` in Streamlit Cloud secrets
- [ ] Set `API_KEY` in Streamlit Cloud secrets
- [ ] Streamlit app restarted (wait 1-2 minutes)
- [ ] Frontend now connects to Railway backend ✅

---

## 🎉 **After Fix**

Your app will work:
- ✅ Frontend connects to Railway backend
- ✅ Can create GPTs
- ✅ Can create chats
- ✅ Can upload documents
- ✅ Can ask questions
- ✅ Everything works!

---

**The frontend code is already updated to use `BACKEND_URL` environment variable. You just need to set it in Streamlit Cloud!** 🚀
