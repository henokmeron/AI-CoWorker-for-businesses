# Dockerfile for Fly.io - Fixed null byte issue
# Updated: 2025-01-27 - Complete rewrite to fix null bytes
FROM python:3.11-slim

# Force cache invalidation - change this to break cache
ARG BUILD_ID=2025-01-27-v3-FINAL
ARG CACHE_BUST=$(date +%s)
RUN echo "Build ID: ${BUILD_ID}" > /tmp/build_id.txt && \
    echo "Cache bust: ${CACHE_BUST}" >> /tmp/build_id.txt

WORKDIR /app

# Install system dependencies
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

# Copy requirements.txt - use different path to break cache
COPY backend/requirements.txt /tmp/req_source.txt

# CRITICAL: Clean null bytes - this MUST run every time
# This step ALWAYS runs (not cached) to ensure clean file
RUN python3 << 'PYEOF'
import sys
import os

null_byte = b'\x00'
newline = b'\n'
input_file = '/tmp/req_source.txt'
output_file = '/app/requirements.txt'

print("=" * 60)
print("CLEANING REQUIREMENTS.TXT")
print("=" * 60)

# Read file in binary mode
with open(input_file, 'rb') as f:
    raw_data = f.read()

print(f"Read file: {len(raw_data)} bytes")
print(f"Lines in file: {len(raw_data.split(newline))}")

# Count null bytes
null_count = raw_data.count(null_byte)
print(f"Null bytes found: {null_count}")

# Remove ALL null bytes
cleaned_data = raw_data.replace(null_byte, b'')
null_removed = len(raw_data) - len(cleaned_data)

if null_removed > 0:
    print(f"⚠️  Removed {null_removed} null bytes!")

# Process lines - keep non-empty lines
lines = []
for line in cleaned_data.split(newline):
    line = line.strip()
    if line and not line.startswith(b'#'):
        lines.append(line)
    elif line.startswith(b'#'):
        lines.append(line)

# Write clean file
final_data = newline.join(lines) + newline
with open(output_file, 'wb') as f:
    f.write(final_data)

# Verify no null bytes remain
verify_data = open(output_file, 'rb').read()
if null_byte in verify_data:
    print("=" * 60)
    print("❌ ERROR: Null bytes still present after cleaning!")
    print("=" * 60)
    sys.exit(1)

print(f"✅ SUCCESS: Clean requirements.txt created")
print(f"   - Size: {len(final_data)} bytes")
print(f"   - Lines: {len(lines)}")
print(f"   - Null bytes: {verify_data.count(null_byte)} (should be 0)")
print("=" * 60)
PYEOF

# Double-check: Verify the file is valid and has no null bytes
RUN python3 -c "import sys; f=open('/app/requirements.txt','rb').read(); assert b'\x00' not in f, 'FAILED: Null bytes found'; print('✅ Verified: No null bytes in requirements.txt')" && \
    python3 -c "f=open('/app/requirements.txt','r'); lines=f.readlines(); print(f'✅ Verified: {len(lines)} lines in requirements.txt')"

# Install Python packages - use absolute path to cleaned file
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY backend/ .

# Create data directory structure for persistent storage
# This matches fly.toml mount: destination = "/app/data"
RUN mkdir -p /app/data/businesses && \
    mkdir -p /app/data/chromadb && \
    chmod -R 755 /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
