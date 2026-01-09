# 🚨 URGENT: Backend Fix Required

## Current Status
Your backend at `https://ai-coworker-for-businesses.fly.dev` is **NOT RESPONDING**.

The frontend has been fixed to work better when the backend is down, but **you still need to fix the backend** for full functionality.

## Quick Fix (5 minutes)

### Step 1: Check if backend is running
```powershell
flyctl status -a ai-coworker-for-businesses
```

### Step 2: Check backend logs for errors
```powershell
flyctl logs -a ai-coworker-for-businesses
```

**Look for:**
- Missing `OPENAI_API_KEY` error
- Python import errors
- Port binding errors
- Database connection errors

### Step 3: Restart the backend
```powershell
flyctl apps restart -a ai-coworker-for-businesses
```

### Step 4: If restart doesn't work, check environment variables
```powershell
flyctl secrets list -a ai-coworker-for-businesses
```

**Required secrets:**
- ✅ `OPENAI_API_KEY` - **CRITICAL** - Without this, backend crashes
- ✅ `API_KEY` - Should be `ai-coworker-secret-key-2024`
- ✅ `SECRET_KEY` - For authentication

### Step 5: Set missing secrets
If any are missing:

```powershell
# Set OpenAI API Key (REQUIRED)
flyctl secrets set OPENAI_API_KEY=sk-your-key-here -a ai-coworker-for-businesses

# Set API Key
flyctl secrets set API_KEY=ai-coworker-secret-key-2024 -a ai-coworker-for-businesses

# Set Secret Key
flyctl secrets set SECRET_KEY=your-secret-key-here -a ai-coworker-for-businesses
```

Then restart:
```powershell
flyctl apps restart -a ai-coworker-for-businesses
```

### Step 6: Wait and test
Wait 15-30 seconds, then test:
```powershell
Invoke-WebRequest -Uri "https://ai-coworker-for-businesses.fly.dev/health" -UseBasicParsing
```

If you get a 200 response, the backend is working!

## Automated Fix Script

Run this script to automatically diagnose and fix:
```powershell
.\fix_backend.ps1
```

## What Was Fixed in Frontend

✅ Frontend now shows **cached GPTs** even when backend is down
✅ **Clear error messages** when creating GPTs/chats fails
✅ **UI doesn't break** when backend is unavailable
✅ **Helpful tips** shown when backend operations fail

## Still Not Working?

1. **Check Fly.io Dashboard:**
   - Go to https://fly.io/dashboard
   - Select app: `ai-coworker-for-businesses`
   - Check "Metrics" and "Logs"

2. **Check if app is stopped:**
   ```powershell
   flyctl apps start -a ai-coworker-for-businesses
   ```

3. **Redeploy backend:**
   ```powershell
   flyctl deploy -a ai-coworker-for-businesses
   ```

4. **Check machine status:**
   ```powershell
   flyctl machines list -a ai-coworker-for-businesses
   ```

## Most Common Issue

**90% of the time, the issue is:**
- Missing `OPENAI_API_KEY` → Backend crashes on startup
- App is stopped → Fly.io auto-stopped it

**Fix:**
```powershell
# Set the key
flyctl secrets set OPENAI_API_KEY=sk-your-key-here -a ai-coworker-for-businesses

# Start the app
flyctl apps start -a ai-coworker-for-businesses
```

## Need More Help?

See `BACKEND_TROUBLESHOOTING.md` for detailed troubleshooting steps.

