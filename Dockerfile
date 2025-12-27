# Dockerfile for Fly.io deployment
# Completely rewritten to fix null byte issues and cache problems

FROM python:3.11-slim

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

# Copy requirements and clean null bytes in one step
COPY backend/requirements.txt /tmp/req_original.txt

# Clean null bytes and create clean requirements.txt
RUN python3 -c "import sys; d=open('/tmp/req_original.txt','rb').read(); c=d.replace(b'\x00',b''); open('requirements.txt','wb').write(c); print(f'Cleaned: {len(d)}->{len(c)}, removed {len(d)-len(c)} null bytes')"

# Verify no null bytes remain
RUN python3 -c "d=open('requirements.txt','rb').read(); assert b'\x00' not in d, 'Null bytes still present!'; print('Verified: No null bytes')"

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
