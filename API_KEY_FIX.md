# API Key Authentication Fix

## Problem
All API requests were returning `403 Forbidden` because the API_KEY didn't match between:
- Streamlit frontend: `"ai-coworker-secret-key-2024"` (hardcoded default)
- Fly.io backend: Not set (using default `"change-this-in-production"`)

## Solution Applied
✅ Set API_KEY in Fly.io secrets to match Streamlit:
```bash
flyctl secrets set API_KEY=ai-coworker-secret-key-2024 -a ai-coworker-for-businesses
```

✅ Restarted the app to apply the new secret

## Current Secrets in Fly.io
- `OPENAI_API_KEY` ✅ Set
- `DATABASE_URL` ✅ Set  
- `API_KEY` ✅ Set to `ai-coworker-secret-key-2024`

## For Production
**IMPORTANT:** Change the API_KEY to a secure random value:

1. **Generate a secure key:**
   ```bash
   openssl rand -hex 32
   ```

2. **Set it in Fly.io:**
   ```bash
   flyctl secrets set API_KEY=<generated-key> -a ai-coworker-for-businesses
   ```

3. **Set it in Streamlit Cloud environment variables:**
   - Go to Streamlit Cloud dashboard
   - Settings → Secrets
   - Add: `API_KEY = <same-generated-key>`

4. **Or update the default in Streamlit app:**
   - Edit `frontend/streamlit_app.py`
   - Change line 20: `API_KEY = os.getenv("API_KEY", "<generated-key>")`

## Verify It's Working
After restart, check the logs - you should see `200 OK` instead of `403 Forbidden`:
```bash
flyctl logs -a ai-coworker-for-businesses
```

You should see successful requests like:
```
INFO: "GET /api/v1/businesses HTTP/1.1" 200 OK
```

