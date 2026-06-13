# SAMAA — Complete CI/CD & Custom Domain Setup Guide

Automated deployment from GitHub to Oracle Cloud with custom domain, SSL, and zero-downtime updates.

---

## Architecture Overview

```
Developer → GitHub Push → GitHub Actions → Oracle Cloud VM
                                                ↓
                                         Nginx (SSL)
                                                ↓
                               Next.js ←→ FastAPI ←→ Celery
                               :3000        :8000      Worker
                                                ↓
                              Neon DB ←→ Upstash Redis ←→ Cloudflare R2
```

---

## Part 1: Custom Domain Setup

### Option A: Cloudflare DNS (Recommended)

#### 1. Add Domain to Cloudflare

1. Go to https://dash.cloudflare.com
2. Click **Add a Domain**
3. Enter your domain: `samaa.ai` (or your domain)
4. Cloudflare will scan your current DNS records
5. Update your domain's nameservers at your registrar to:
   - `ns1.cloudflare.com`
   - `ns2.cloudflare.com`
   - (Cloudflare will show exact nameservers)

#### 2. Create DNS Records

In Cloudflare dashboard:

**A Record** (points to Oracle VM):
```
Type: A
Name: @
Content: 155.248.245.21  (your Oracle VM public IP)
Proxy status: Proxied (orange cloud)
TTL: Auto
```

**A Record** (optional www subdomain):
```
Type: A
Name: www
Content: 155.248.245.21
Proxy status: Proxied
TTL: Auto
```

#### 3. Configure Cloudflare Settings

**SSL/TLS**:
- Go to **SSL/TLS** → **Overview**
- Set to **Full (strict)**

**SSL/TLS Edge Certificates**:
- Enable **Always Use HTTPS**
- Enable **Automatic HTTPS Rewrites**
- Enable **HSTS** (optional but recommended)

---

### Option B: Other DNS Providers

If using GoDaddy, Namecheap, etc.:

```
Type: A
Name: @
Value: 155.248.245.21
TTL: 3600
```

---

## Part 2: SSH Key Setup for GitHub Actions

### 1. Generate Deploy Key

On your **local machine**:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/samaa_deploy -N ""
```

This creates:
- `~/.ssh/samaa_deploy` (private key)
- `~/.ssh/samaa_deploy.pub` (public key)

### 2. Add Public Key to Oracle VM

SSH into your Oracle VM:

```bash
ssh -i <your-private-key> opc@155.248.245.21
```

Add the deploy key:

```bash
# Create .ssh directory if not exists
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add the public key (copy from your local machine)
nano ~/.ssh/authorized_keys

# Paste the content of ~/.ssh/samaa_deploy.pub from your local machine
# Save and exit

chmod 600 ~/.ssh/authorized_keys
```

Test the key from your local machine:

```bash
ssh -i ~/.ssh/samaa_deploy opc@155.248.245.21
# Should connect without password
```

### 3. Add Private Key to GitHub Secrets

1. Go to your GitHub repo: `https://github.com/userisaziz/xsamaa-ai-pipeline`
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `SSH_PRIVATE_KEY` | Content of `~/.ssh/samaa_deploy` |
| `SSH_HOST` | `155.248.245.21` |
| `SSH_USER` | `opc` |
| `SSH_PORT` | `22` |

---

## Part 3: GitHub Actions CI/CD Workflow

### 1. Create Workflow File

Create `.github/workflows/deploy.yml` in your repository:

```yaml
name: Deploy to Oracle Cloud

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
    types: [ closed ]

jobs:
  deploy:
    if: github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.pull_request.merged == true)
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

      - name: Add Oracle VM to known_hosts
        run: |
          mkdir -p ~/.ssh
          ssh-keyscan -H ${{ secrets.SSH_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy to Oracle Cloud
        run: |
          ssh -p ${{ secrets.SSH_PORT }} ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }} << 'EOF'
            set -e
            
            echo "🚀 Starting deployment..."
            
            # Navigate to app directory
            cd /home/opc/xsamaa-ai-pipeline
            
            # Pull latest changes
            echo "📦 Pulling latest code..."
            git pull origin main
            
            # Install dependencies
            echo "🔧 Installing dependencies..."
            cd apps/api
            source .venv/bin/activate
            uv pip install -e '.[prod]'
            
            cd ../web
            npm install
            npm run build
            
            cd ../..
            
            # Run database migrations
            echo "🗄️ Running migrations..."
            cd apps/api
            source .venv/bin/activate
            export $(cat ../../.env.prod | xargs)
            alembic upgrade head
            
            cd ../..
            
            # Restart services
            echo "🔄 Restarting services..."
            sudo systemctl restart samaa-api
            sudo systemctl restart samaa-celery
            sudo systemctl restart samaa-web
            
            # Check service health
            echo "✅ Checking service health..."
            sleep 5
            
            if systemctl is-active --quiet samaa-api; then
              echo "✅ FastAPI is running"
            else
              echo "❌ FastAPI failed to start"
              exit 1
            fi
            
            if systemctl is-active --quiet samaa-celery; then
              echo "✅ Celery is running"
            else
              echo "❌ Celery failed to start"
              exit 1
            fi
            
            if systemctl is-active --quiet samaa-web; then
              echo "✅ Next.js is running"
            else
              echo "❌ Next.js failed to start"
              exit 1
            fi
            
            echo "🎉 Deployment successful!"
            echo "🌐 Application: https://${{ vars.DOMAIN_NAME }}"
            echo "📝 API Docs: https://${{ vars.DOMAIN_NAME }}/docs"
          EOF

      - name: Notify on failure
        if: failure()
        run: |
          echo "❌ Deployment failed!"
          echo "Check GitHub Actions logs for details"
```

### 2. Add Repository Variables

In GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **Variables**:

| Variable Name | Value |
|---------------|-------|
| `DOMAIN_NAME` | `samaa.ai` (or your domain) |

---

## Part 4: Oracle VM Preparation

### 1. Clone Repository on VM

SSH into Oracle VM:

```bash
ssh -i <your-private-key> opc@155.248.245.21
```

Clone your repository:

```bash
cd ~
git clone https://github.com/userisaziz/xsamaa-ai-pipeline.git
cd xsamaa-ai-pipeline
```

### 2. Initial Setup (Run Once)

```bash
# Copy .env.prod to VM
# From your LOCAL machine:
scp -i <your-private-key> .env.prod opc@155.248.245.21:~/xsamaa-ai-pipeline/.env.prod

# On VM:
cd ~/xsamaa-ai-pipeline

# Install dependencies
cd apps/api
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[prod]'

cd ../web
npm install
npm run build

cd ../..

# Run migrations
cd apps/api
source .venv/bin/activate
export $(cat ../../.env.prod | xargs)
alembic upgrade head

cd ../..

# Create systemd services (from DEPLOYMENT_ORACLE_CLOUD.md)
# ... create the service files ...

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable samaa-api samaa-celery samaa-web
sudo systemctl start samaa-api samaa-celery samaa-web
```

---

## Part 5: SSL Certificate with Let's Encrypt

### 1. Install Certbot

SSH into Oracle VM:

```bash
sudo dnf install -y certbot python3-certbot-nginx
```

### 2. Obtain SSL Certificate

```bash
# Replace with your domain
sudo certbot --nginx -d samaa.ai -d www.samaa.ai
```

Follow the prompts:
- Enter email for renewal notifications
- Accept terms of service
- Choose whether to share email with EFF
- Certbot will automatically configure Nginx

### 3. Auto-Renewal Setup

Certbot creates a systemd timer automatically. Verify:

```bash
sudo systemctl status certbot-renew.timer
```

Test renewal:

```bash
sudo certbot renew --dry-run
```

---

## Part 6: Nginx Configuration with Custom Domain

### 1. Update Nginx Config

SSH into Oracle VM:

```bash
sudo nano /etc/nginx/conf.d/samaa.conf
```

```nginx
upstream frontend {
    server 127.0.0.1:3000;
}

upstream backend {
    server 127.0.0.1:8000;
}

# HTTP → HTTPS redirect
server {
    listen 80;
    server_name samaa.ai www.samaa.ai;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name samaa.ai www.samaa.ai;

    # SSL certificates (auto-configured by Certbot)
    ssl_certificate /etc/letsencrypt/live/samaa.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/samaa.ai/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Increase upload limit
    client_max_body_size 2G;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

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

    # WebSocket support
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. Test and Reload

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Part 7: Environment-Specific Configuration

### Update `.env.prod` for Production

```env
# ===========================================
# SAMAA Production Environment
# ===========================================

# --- Database (Neon) ---
DATABASE_URL=postgresql+asyncpg://neondb_owner:npg_zkJLNhnw0CZ5@ep-icy-meadow-aoscjaao-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
DATABASE_URL_SYNC=postgresql://neondb_owner:npg_zkJLNhnw0CZ5@ep-icy-meadow-aoscjaao-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

# --- Redis (Upstash) ---
UPSTASH_REDIS_REST_URL="https://calm-emu-73378.upstash.io"
UPSTASH_REDIS_REST_TOKEN="gQAAAAAAAR6iAAIgcDFhOTQzMmNmZDBkNzY0NDgwOTVmOTI0YmM5NGZiY2ZiZQ"
REDIS_URL=rediss://default:gQAAAAAAAR6iAAIgcDFhOTQzMmNmZDBkNzY0NDgwOTVmOTI0YmM5NGZiY2ZiZQ@calm-emu-73378.upstash.io:6379

# --- JWT ---
JWT_SECRET=<your-strong-secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# --- Storage (R2) ---
STORAGE_BACKEND=r2
R2_ACCOUNT_ID=42f6031dde7b1a28c26aa6815192b08d
R2_ACCESS_KEY_ID=870e8f6a829e4158c5799b2291a552e0
R2_SECRET_ACCESS_KEY=96f1b0bca1702151f6d94045611085c42802a7326fb296665cd6e46aed5bddc5
R2_BUCKET=cxsamaa-prod

# --- NVIDIA ---
NVIDIA_API_KEY=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
NVIDIA_STT_MODEL=parakeet-rnnt-1.1b
NVIDIA_DIARIZATION_MODEL=streusand-rnnt
NVIDIA_LLM_MODEL=meta/llama-3.3-70b-instruct

# --- Pyannote ---
DIARIZATION_USE_PYANNOTE=true
PYANNOTE_HF_TOKEN=hf_your_token_here
PYANNOTE_MODEL_NAME=pyannote/speaker-diarization-3.1

# --- Application ---
APP_ENV=production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000

# --- CORS (Update with your domain) ---
CORS_ORIGINS=https://samaa.ai,https://www.samaa.ai
```

---

## Part 8: Deployment Workflow

### Automated Deployment

1. **Push to main branch**:
```bash
git add .
git commit -m "feat: update feature"
git push origin main
```

2. **GitHub Actions automatically**:
   - Pulls latest code on Oracle VM
   - Installs dependencies
   - Runs database migrations
   - Restarts all services
   - Checks service health

3. **Monitor deployment**:
   - GitHub → Actions tab → View logs
   - Check deployment status

### Manual Deployment (if needed)

```bash
ssh -i ~/.ssh/samaa_deploy opc@155.248.245.21

cd ~/xsamaa-ai-pipeline
git pull origin main

# Restart services
sudo systemctl restart samaa-api samaa-celery samaa-web

# Check status
sudo systemctl status samaa-api samaa-celery samaa-web
```

---

## Part 9: Monitoring & Alerts

### 1. Service Monitoring

```bash
# Check all services
sudo systemctl status samaa-api samaa-celery samaa-web

# View logs
sudo journalctl -u samaa-api -f
sudo journalctl -u samaa-celery -f
sudo journalctl -u samaa-web -f

# Check memory
free -h
htop
```

### 2. Uptime Monitoring (Free)

**Option A: UptimeRobot**
1. Go to https://uptimerobot.com
2. Add monitor: `https://samaa.ai`
3. Check every 5 minutes
4. Get email/SMS alerts on downtime

**Option B: Better Stack**
1. Go to https://betterstack.com
2. Free tier: 10 monitors, 3-minute checks
3. Better alerting and incident management

### 3. Resource Monitoring

```bash
# Install monitoring tools
sudo dnf install -y htop iotop nethogs

# Monitor
htop          # CPU/Memory
iotop         # Disk I/O
nethogs       # Network usage
```

---

## Part 10: Backup Strategy

### 1. Database Backup (Neon handles this)

Neon provides:
- Automatic daily backups
- Point-in-time recovery
- 7-day retention (free tier)

### 2. Application Backup

Create backup script on Oracle VM:

```bash
nano ~/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/opc/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup .env.prod
cp ~/xsamaa-ai-pipeline/.env.prod $BACKUP_DIR/env_$DATE

# Backup Nginx config
sudo cp /etc/nginx/conf.d/samaa.conf $BACKUP_DIR/nginx_$DATE.conf

# Backup systemd services
sudo cp /etc/systemd/system/samaa-*.service $BACKUP_DIR/

# Keep only last 7 backups
find $BACKUP_DIR -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x ~/backup.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /home/opc/backup.sh
```

---

## Part 11: Security Hardening

### 1. Firewall Rules

```bash
# Only allow necessary ports
sudo firewall-cmd --permanent --remove-service=dhcpv6-client
sudo firewall-cmd --permanent --remove-service=cockpit
sudo firewall-cmd --reload
```

### 2. SSH Security

Edit `/etc/ssh/sshd_config`:

```bash
sudo nano /etc/ssh/sshd_config
```

```ini
Port 22
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

```bash
sudo systemctl restart sshd
```

### 3. Fail2Ban (Optional)

```bash
sudo dnf install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Checklist

### Pre-Deployment
- [ ] Domain purchased and pointed to Cloudflare (or registrar)
- [ ] DNS A record created pointing to Oracle VM IP
- [ ] SSH deploy key generated and added to Oracle VM
- [ ] SSH private key added to GitHub Secrets
- [ ] Repository cloned on Oracle VM
- [ ] `.env.prod` uploaded to Oracle VM
- [ ] All dependencies installed
- [ ] Database migrations run
- [ ] Systemd services created and enabled

### SSL & Nginx
- [ ] Certbot installed
- [ ] SSL certificate obtained
- [ ] Nginx configured with SSL
- [ ] HTTP → HTTPS redirect working
- [ ] Auto-renewal tested

### CI/CD
- [ ] `.github/workflows/deploy.yml` created
- [ ] GitHub secrets configured
- [ ] Test deployment triggered
- [ ] Deployment logs verified
- [ ] Services restarting correctly

### Post-Deployment
- [ ] Website accessible via `https://samaa.ai`
- [ ] API accessible via `https://samaa.ai/api/`
- [ ] API docs at `https://samaa.ai/docs`
- [ ] Audio upload working
- [ ] CORS configured correctly
- [ ] Monitoring setup (UptimeRobot)
- [ ] Backup script created and scheduled
- [ ] Security hardening applied

---

## Cost Summary

| Service | Cost |
|---------|------|
| Oracle Cloud VM | **FREE** |
| Neon PostgreSQL | **FREE** |
| Upstash Redis | **FREE** |
| Cloudflare R2 | **FREE** (first 10 GB) |
| Cloudflare DNS/SSL | **FREE** |
| GitHub Actions | **FREE** (2000 min/month) |
| Let's Encrypt SSL | **FREE** |
| **Total** | **$0/month** 🎉 |

---

## Troubleshooting

### Deployment Fails

```bash
# SSH into VM and check
ssh opc@155.248.245.21

# Check Git
cd ~/xsamaa-ai-pipeline
git status
git log --oneline -5

# Check services
sudo systemctl status samaa-api
sudo journalctl -u samaa-api -n 100 --no-pager
```

### SSL Certificate Issues

```bash
# Check certificate
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal

# Check Nginx config
sudo nginx -t
```

### Domain Not Resolving

```bash
# Check DNS
dig samaa.ai
nslookup samaa.ai

# Check Cloudflare DNS records
# Verify A record points to 155.248.245.21
```

---

**Ready to deploy?** Start with Part 1 (Custom Domain) and work through each section!
