# Dockerfile for Fly.io deployment
# Updated: 2025-01-27 - Fixed null bytes and removed unnecessary packages
# Updated: 2025-01-27 - Added cache busting and improved null byte cleaning

FROM python:3.11-slim

# Add build argument to bust cache if needed
ARG CACHE_BUST=1

WORKDIR /app

# Install system dependencies for document processing
# NOTE: Removed tesseract-ocr, poppler-utils, pandoc (not needed without unstructured)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt to temp location first
COPY backend/requirements.txt /tmp/requirements_original.txt

# CRITICAL: Clean null bytes from requirements.txt BEFORE pip install
# Use a more robust cleaning script to handle any encoding issues
RUN python3 << 'EOF'
import sys
null_byte = b'\x00'
with open('/tmp/requirements_original.txt', 'rb') as f:
    data = f.read()
cleaned = data.replace(null_byte, b'')
null_count = len(data) - len(cleaned)
print(f'Cleaned requirements.txt: {len(data)} bytes -> {len(cleaned)} bytes (removed {null_count} null bytes)')
with open('requirements.txt', 'wb') as f:
    f.write(cleaned)
print('Successfully cleaned requirements.txt')
sys.exit(0)
EOF

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

