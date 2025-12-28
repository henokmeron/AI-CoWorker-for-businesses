# CRITICAL: Fly.io Volume Setup for Document Persistence

## The Problem
Documents were disappearing because ChromaDB was writing to an ephemeral filesystem that gets wiped on restart. The `fly.toml` file was missing the volume mount configuration.

## The Fix
I've added the volume mount to `fly.toml`, but you need to create the volume in Fly.io.

## Steps to Fix Persistence

### 1. Create the Persistent Volume
Run this command in your terminal:

```bash
fly volumes create ai_coworker_data --size 10 --region lhr
```

This creates a 10GB persistent volume named `ai_coworker_data` in the London region (matching your app's primary region).

### 2. Verify Volume is Created
```bash
fly volumes list
```

You should see `ai_coworker_data` in the list.

### 3. Deploy the Updated Configuration
The `fly.toml` now includes:
```toml
[[mounts]]
  destination = "/app/data"
  source = "ai_coworker_data"
```

Deploy with:
```bash
fly deploy
```

### 4. Verify Volume is Mounted
After deployment, check the logs:
```bash
fly logs
```

You should see:
```
✅ Initializing ChromaDB at /app/data/chromadb (persistent volume)
```

### 5. Test Document Persistence
1. Upload a document
2. Wait a few minutes
3. Ask a question about it
4. The AI should still remember the document

## What This Fixes

✅ **Documents persist across restarts** - ChromaDB data survives app restarts
✅ **Documents persist across deployments** - Data survives code updates
✅ **Documents persist across container recreations** - Data survives container changes
✅ **Documents are searchable long-term** - Vector database is permanently stored

## Troubleshooting

If documents still disappear:

1. **Check volume is mounted:**
   ```bash
   fly ssh console
   ls -la /app/data
   ```
   You should see `chromadb` and `businesses` directories.

2. **Check ChromaDB directory:**
   ```bash
   fly ssh console
   ls -la /app/data/chromadb
   ```
   You should see ChromaDB files.

3. **Check collection exists:**
   Look in logs for:
   ```
   ✅ Retrieved existing collection 'business_temp_chat' with X documents
   ```

4. **Verify business_id consistency:**
   - Upload uses: `business_id = selected_gpt or "temp_chat"`
   - Query uses: `business_id = selected_gpt or "temp_chat"`
   - Both should match!

## Important Notes

- The volume is **persistent** - data survives everything
- The volume is **region-specific** - must be in same region as app (lhr)
- The volume has a **size limit** - 10GB should be plenty for documents
- You can **increase volume size** later if needed:
  ```bash
  fly volumes extend ai_coworker_data --size 20
  ```

