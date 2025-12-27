# Dockerfile for Fly.io - Fixed null byte issue
FROM python:3.11-slim

# Force cache invalidation
ARG BUILD_ID=2025-01-27-v2
RUN echo "Build ID: ${BUILD_ID}" > /tmp/build_id.txt

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

# Copy requirements.txt with a different name to break cache
COPY backend/requirements.txt /tmp/requirements_raw.txt

# CRITICAL: Clean null bytes - this MUST run every time
RUN python3 << 'PYEOF'
import sys
null_byte = b'\x00'
newline = b'\n'

# Read file
with open('/tmp/requirements_raw.txt', 'rb') as f:
    raw_data = f.read()

print(f"Read file: {len(raw_data)} bytes")

# Remove null bytes
cleaned_data = raw_data.replace(null_byte, b'')
null_removed = len(raw_data) - len(cleaned_data)

print(f"Removed {null_removed} null bytes")

# Remove empty lines and trailing whitespace
lines = []
for line in cleaned_data.split(newline):
    line = line.strip()
    if line:  # Keep non-empty lines
        lines.append(line)

# Write clean file
final_data = newline.join(lines) + newline
with open('requirements.txt', 'wb') as f:
    f.write(final_data)

# Verify
verify_data = open('requirements.txt', 'rb').read()
if null_byte in verify_data:
    print("ERROR: Null bytes still present after cleaning!")
    sys.exit(1)

print(f"SUCCESS: Clean requirements.txt created ({len(final_data)} bytes, {len(lines)} lines)")
PYEOF

# Verify the file is valid
RUN python3 -c "import sys; f=open('requirements.txt','rb').read(); assert b'\x00' not in f, 'FAILED: Null bytes found'; print('Verified: No null bytes')"

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
