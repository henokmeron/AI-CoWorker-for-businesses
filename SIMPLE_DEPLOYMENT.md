# 🚀 Simple Deployment Guide

## Quick Answers to Your Questions

### 1. Where Do I Put My API Key?

**Step 1:** Create a `.env` file in the project root (copy from `env.example.txt`)

**Step 2:** Add your OpenAI API key:
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**That's it!** The app will automatically use it.

**For Cloud Deployment:**
- Railway/Render: Add it in their dashboard under "Environment Variables"
- Docker: The `.env` file is automatically loaded
- VPS: Same `.env` file

---

### 2. How Do I Deploy?

#### Option 1: Railway (Easiest - Like Vercel but for Python)

**Steps:**
1. Go to [railway.app](https://railway.app) and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your GitHub repository: `henokmeron/AI-CoWorker-for-businesses`
4. Railway auto-detects it's a Docker project
5. Add environment variables:
   - `OPENAI_API_KEY` = your key
   - `API_KEY` = any secret password (for API access)
6. Click "Deploy"
7. Railway gives you a URL like: `https://your-app.railway.app`

**Done!** Your app is live. No Docker knowledge needed.

**Cost:** Free tier available, paid starts at $5/month

---

#### Option 2: Render (Also Easy)

**Steps:**
1. Go to [render.com](https://render.com) and sign up
2. Click "New" → "Web Service"
3. Connect your GitHub repo
4. Settings:
   - **Environment:** Docker
   - **Dockerfile Path:** `backend/Dockerfile`
   - Add environment variables (same as Railway)
5. Deploy

**Cost:** Free tier available

---

#### Option 3: Docker (On Your Computer or VPS)

**On Your Computer:**
```bash
# 1. Create .env file
cp env.example.txt .env
# Edit .env and add OPENAI_API_KEY

# 2. Start everything
docker-compose up -d

# 3. Access at http://localhost:8501
```

**On a VPS (DigitalOcean, AWS, etc.):**
- Same commands, but accessible from the internet
- Add nginx for domain name
- See DEPLOYMENT.md for details

---

### 3. Do I Need Login/Password?

**Current Setup:**
- **No user login system** (like Gmail login)
- Uses **API key authentication** (simple password)
- Anyone with the API key can access it

**How It Works:**
1. You set an `API_KEY` in `.env` (like a password)
2. The frontend automatically uses it
3. For API access, you need to include it in headers

**Is It Open Source?**
- ✅ Code is open source (MIT License)
- ✅ You can see all the code
- ✅ You can modify it
- ⚠️ But your `.env` file (with API keys) should be **private** (not in GitHub)

**To Add User Login (Future):**
- Would need to add authentication system
- OAuth (Google login) can be added later
- For now, API key is simpler for prototype

---

## Step-by-Step: Deploy to Railway (Recommended)

### 1. Prepare Your Repository
```bash
# Make sure .env is NOT in GitHub (it's in .gitignore)
# Your code is already on GitHub ✅
```

### 2. Deploy on Railway

1. **Sign up:** https://railway.app
2. **New Project** → **Deploy from GitHub**
3. **Select repo:** `AI-CoWorker-for-businesses`
4. **Railway auto-detects Docker** ✅
5. **Add Environment Variables:**
   ```
   OPENAI_API_KEY = sk-your-key-here
   API_KEY = your-secret-password
   ```
6. **Deploy** (takes 2-5 minutes)

### 3. Access Your App
- Railway gives you a URL
- Open it in browser
- Your app is live! 🎉

### 4. Deploy Frontend (Optional)
- Railway can also deploy the frontend
- Or use Streamlit Cloud (free): https://streamlit.io/cloud
- Connect your GitHub repo
- Set `BACKEND_URL` to your Railway backend URL

---

## Environment Variables Cheat Sheet

**Required:**
```env
OPENAI_API_KEY=sk-xxx          # Your OpenAI key
API_KEY=any-secret-password     # For API access
```

**Optional:**
```env
LLM_PROVIDER=openai            # or anthropic, ollama
OPENAI_MODEL=gpt-4-turbo-preview
MAX_FILE_SIZE_MB=50
```

---

## Quick Comparison

| Method | Difficulty | Cost | Best For |
|--------|-----------|------|----------|
| **Railway** | ⭐ Easy | $5-20/mo | Quick deployment |
| **Render** | ⭐ Easy | $7-20/mo | Quick deployment |
| **Docker (Local)** | ⭐⭐ Medium | Free | Testing |
| **Docker (VPS)** | ⭐⭐⭐ Hard | $5-10/mo | Full control |

---

## Common Questions

**Q: Can I use Vercel?**
A: Not directly. Vercel is for static sites. Use Railway/Render instead (same ease, works with Python).

**Q: Where do I get OpenAI API key?**
A: https://platform.openai.com/api-keys → Create new key

**Q: Is my API key safe?**
A: Yes, if you:
- ✅ Don't commit `.env` to GitHub (already in `.gitignore`)
- ✅ Only add it in cloud platform's secure environment variables
- ✅ Don't share it publicly

**Q: Can I use it without API key?**
A: Yes! Use Ollama (local LLM, free):
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
# No API key needed!
```

**Q: Do I need to login every time?**
A: No. The API key is stored in `.env` and used automatically. No user login system (can be added later).

---

## Recommended: Railway Deployment

**Why Railway?**
- ✅ Easiest (like Vercel for Python)
- ✅ Auto-detects Docker
- ✅ Free tier available
- ✅ Auto-deploys on git push
- ✅ Built-in HTTPS
- ✅ No server management

**Time to deploy:** 5-10 minutes

**Steps:**
1. Sign up at railway.app
2. Connect GitHub repo
3. Add `OPENAI_API_KEY` in environment variables
4. Deploy
5. Done! 🎉

---

## Need Help?

- **Railway Docs:** https://docs.railway.app
- **Render Docs:** https://render.com/docs
- **Full Deployment Guide:** See `DEPLOYMENT.md`

