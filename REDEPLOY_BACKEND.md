# 🚀 Redeploy Backend to Fly.io

## The Problem
Your code on GitHub was updated 5 hours ago, but **Fly.io is still running the old version**. You need to redeploy to get the latest code.

## Quick Fix: Redeploy Now

### Step 1: Make sure you're in the right directory
```powershell
cd "C:\Henok\Co-Worker AI Assistant"
```

### Step 2: Deploy backend to Fly.io
```powershell
flyctl deploy -a ai-coworker-for-businesses
```

This will:
- ✅ Pull the latest code from your local directory
- ✅ Build a new Docker image
- ✅ Deploy it to Fly.io
- ✅ Restart the backend with the new code

### Step 3: Wait for deployment (2-5 minutes)
You'll see build progress. Wait until it says "Deployment successful".

### Step 4: Test the backend
```powershell
Invoke-WebRequest -Uri "https://ai-coworker-for-businesses.fly.dev/health" -UseBasicParsing
```

If you get a 200 response, the backend is working!

## Alternative: Deploy from GitHub (Recommended)

If you want Fly.io to automatically deploy when you push to GitHub:

### Option 1: Manual deploy from GitHub
```powershell
flyctl deploy -a ai-coworker-for-businesses --remote-only
```

This tells Fly.io to pull from GitHub instead of local files.

### Option 2: Set up GitHub Actions (Auto-deploy)

Create `.github/workflows/fly-deploy.yml`:

```yaml
name: Fly Deploy
on:
  push:
    branches: [main]
    paths:
      - 'backend/**'
      - 'Dockerfile*'
      - 'fly.toml'

jobs:
  deploy:
    name: Deploy app
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only -a ai-coworker-for-businesses
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

Then add `FLY_API_TOKEN` to GitHub Secrets:
1. Go to https://github.com/henokmeron/AI-CoWorker-for-businesses/settings/secrets/actions
2. Click "New repository secret"
3. Name: `FLY_API_TOKEN`
4. Value: Get it from `flyctl auth token`

## What Happens During Deployment

1. **Build**: Fly.io builds a Docker image from your code
2. **Test**: Checks if the build succeeded
3. **Deploy**: Replaces the old running instance with the new one
4. **Health Check**: Verifies the new instance is working
5. **Switch**: Routes traffic to the new instance

## Troubleshooting

### If deployment fails:

1. **Check logs:**
   ```powershell
   flyctl logs -a ai-coworker-for-businesses
   ```

2. **Check build errors:**
   - Missing dependencies?
   - Dockerfile issues?
   - Environment variables missing?

3. **Verify Dockerfile exists:**
   ```powershell
   Test-Path backend/Dockerfile
   Test-Path Dockerfile.flyio
   ```

4. **Check fly.toml:**
   ```powershell
   Get-Content fly.toml
   ```

### If backend still doesn't work after deployment:

1. **Check if app is running:**
   ```powershell
   flyctl status -a ai-coworker-for-businesses
   ```

2. **Restart the app:**
   ```powershell
   flyctl apps restart -a ai-coworker-for-businesses
   ```

3. **Check environment variables:**
   ```powershell
   flyctl secrets list -a ai-coworker-for-businesses
   ```

## Quick Command Reference

```powershell
# Deploy from local code
flyctl deploy -a ai-coworker-for-businesses

# Deploy from GitHub
flyctl deploy -a ai-coworker-for-businesses --remote-only

# Check status
flyctl status -a ai-coworker-for-businesses

# View logs
flyctl logs -a ai-coworker-for-businesses

# Restart app
flyctl apps restart -a ai-coworker-for-businesses
```

## After Deployment

1. ✅ Wait 30 seconds for the app to start
2. ✅ Test the health endpoint
3. ✅ Refresh your Streamlit frontend
4. ✅ The warning should disappear!

