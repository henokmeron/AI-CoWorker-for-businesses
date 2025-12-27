# Cloud Storage Setup Guide

## Overview

Documents are now saved to **permanent cloud storage** instead of temporary filesystem storage. This ensures your documents persist even after server restarts or deployments.

## Supported Storage Providers

### 1. AWS S3 (Recommended - Free Tier Available)
- **Free Tier**: 5GB storage, 20,000 GET requests, 2,000 PUT requests per month for 12 months
- **Setup**: Create an S3 bucket and get access keys

### 2. Local Storage (Fallback)
- Used when cloud storage is not configured
- Files saved to `/app/data/businesses/` (persistent volume on Fly.io)

## Setup Instructions

### Option 1: AWS S3 (Recommended)

1. **Create AWS Account** (if you don't have one)
   - Go to https://aws.amazon.com/
   - Sign up (requires credit card, but free tier is generous)

2. **Create S3 Bucket**
   - Go to AWS Console → S3
   - Click "Create bucket"
   - Choose a unique name (e.g., `ai-coworker-documents`)
   - Select region (e.g., `us-east-1`)
   - Keep default settings (public access can be blocked)
   - Click "Create bucket"

3. **Create IAM User for Access**
   - Go to AWS Console → IAM → Users
   - Click "Create user"
   - Username: `ai-coworker-storage`
   - Select "Programmatic access"
   - Click "Next"

4. **Attach S3 Policy**
   - Click "Attach policies directly"
   - Search for "S3" and select "AmazonS3FullAccess" (or create custom policy with only your bucket)
   - Click "Next" → "Create user"

5. **Get Access Keys**
   - Click on the user you just created
   - Go to "Security credentials" tab
   - Click "Create access key"
   - Select "Application running outside AWS"
   - Copy the **Access Key ID** and **Secret Access Key** (save these securely!)

6. **Set Environment Variables in Fly.io**
   ```bash
   flyctl secrets set USE_CLOUD_STORAGE=true
   flyctl secrets set STORAGE_PROVIDER=s3
   flyctl secrets set AWS_S3_BUCKET=your-bucket-name
   flyctl secrets set AWS_S3_REGION=us-east-1
   flyctl secrets set AWS_ACCESS_KEY_ID=your-access-key-id
   flyctl secrets set AWS_SECRET_ACCESS_KEY=your-secret-access-key
   ```

### Option 2: Use Fly.io Persistent Volume (Free, No Setup)

If you don't want to set up AWS S3, the app will use local storage on Fly.io's persistent volume:

1. **Ensure Fly.io Volume is Configured**
   - Check `fly.toml` - it should have a `[[mounts]]` section
   - The volume `ai_coworker_data` should be created

2. **No Additional Setup Needed**
   - Documents will be saved to `/app/data/businesses/` on the persistent volume
   - This persists across deployments

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `USE_CLOUD_STORAGE` | Enable cloud storage | No | `false` |
| `STORAGE_PROVIDER` | Storage provider (`s3`, `gcs`, `azure`) | No | `s3` |
| `AWS_S3_BUCKET` | S3 bucket name | Yes (if using S3) | - |
| `AWS_S3_REGION` | AWS region | No | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes (if using S3) | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes (if using S3) | - |

## How It Works

1. **Document Upload**: User uploads a document
2. **Temporary Storage**: File saved temporarily to `/tmp`
3. **Permanent Storage**: File uploaded to cloud storage (S3) or local persistent volume
4. **Metadata Saved**: Document metadata saved to database
5. **Vector Storage**: Document processed and embeddings stored in vector DB
6. **Permanent**: Document is now permanently stored and accessible

## Benefits

✅ **Permanent Storage**: Documents never disappear  
✅ **Scalable**: Can handle unlimited documents  
✅ **Reliable**: Cloud storage is highly available  
✅ **Cost-Effective**: Free tier covers most use cases  
✅ **Backup**: Cloud storage includes automatic backups  

## Troubleshooting

### Documents Still Disappearing?

1. Check if `USE_CLOUD_STORAGE=true` is set
2. Verify AWS credentials are correct
3. Check S3 bucket permissions
4. Review application logs for storage errors

### AWS S3 Setup Issues?

1. Ensure bucket name is unique globally
2. Verify IAM user has S3 permissions
3. Check region matches bucket region
4. Test credentials with AWS CLI: `aws s3 ls s3://your-bucket-name`

## Free Storage Options

- **AWS S3**: 5GB free for 12 months
- **Google Cloud Storage**: 5GB free tier
- **Azure Blob Storage**: 5GB free tier
- **Backblaze B2**: 10GB free tier (no time limit)
- **Cloudinary**: 25GB free tier (for images/videos)

For this application, **AWS S3** is recommended due to:
- Easiest setup
- Most reliable
- Best documentation
- Generous free tier

