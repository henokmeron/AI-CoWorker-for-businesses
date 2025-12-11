# 🔍 Troubleshooting Guide - Why Chat Isn't Working

## What's Happening Right Now

### The Problem:
1. **You send a message** → Frontend sends request to backend
2. **Backend tries to process** → But something fails
3. **Error message shows** → "Sorry, I encountered an error"

### Why This Happens:

**Most Likely Causes:**

1. **OpenAI API Key Not Set in Render** ❌
   - Backend can't call OpenAI
   - Error: "OpenAI API key not configured"

2. **Backend Not Deployed Yet** ⏳
   - Your latest code isn't live
   - Old code is still running

3. **Backend Crashed** 💥
   - Check Render logs for errors
   - Might be a dependency issue

---

## How to Fix - Step by Step

### Step 1: Check Render Environment Variables

**Go to Render Dashboard:**
1. https://dashboard.render.com/
2. Click your backend service
3. Go to "Environment" tab
4. **Check if you have:**
   ```
   OPENAI_API_KEY=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
   ```

**If missing:**
- Click "Add Environment Variable"
- Key: `OPENAI_API_KEY`
- Value: Your API key (above)
- Save

### Step 2: Check Render Logs

**In Render Dashboard:**
1. Click your backend service
2. Go to "Logs" tab
3. **Look for errors:**
   - "OpenAI API key not configured" → Add API key
   - "Failed to generate response" → Check API key validity
   - "Import error" → Dependency issue

### Step 3: Force Redeploy Backend

**In Render Dashboard:**
1. Click your backend service
2. Click "Manual Deploy" (top right)
3. Select "Clear build cache & deploy"
4. Wait 5-10 minutes

### Step 4: Check Backend is Running

**Test the backend directly:**
```
https://ai-coworker-for-businesses.onrender.com/health
```

**Should return:**
```json
{"status": "healthy", "version": "1.0.0"}
```

**If it doesn't work:**
- Backend is down
- Check Render logs
- Redeploy

### Step 5: Test Chat Endpoint Directly

**Open this URL:**
```
https://ai-coworker-for-businesses.onrender.com/docs
```

**Try the chat endpoint:**
1. Click "POST /api/v1/chat"
2. Click "Try it out"
3. Enter:
   ```json
   {
     "business_id": "test",
     "query": "What time is it?",
     "conversation_history": [],
     "max_sources": 5
   }
   ```
4. Click "Execute"

**If it works:**
- Backend is fine
- Problem is frontend connection

**If it fails:**
- Check the error message
- Likely missing OpenAI API key

---

## Common Errors & Fixes

### Error: "OpenAI API key not configured"
**Fix:** Add `OPENAI_API_KEY` to Render environment variables

### Error: "Internal Server Error"
**Fix:** 
1. Check Render logs for actual error
2. Usually means API key is wrong or missing
3. Or backend code has a bug

### Error: "Cannot connect to backend"
**Fix:**
1. Check backend URL is correct in Streamlit
2. Backend might be sleeping (Render free tier)
3. Wait 30 seconds and try again

### Error: "Failed to process query"
**Fix:**
1. Check OpenAI API key is valid
2. Check you have credits in OpenAI account
3. Check Render logs for details

---

## Quick Diagnostic

**Run these checks:**

1. **Backend Health:**
   ```
   https://ai-coworker-for-businesses.onrender.com/health
   ```
   ✅ Should return JSON

2. **Backend API Docs:**
   ```
   https://ai-coworker-for-businesses.onrender.com/docs
   ```
   ✅ Should show API documentation

3. **Test Chat Endpoint:**
   - Use the `/docs` page
   - Try POST /api/v1/chat
   - See if it works

4. **Check Environment Variables:**
   - Render → Your service → Environment
   - Must have `OPENAI_API_KEY`

---

## Why You Have to Redeploy

**Render Auto-Deploy:**
- Render watches your GitHub repo
- When you push, it should auto-deploy
- But sometimes it doesn't trigger

**Manual Deploy:**
- Click "Manual Deploy" in Render
- Select "Clear build cache & deploy"
- This forces a fresh build

**Why Streamlit Updates Automatically:**
- Streamlit Cloud watches GitHub
- Auto-deploys when you push
- Usually faster (1-2 minutes)

---

## Current Status Check

**Right now, check:**

1. ✅ **Is backend running?**
   - Go to: https://ai-coworker-for-businesses.onrender.com/health
   - Should show: `{"status": "healthy"}`

2. ✅ **Is OpenAI API key set?**
   - Render → Environment → Check for `OPENAI_API_KEY`

3. ✅ **Are latest changes deployed?**
   - Check Render logs for recent deployment
   - Should see "Deploy succeeded"

4. ✅ **Is frontend connecting?**
   - Check browser console (F12)
   - Look for connection errors

---

## Next Steps

1. **Check Render environment variables** (most important!)
2. **Check Render logs** for actual error
3. **Test backend directly** using `/docs` page
4. **If still broken**, share the exact error from Render logs

---

## Need Help?

**Share these:**
1. Render logs (last 50 lines)
2. Error message from frontend
3. Backend health check result
4. Environment variables (just names, not values)

Then I can fix it quickly!

