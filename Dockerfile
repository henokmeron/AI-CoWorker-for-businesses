# Dockerfile for Fly.io deployment
# Updated: 2025-01-27 - Fixed null bytes and removed unnecessary packages
# Updated: 2025-01-27 - Added cache busting and improved null byte cleaning
# Updated: 2025-01-27 - Force cache invalidation

FROM python:3.11-slim

# Add build argument to bust cache if needed
ARG CACHE_BUST=2
ARG BUILD_DATE=2025-01-27

WORKDIR /app

# Force cache invalidation by touching a file
RUN echo "Build date: ${BUILD_DATE}" > /tmp/build_info.txt

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
# IMPORTANT: This step MUST run (not cached) to ensure we get the latest file
COPY --chmod=644 backend/requirements.txt /tmp/requirements_original.txt

# CRITICAL: Clean null bytes from requirements.txt BEFORE pip install
# Use a more robust cleaning script to handle any encoding issues
# This step will always run and clean the file, even if it's cached
RUN python3 << 'EOF'
import sys
import os

null_byte = b'\x00'
input_file = '/tmp/requirements_original.txt'
output_file = 'requirements.txt'

print(f'Reading file: {input_file}')
with open(input_file, 'rb') as f:
    data = f.read()

print(f'Original file size: {len(data)} bytes')
print(f'Original file lines: {len(data.split(b"\\n"))}')

# Remove null bytes
cleaned = data.replace(null_byte, b'')
null_count = len(data) - len(cleaned)

print(f'Cleaned requirements.txt: {len(data)} bytes -> {len(cleaned)} bytes (removed {null_count} null bytes)')

# Verify the cleaned file is valid (no null bytes remaining)
if null_byte in cleaned:
    print('ERROR: Null bytes still present after cleaning!')
    sys.exit(1)

# Also remove any empty lines that might cause issues
lines = [line for line in cleaned.split(b'\n') if line.strip()]
cleaned = b'\n'.join(lines)

# Write cleaned file
with open(output_file, 'wb') as f:
    f.write(cleaned)
    f.write(b'\n')  # Ensure file ends with newline

print(f'Successfully cleaned and verified requirements.txt: {len(cleaned)} bytes, {len(lines)} lines')
print(f'Output file exists: {os.path.exists(output_file)}')
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

