# SAMAA — Oracle Cloud Free Tier Deployment Guide

Deploy the SAMAA AI pipeline to Oracle Cloud Always Free resources with zero cost.

---

## Oracle Cloud Free Tier Resources

**Always Free VM:**
- **Shape**: VM.Standard.E2.1.Micro (1 OCPU, 1 GB RAM) or VM.A1.Flex (4 OCPUs, 24 GB RAM - ARM)
- **Storage**: 200 GB block storage
- **Network**: 10 TB/month outbound bandwidth

**Recommendation**: Use **VM.A1.Flex (ARM)** with 2 OCPUs, 12 GB RAM for SAMAA (plenty for Docker + AI pipeline).

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Oracle Cloud VM (Always Free)                      │
│                                                     │
│  ┌─────────────┐    ┌─────────────┐                │
│  │   Nginx     │───▶│  Next.js    │                │
│  │  Port 80/443│    │  Port 3000  │                │
│  └─────────────┘    └──────┬──────┘                │
│                            │                        │
│                            ▼                        │
│                     ┌─────────────┐                │
│                     │  FastAPI    │                │
│                     │  Port 8000  │                │
│                     └──────┬──────┘                │
│                            │                        │
│          ┌─────────────────┼─────────────┐        │
│          ▼                 ▼             ▼        │
│   ┌────────────┐   ┌────────────┐  ┌──────────┐  │
│   │ PostgreSQL │   │   Celery   │  │  NVIDIA  │  │
│   │ (Docker)   │   │  Worker    │  │  APIs    │  │
│   └────────────┘   └────────────┘  └──────────┘  │
│                                                     │
│  External Services (Free Tier):                    │
│  • Neon PostgreSQL (database)                      │
│  • Upstash Redis (cache/queue)                     │
│  • Cloudflare R2 (file storage)                    │
└─────────────────────────────────────────────────────┘
```

---

## Step 1: Create Oracle Cloud Account

1. Go to https://www.oracle.com/cloud/free/
2. Sign up with credit card (required but not charged for free tier)
3. Choose your home region (closest to your users)
4. Wait for account activation (usually instant)

---

## Step 2: Create Compute Instance

### 2.1 Launch Instance

1. Navigate to **Compute → Instances**
2. Click **Create Instance**
3. Configure:
   - **Name**: `samaa-production`
   - **Compartment**: Root compartment
   - **Placement**: AD-1 (default)
   - **Image**: Ubuntu 24.04 or Oracle Linux 9
   - **Shape**: 
     - Click "Change shape"
     - Select **ARM** → `VM.Standard.A1.Flex`
     - **OCPUs**: 2
     - **Memory**: 12 GB
   - **Networking**: Create new VCN (or use existing)
   - **SSH Keys**: Download private key or paste your public key
4. Click **Create**

### 2.2 Configure Security List (Firewall)

1. Go to your instance details
2. Click the **Subnet** link
3. Click **Default Security List**
4. Add Ingress Rules:

| Source | Protocol | Port | Purpose |
|--------|----------|------|---------|
| 0.0.0.0/0 | TCP | 22 | SSH |
| 0.0.0.0/0 | TCP | 80 | HTTP |
| 0.0.0.0/0 | TCP | 443 | HTTPS |

### 2.3 Configure OS Firewall

SSH into your instance:
```bash
ssh -i <your-private-key> ubuntu@<public-ip>
```

For **Ubuntu**:
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

For **Oracle Linux**:
```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## Step 3: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3.12 + uv
sudo apt install -y python3.12 python3.12-venv python3.12-dev
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install Nginx
sudo apt install -y nginx

# Install ffmpeg (required for audio processing)
sudo apt install -y ffmpeg

# Verify installations
docker --version
docker compose version
node --version
python3 --version
uv --version
nginx -v
ffmpeg -version
```

---

## Step 4: Deploy Application

### 4.1 Clone Repository

```bash
cd ~
git clone https://github.com/your-username/xsamaa-ai-pipeline.git
cd xsamaa-ai-pipeline
```

### 4.2 Configure Environment

Create `.env.prod` with your production credentials:

```bash
nano .env.prod
```

```env
# ===========================================
# SAMAA Production Environment
# ===========================================

# --- Database (Neon PostgreSQL) ---
DATABASE_URL=postgresql+asyncpg://neondb_owner:npg_zkJLNhnw0CZ5@ep-icy-meadow-aoscjaao-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
DATABASE_URL_SYNC=postgresql://neondb_owner:npg_zkJLNhnw0CZ5@ep-icy-meadow-aoscjaao-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

# --- Redis (Upstash) ---
UPSTASH_REDIS_REST_URL="https://calm-emu-73378.upstash.io"
UPSTASH_REDIS_REST_TOKEN="gQAAAAAAAR6iAAIgcDFhOTQzMmNmZDBkNzY0NDgwOTVmOTI0YmM5NGZiY2ZiZQ"
REDIS_URL=rediss://default:gQAAAAAAAR6iAAIgcDFhOTQzMmNmZDBkNzY0NDgwOTVmOTI0YmM5NGZiY2ZiZQ@calm-emu-73378.upstash.io:6379

# --- JWT Authentication ---
JWT_SECRET=<generate-strong-secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# --- File Storage (Cloudflare R2) ---
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=<your-r2-access-key>
AWS_SECRET_ACCESS_KEY=<your-r2-secret-key>
AWS_S3_BUCKET=samaa-recordings
AWS_S3_REGION=auto
AWS_S3_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com

# --- NVIDIA NIM API ---
NVIDIA_API_KEY=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
NVIDIA_STT_MODEL=parakeet-rnnt-1.1b
NVIDIA_DIARIZATION_MODEL=streusand-rnnt
NVIDIA_LLM_MODEL=meta/llama-3.3-70b-instruct

# --- Pyannote.audio ---
DIARIZATION_USE_PYANNOTE=true
PYANNOTE_HF_TOKEN=hf_your_token_here
PYANNOTE_MODEL_NAME=pyannote/speaker-diarization-3.1

# --- Application ---
APP_ENV=production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000

# --- CORS ---
CORS_ORIGINS=https://your-domain.com
```

Generate a strong JWT secret:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4.3 Install Python Dependencies

```bash
cd apps/api
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[prod]'
```

### 4.4 Install Frontend Dependencies

```bash
cd ../..
npm install
```

### 4.5 Build Frontend

```bash
cd apps/web
npm run build
```

---

## Step 5: Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/samaa
```

```nginx
upstream frontend {
    server 127.0.0.1:3000;
}

upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    # Increase upload limit for audio files
    client_max_body_size 2G;

    # Frontend (Next.js)
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API (FastAPI)
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/samaa /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Step 6: Setup SSL with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Auto-renewal is configured automatically.

---

## Step 7: Create Systemd Services

### 7.1 FastAPI Service

```bash
sudo nano /etc/systemd/system/samaa-api.service
```

```ini
[Unit]
Description=SAMAA FastAPI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/xsamaa-ai-pipeline/apps/api
Environment=PATH=/home/ubuntu/xsamaa-ai-pipeline/apps/api/.venv/bin
ExecStart=/home/ubuntu/xsamaa-ai-pipeline/apps/api/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --env-file ../../.env.prod
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 7.2 Celery Worker Service

```bash
sudo nano /etc/systemd/system/samaa-celery.service
```

```ini
[Unit]
Description=SAMAA Celery Worker
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/xsamaa-ai-pipeline/apps/api
Environment=PATH=/home/ubuntu/xsamaa-ai-pipeline/apps/api/.venv/bin
ExecStart=/home/ubuntu/xsamaa-ai-pipeline/apps/api/.venv/bin/celery -A src.workers.celery_app worker --loglevel=info --pool=solo
EnvironmentFile=/home/ubuntu/xsamaa-ai-pipeline/.env.prod
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 7.3 Next.js Service

```bash
sudo nano /etc/systemd/system/samaa-web.service
```

```ini
[Unit]
Description=SAMAA Next.js Frontend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/xsamaa-ai-pipeline/apps/web
ExecStart=/usr/bin/node server.js
Environment=NODE_ENV=production
Environment=PORT=3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 7.4 Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable samaa-api samaa-celery samaa-web
sudo systemctl start samaa-api samaa-celery samaa-web

# Check status
sudo systemctl status samaa-api
sudo systemctl status samaa-celery
sudo systemctl status samaa-web
```

---

## Step 8: Run Database Migrations

```bash
cd ~/xsamaa-ai-pipeline/apps/api
source .venv/bin/activate
export $(cat ../../.env.prod | xargs)
alembic upgrade head
```

Seed initial data:
```bash
cd ~/xsamaa-ai-pipeline
bash seed.sh
```

---

## Step 9: Setup Monitoring

### 9.1 View Logs

```bash
# API logs
sudo journalctl -u samaa-api -f

# Celery logs
sudo journalctl -u samaa-celery -f

# Frontend logs
sudo journalctl -u samaa-web -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 9.2 Resource Monitoring

```bash
# Install htop
sudo apt install -y htop

# Monitor resources
htop
```

---

## Step 10: Backup Strategy

### 10.1 Automated Backups

Create backup script:
```bash
nano ~/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Export PostgreSQL data (if using local DB)
# docker exec samaa-postgres pg_dump -U samaa samaa > $BACKUP_DIR/db_$DATE.sql

# Backup uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz ~/xsamaa-ai-pipeline/apps/api/uploads/

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x ~/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/ubuntu/backup.sh
```

---

## Deployment Verification Checklist

- [ ] VM running with Oracle Cloud Free Tier
- [ ] Docker installed and running
- [ ] Node.js 20+ installed
- [ ] Python 3.12 + uv installed
- [ ] Nginx configured and running
- [ ] SSL certificate installed
- [ ] `.env.prod` configured with production credentials
- [ ] Database migrations completed
- [ ] FastAPI running on port 8000
- [ ] Celery worker processing tasks
- [ ] Next.js running on port 3000
- [ ] Application accessible via https://your-domain.com
- [ ] Audio upload working (test with sample file)
- [ ] AI pipeline processing correctly (check logs)
- [ ] Monitoring and backups configured

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u samaa-api -n 100 --no-pager

# Restart service
sudo systemctl restart samaa-api
```

### Database Connection Issues

```bash
# Test connection
cd apps/api
source .venv/bin/activate
python -c "from src.database import engine; print('Connected!')"
```

### Celery Worker Not Processing

```bash
# Check Redis connection
curl -X GET "https://calm-emu-73378.upstash.io/ping" -H "Authorization: Bearer gQAAAAAAAR6iAAIgcDFhOTQzMmNmZDBkNzY0NDgwOTVmOTI0YmM5NGZiY2ZiZQ"

# Restart worker
sudo systemctl restart samaa-celery
```

### High Memory Usage

```bash
# Check memory
free -h
docker stats

# If needed, reduce worker concurrency or increase swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Cost Summary

| Resource | Cost |
|----------|------|
| Oracle Cloud VM (ARM, 2 OCPU, 12 GB) | **FREE** (Always Free) |
| Neon PostgreSQL | **FREE** (Free tier) |
| Upstash Redis | **FREE** (Free tier) |
| Cloudflare R2 | **FREE** (First 10 GB) |
| Let's Encrypt SSL | **FREE** |
| **Total** | **$0/month** 🎉 |

---

## Next Steps

1. **Domain Setup**: Point your domain to Oracle Cloud public IP
2. **Monitoring**: Setup uptime monitoring (UptimeRobot, Better Stack)
3. **CDN**: Add Cloudflare CDN for better performance
4. **Scaling**: Monitor resource usage and upgrade if needed
5. **Security**: Enable Oracle Cloud WAF, setup fail2ban

---

**Need help?** Check the logs or run `sudo journalctl -u <service> -f` for real-time debugging.
