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

# Copy and clean requirements.txt in one step
COPY backend/requirements.txt /tmp/req.txt
RUN python3 -c "d=open('/tmp/req.txt','rb').read().replace(b'\x00',b''); open('requirements.txt','wb').write(d)" && \
    python3 -c "assert b'\x00' not in open('requirements.txt','rb').read(), 'Null bytes found'"

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create data directories
RUN mkdir -p /app/data/businesses /app/data/chromadb && chmod -R 755 /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
