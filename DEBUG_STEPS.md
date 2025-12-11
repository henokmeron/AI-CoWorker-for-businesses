# 🔍 Debug Steps - Find the Actual Error

## Step 1: Check Render Logs (MOST IMPORTANT)

**This will show you the EXACT error:**

1. Go to: https://dashboard.render.com/
2. Click your backend service
3. Click "Logs" tab
4. **Look for recent errors** (red text)
5. **Copy the last 20-30 lines** and share them

**What to look for:**
- "OpenAI API key not configured" → API key not being read
- "Authentication failed" → API key is wrong
- "Rate limit" → Too many requests
- "Import error" → Code issue
- Any red error messages

---

## Step 2: Test Debug Endpoint

**After backend redeploys (5 minutes), test:**

```
https://ai-coworker-for-businesses.onrender.com/debug
```

**This will show:**
- Is API key set? (true/false)
- API key length
- API key prefix (first 10 chars)
- Current configuration

**Share the result** - this will tell us if the API key is being read correctly.

---

## Step 3: Test Chat Endpoint Directly

**Go to:**
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
     "query": "Hello",
     "conversation_history": [],
     "max_sources": 5
   }
   ```
4. Click "Execute"
5. **See the exact error message**

**Share the error** - this is the real problem.

---

## Step 4: Check Environment Variables Format

**In Render:**
1. Go to Environment tab
2. **Check the variable name is EXACTLY:**
   ```
   OPENAI_API_KEY
   ```
   (No spaces, exact case)

3. **Check the value starts with:**
   ```
   sk-proj-
   ```
   (Should start with this)

---

## Common Issues

### Issue 1: API Key Not Being Read
**Symptom:** Debug endpoint shows `openai_api_key_set: false`
**Fix:** 
- Check variable name is exactly `OPENAI_API_KEY`
- Make sure it's saved
- Restart the service

### Issue 2: API Key Invalid
**Symptom:** Error says "Authentication failed" or "Invalid API key"
**Fix:**
- Check the API key is correct
- Make sure it hasn't expired
- Check OpenAI account has credits

### Issue 3: Backend Not Redeployed
**Symptom:** Old error messages, debug endpoint doesn't exist
**Fix:**
- Click "Manual Deploy" in Render
- Select "Clear build cache & deploy"
- Wait 5-10 minutes

---

## What I Need From You

**To fix this quickly, share:**

1. **Render logs** (last 30 lines from Logs tab)
2. **Debug endpoint result** (from `/debug` URL)
3. **Chat endpoint error** (from `/docs` page test)

**With this info, I can fix it in 2 minutes!**

---

## Quick Test Right Now

**Test these URLs:**

1. **Health:**
   ```
   https://ai-coworker-for-businesses.onrender.com/health
   ```
   Should return: `{"status": "healthy"}`

2. **Debug (after redeploy):**
   ```
   https://ai-coworker-for-businesses.onrender.com/debug
   ```
   Shows API key status

3. **API Docs:**
   ```
   https://ai-coworker-for-businesses.onrender.com/docs
   ```
   Test chat endpoint here

**Share the results!**

