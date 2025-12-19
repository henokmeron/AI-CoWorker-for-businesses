# Critical Fixes for Deployment

## Issues Fixed

### 1. ✅ Missing System Libraries (libGL.so.1)
**Problem**: Backend crashed on Render due to missing OpenGL library needed for OpenCV/document processing.

```
ERROR: libGL.so.1: cannot open shared object file: No such file or directory
```

**Fix**: Added to Dockerfile:
```dockerfile
libgl1-mesa-glx \
libglib2.0-0 \
```

### 2. ✅ ChromaDB Import Errors
**Problem**: ChromaDB was failing to import with circular import errors.

```
ERROR: cannot import name 'utils' from partially initialized module 'chromadb'
```

**Fix**: Improved error handling and logging in vector_store.py initialization.

### 3. ✅ Conversation Switching Not Working
**Problem**: Clicking different conversations didn't load their chat history.

**Fix**: Modified conversation button to actually load messages from backend:
```python
# Load messages from backend when conversation is clicked
response = api_request("GET", f"/api/v1/conversations/{conv_id}")
if response and response.status_code == 200:
    loaded_conv = response.json()
    st.session_state.chat_history = [...]
```

### 4. ✅ "New Chat" Not Creating New Conversation
**Problem**: "New Chat" button just cleared the screen but didn't create a new conversation on the backend.

**Fix**: Now creates actual conversation on backend:
```python
new_conv = create_conversation(business_id, title=new_conv_title)
st.session_state.current_conversation_id = new_conv.get('id')
```

## Deployment Steps

### Step 1: Render Will Auto-Deploy
- Render detects the GitHub push
- Builds new Docker image with fixed Dockerfile
- Deploys automatically

### Step 2: Set Environment Variables on Render
**CRITICAL**: You MUST set these on Render dashboard:

1. Go to: https://dashboard.render.com
2. Select your service: "ai-coworker-for-businesses"
3. Go to "Environment" tab
4. Add these variables:

```
OPENAI_API_KEY=your-actual-openai-api-key-here
VECTOR_DB_TYPE=chromadb
CHROMA_PERSIST_DIR=/app/data/chromadb
DATA_DIR=/app/data
UPLOAD_DIR=/app/data/businesses
```

### Step 3: Check Deployment Logs
After deployment, check logs for:
- ✅ "✅ ChromaDB imported successfully"
- ✅ "✅ Vector store client initialized successfully"
- ✅ "✅ Embedding service initialized successfully"

If you see errors:
- ❌ "Vector store client is None" = OpenAI API key not set
- ❌ "ChromaDB import failed" = System libraries missing (should be fixed now)

### Step 4: Test File Upload
1. Go to your app: https://ai-coworker-for-businesses-mm7cv4frpxmt6intuz42oe.streamlit.app
2. Click "+" button
3. Upload a test PDF
4. Check backend logs for:
   - "Generating embeddings for X chunks"
   - "Successfully stored X chunks in vector database"

### Step 5: Test Conversation Switching
1. Create multiple conversations
2. Click between them
3. Verify chat history loads correctly for each

## If Vector Store Still Fails

### Check 1: OpenAI API Key
```bash
# Test your API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Should return list of models. If error, your key is invalid.

### Check 2: Render Logs
Look for these specific errors:
- "OpenAI API key not configured" = Key not set in Render environment
- "ChromaDB import failed" = System libraries issue (should be fixed)
- "Vector store client is None" = ChromaDB didn't initialize

### Check 3: Data Directory Permissions
Render should auto-create `/app/data` but if not:
```dockerfile
RUN mkdir -p /app/data/chromadb && chmod 777 /app/data
```

## Google OAuth Still Broken
**Status**: Not implemented yet (requires OAuth app setup)

**Current behavior**: Returns HTTP 501 error with message "Not implemented yet"

**To fix properly**:
1. Create Google OAuth app in Google Cloud Console
2. Get client ID and secret
3. Add redirect URI: `https://your-app.onrender.com/api/v1/auth/google/callback`
4. Implement full OAuth flow

For now, users must use email/password login.

## Testing Checklist

After deployment completes:

- [ ] Backend starts without errors
- [ ] Vector store initializes (check logs)
- [ ] Upload a test document
- [ ] Verify "Successfully stored X chunks" in logs
- [ ] Ask a question about the document
- [ ] Verify AI retrieves information correctly
- [ ] Click "New Chat" - creates new conversation
- [ ] Switch between conversations - loads correct chat history
- [ ] No infinite upload loops
- [ ] Google OAuth shows proper error (not 400)

## Files Changed

1. `Dockerfile` - Added libgl1-mesa-glx and libglib2.0-0
2. `backend/app/services/vector_store.py` - Improved ChromaDB import error handling
3. `frontend/streamlit_app.py` - Fixed conversation switching and "New Chat" button

All changes committed and pushed to GitHub. Render should auto-deploy within 5-10 minutes.

