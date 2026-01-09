# Backend Troubleshooting Guide

## Issue: Backend Not Responding

If you see the error: **"⚠️ Backend connection check failed. The app may not work correctly."**

This means the backend at `https://ai-coworker-for-businesses.fly.dev` is either:
1. Not running (stopped/crashed)
2. Not deployed
3. Missing environment variables
4. Experiencing startup errors

## Quick Fix Steps

### Step 1: Check Backend Status

Open PowerShell and run:
```powershell
flyctl status -a ai-coworker-for-businesses
```

This will show:
- Whether the app is running
- Current machine status
- Recent errors

### Step 2: Check Backend Logs

View recent logs to see what's wrong:
```powershell
flyctl logs -a ai-coworker-for-businesses
```

Look for:
- Startup errors
- Missing environment variables
- Import errors
- Database connection issues

### Step 3: Restart the Backend

If the app is stopped or crashed, restart it:
```powershell
flyctl apps restart -a ai-coworker-for-businesses
```

### Step 4: Check Environment Variables

Verify required secrets are set:
```powershell
flyctl secrets list -a ai-coworker-for-businesses
```

**Required secrets:**
- `OPENAI_API_KEY` - **CRITICAL** - Without this, the app will crash
- `API_KEY` - Should be `ai-coworker-secret-key-2024` (or your custom key)
- `DATABASE_URL` - If using PostgreSQL
- `SECRET_KEY` - For authentication

### Step 5: Set Missing Secrets

If any secrets are missing, set them:

```powershell
# Set OpenAI API Key (REQUIRED)
flyctl secrets set OPENAI_API_KEY=sk-your-key-here -a ai-coworker-for-businesses

# Set API Key (should match frontend)
flyctl secrets set API_KEY=ai-coworker-secret-key-2024 -a ai-coworker-for-businesses

# Set Secret Key
flyctl secrets set SECRET_KEY=your-secret-key-here -a ai-coworker-for-businesses
```

After setting secrets, restart:
```powershell
flyctl apps restart -a ai-coworker-for-businesses
```

### Step 6: Redeploy (If Restart Doesn't Work)

If restart doesn't fix it, redeploy:
```powershell
cd backend
flyctl deploy -a ai-coworker-for-businesses
```

Or from root directory:
```powershell
flyctl deploy -a ai-coworker-for-businesses --config fly.toml
```

### Step 7: Test Backend Directly

Test the health endpoint:
```powershell
Invoke-WebRequest -Uri "https://ai-coworker-for-businesses.fly.dev/health" -UseBasicParsing
```

Or test the root endpoint:
```powershell
Invoke-WebRequest -Uri "https://ai-coworker-for-businesses.fly.dev/" -UseBasicParsing
```

## Common Issues

### Issue: "App is stopped"
**Solution:** Start the app:
```powershell
flyctl apps start -a ai-coworker-for-businesses
```

### Issue: "OPENAI_API_KEY not set"
**Solution:** Set the OpenAI API key (see Step 5)

### Issue: "Vector store initialization failed"
**Solution:** Check if ChromaDB volume is mounted:
```powershell
flyctl volumes list -a ai-coworker-for-businesses
```

If no volume exists, create it:
```powershell
flyctl volumes create ai_coworker_data --size 10 --region lhr -a ai-coworker-for-businesses
```

### Issue: "Port 8000 not accessible"
**Solution:** Check fly.toml configuration - internal_port should be 8000

### Issue: "Machine crashed on startup"
**Solution:** 
1. Check logs: `flyctl logs -a ai-coworker-for-businesses`
2. Look for Python errors, missing dependencies, or import failures
3. Redeploy with latest code

## Verify Backend is Working

After fixing, verify:
1. Health check returns 200:
   ```powershell
   $response = Invoke-WebRequest -Uri "https://ai-coworker-for-businesses.fly.dev/health" -UseBasicParsing
   Write-Host "Status: $($response.StatusCode)"
   ```

2. Frontend should stop showing the warning

3. You should be able to:
   - Upload documents
   - Send chat messages
   - Get responses from the AI

## Still Not Working?

1. **Check Fly.io Dashboard:**
   - Go to https://fly.io/dashboard
   - Select your app: `ai-coworker-for-businesses`
   - Check "Metrics" and "Logs" tabs

2. **Check Machine Status:**
   ```powershell
   flyctl machines list -a ai-coworker-for-businesses
   ```

3. **SSH into Machine (for debugging):**
   ```powershell
   flyctl ssh console -a ai-coworker-for-businesses
   ```

4. **Check if port is correct:**
   - Verify `fly.toml` has `internal_port = 8000`
   - Verify backend code uses port 8000

5. **Check CORS settings:**
   - Backend should allow requests from your frontend domain
   - Check `ALLOWED_ORIGINS` in backend config

## Need Help?

If none of these steps work:
1. Share the output of `flyctl logs -a ai-coworker-for-businesses`
2. Share the output of `flyctl status -a ai-coworker-for-businesses`
3. Check the Fly.io dashboard for any alerts or errors

