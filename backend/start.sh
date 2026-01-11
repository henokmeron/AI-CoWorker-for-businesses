#!/bin/bash
# Startup script for Railway deployment
# Railway provides PORT environment variable - use it or default to 8000

PORT=${PORT:-8000}
echo "Starting uvicorn on port $PORT"
exec uvicorn main:app --host 0.0.0.0 --port $PORT
