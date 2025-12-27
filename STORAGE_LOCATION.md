# Where Documents Are Actually Saved

## Current Setup (Default)

**Location:** `/app/data/businesses/{business_id}/{uuid}.{ext}`

**Storage Type:** Fly.io Persistent Volume

**Volume Name:** `ai_coworker_data`

**Is it Permanent?** ✅ **YES** - Documents are saved to a persistent volume that survives:
- Server restarts
- Deployments
- Container recreations
- App updates

## File Path Structure

```
/app/data/
└── businesses/
    ├── business_1/
    │   ├── 550e8400-e29b-41d4-a716-446655440000.pdf
    │   ├── 6ba7b810-9dad-11d1-80b4-00c04fd430c8.docx
    │   └── 6ba7b811-9dad-11d1-80b4-00c04fd430c8.xlsx
    └── business_2/
        └── 6ba7b812-9dad-11d1-80b4-00c04fd430c8.pdf
```

## How to Verify

1. **Check Fly.io Volume:**
   ```bash
   flyctl volumes list
   ```

2. **Check Volume Size:**
   ```bash
   flyctl volumes show ai_coworker_data
   ```

3. **SSH into App and Check:**
   ```bash
   flyctl ssh console
   ls -la /app/data/businesses/
   ```

## To Use AWS S3 Instead

If you want documents saved to AWS S3 (cloud storage) instead of the Fly.io volume:

1. **Set Environment Variables:**
   ```bash
   flyctl secrets set USE_CLOUD_STORAGE=true
   flyctl secrets set AWS_S3_BUCKET=your-bucket-name
   flyctl secrets set AWS_ACCESS_KEY_ID=your-key
   flyctl secrets set AWS_SECRET_ACCESS_KEY=your-secret
   ```

2. **Documents will then be saved to:**
   - **S3 Bucket:** `s3://your-bucket-name/{business_id}/{uuid}.{ext}`
   - **Not** in the Fly.io volume anymore

## Current Status

✅ **Documents ARE saved permanently**  
✅ **Using Fly.io persistent volume** (`ai_coworker_data`)  
✅ **Survives deployments and restarts**  
✅ **No setup required** - works automatically  

## Summary

- **Right now:** Documents saved to `/app/data/businesses/` on Fly.io persistent volume
- **This is permanent** - not temporary
- **To use S3:** Set the environment variables above
- **Both options are permanent** - just different storage locations

