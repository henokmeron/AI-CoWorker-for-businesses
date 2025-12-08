# Deployment Guide

This guide covers various deployment options for the AI Assistant Coworker.

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Platforms](#cloud-platforms)
4. [VPS Deployment](#vps-deployment)
5. [Production Checklist](#production-checklist)

---

## Local Development

Best for: Testing and development

### Setup

```bash
# 1. Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Install frontend dependencies
cd ../frontend
pip install -r requirements.txt

# 3. Configure environment
cp env.example.txt .env
# Edit .env and add your API keys

# 4. Run backend
cd backend
python main.py

# 5. Run frontend (new terminal)
cd frontend
streamlit run streamlit_app.py
```

### Access
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Docker Deployment

Best for: Easy deployment and sharing

### Prerequisites
- Docker Desktop installed
- Docker Compose installed

### Quick Start

```bash
# 1. Configure environment
cp env.example.txt .env
# Edit .env with your settings

# 2. Start all services
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Stop services
docker-compose down
```

### Access
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- ChromaDB: http://localhost:8001

### Troubleshooting

```bash
# Rebuild after code changes
docker-compose up -d --build

# View specific service logs
docker-compose logs backend
docker-compose logs frontend

# Restart a service
docker-compose restart backend

# Remove all containers and volumes
docker-compose down -v
```

---

## Cloud Platforms

### Option 1: Railway (Easiest)

Railway automatically detects and deploys Dockerized apps.

#### Steps:

1. **Create account at railway.app**

2. **Create new project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your repository

3. **Configure services**

   **Backend Service:**
   - Detects `backend/Dockerfile`
   - Set environment variables:
     ```
     OPENAI_API_KEY=your-key
     API_HOST=0.0.0.0
     API_PORT=8000
     ```
   - Railway assigns a public URL

   **Frontend Service:**
   - Detects `frontend/Dockerfile`
   - Set environment variables:
     ```
     BACKEND_URL=https://your-backend-url.railway.app
     API_KEY=your-api-key
     ```

4. **Deploy**
   - Railway auto-deploys on git push
   - Get your public URLs

**Cost:** ~$5-20/month depending on usage

---

### Option 2: Render

Similar to Railway, great for Docker deployments.

#### Steps:

1. **Create account at render.com**

2. **Create Web Services**

   **Backend:**
   - New → Web Service
   - Connect GitHub repo
   - Docker environment
   - Set environment variables
   - Deploy

   **Frontend:**
   - New → Web Service
   - Connect GitHub repo
   - Docker environment
   - Set `BACKEND_URL` to backend service URL
   - Deploy

3. **Set up Database** (Optional)
   - Add PostgreSQL for metadata storage
   - Add Redis for caching

**Cost:** Free tier available, paid starts at $7/month

---

### Option 3: Fly.io

Great for global deployment with edge locations.

#### Steps:

```bash
# 1. Install flyctl
curl -L https://fly.io/install.sh | sh

# 2. Login
flyctl auth login

# 3. Deploy backend
cd backend
flyctl launch
# Follow prompts, select region
flyctl deploy

# 4. Deploy frontend
cd ../frontend
flyctl launch
# Set BACKEND_URL to backend app URL
flyctl deploy
```

**Cost:** Free tier includes 3 VMs

---

### Option 4: Vercel (Frontend) + Railway (Backend)

Best for: Fast frontend, scalable backend

#### Steps:

1. **Deploy Backend on Railway** (see above)

2. **Deploy Frontend on Vercel:**
   - Create `vercel.json`:
     ```json
     {
       "buildCommand": "pip install -r requirements.txt",
       "devCommand": "streamlit run streamlit_app.py",
       "installCommand": "pip install -r requirements.txt"
     }
     ```
   - Connect GitHub repo
   - Set environment variables
   - Deploy

---

## VPS Deployment

Best for: Full control and customization

### Prerequisites
- Ubuntu 22.04 server
- SSH access
- Domain name (optional)

### Setup

```bash
# 1. Connect to server
ssh user@your-server-ip

# 2. Update system
sudo apt update && sudo apt upgrade -y

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 4. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. Clone repository
git clone https://github.com/your-repo/ai-assistant.git
cd ai-assistant

# 6. Configure environment
cp env.example.txt .env
nano .env  # Edit with your settings

# 7. Start services
docker-compose up -d

# 8. Install Nginx (reverse proxy)
sudo apt install nginx -y

# 9. Configure Nginx
sudo nano /etc/nginx/sites-available/ai-assistant
```

**Nginx Configuration:**

```nginx
# Backend
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Frontend
server {
    listen 80;
    server_name app.yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ai-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 10. Install SSL (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d app.yourdomain.com -d api.yourdomain.com
```

### Auto-restart on Boot

```bash
# Docker Compose auto-start
sudo systemctl enable docker

# Update docker-compose.yml services with:
# restart: unless-stopped
```

---

## Production Checklist

### Security
- [ ] Change default API key in .env
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall (UFW/Security Groups)
- [ ] Set strong SECRET_KEY
- [ ] Enable rate limiting
- [ ] Regular security updates

### Performance
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure logging
- [ ] Set up backups (database + files)
- [ ] Enable caching (Redis)
- [ ] Optimize chunk sizes
- [ ] Use production LLM models

### Reliability
- [ ] Set up health checks
- [ ] Configure auto-restart
- [ ] Set up alerting
- [ ] Plan for scaling
- [ ] Document recovery procedures

### Monitoring

```bash
# View Docker logs
docker-compose logs -f

# Check resource usage
docker stats

# Monitor disk space
df -h

# Check memory
free -h
```

### Backup Strategy

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backups/ai-assistant-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup data directory
cp -r ./data $BACKUP_DIR/

# Backup .env
cp .env $BACKUP_DIR/

# Create archive
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Upload to S3 (optional)
# aws s3 cp $BACKUP_DIR.tar.gz s3://your-bucket/backups/
```

---

## Scaling

### Horizontal Scaling

1. **Load Balancer Setup:**
   - Nginx or cloud load balancer
   - Multiple backend instances
   - Shared vector database (Qdrant/Pinecone)

2. **Database Migration:**
   - PostgreSQL for metadata
   - Cloud vector DB (Qdrant Cloud/Pinecone)
   - S3/Cloud storage for files

3. **Caching Layer:**
   - Redis for query caching
   - CDN for static files

### Vertical Scaling

- Increase server resources
- Optimize chunk sizes
- Use faster embedding models
- Enable GPU for local LLMs

---

## Cost Estimates

### Small Deployment (1-10 businesses)
- **VPS:** $5-10/month (DigitalOcean/Linode)
- **OpenAI API:** $10-50/month
- **Total:** $15-60/month

### Medium Deployment (10-100 businesses)
- **Cloud Platform:** $20-50/month
- **OpenAI API:** $50-200/month
- **Vector DB:** $0-30/month
- **Total:** $70-280/month

### Large Deployment (100+ businesses)
- **Multi-server:** $100-500/month
- **OpenAI API:** $200-1000/month
- **Vector DB:** $50-200/month
- **CDN/Cache:** $20-100/month
- **Total:** $370-1800/month

---

## Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Verify environment variables
3. Check API documentation: `/docs`
4. Review error messages in browser console

