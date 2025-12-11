# Setup Neon Database - Step by Step Guide

## Quick Setup

1. **Go to Neon Console**: https://console.neon.tech
2. **Select your project** (or create one if you don't have one)
3. **Open SQL Editor** (left sidebar)
4. **Copy and paste** the entire contents of `database_schema.sql`
5. **Click "Run"** to execute
6. **Verify tables created**: You should see `conversations` and `messages` tables

## What the Schema Creates

- **conversations table**: Stores chat sessions
  - `id`: Unique conversation ID
  - `business_id`: Which business owns this conversation
  - `title`: Conversation title
  - `archived`: Whether conversation is archived
  - `tags`: JSON array for organizing conversations

- **messages table**: Stores individual messages
  - `id`: Auto-incrementing message ID
  - `conversation_id`: Links to conversation
  - `role`: "user" or "assistant"
  - `content`: Message text
  - `sources`: JSON array of source citations

## Verify It Worked

After running the SQL, check:
1. Tables should appear in Neon dashboard
2. Backend logs should show "✅ Database tables initialized successfully"
3. No more database errors in backend logs

## Troubleshooting

If you see errors:
- Make sure DATABASE_URL is set correctly in Render
- Check that the connection string includes `?sslmode=require`
- Verify tables were created in Neon SQL Editor

