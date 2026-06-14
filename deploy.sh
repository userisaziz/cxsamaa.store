#!/usr/bin/env bash
# ============================================
# SAMAA — Production Deploy to Oracle Cloud
# ============================================
# Domain: cxsamaa.store
# VM:     92.4.87.24 (Oracle Cloud, 1GB RAM)
# Stack:  Neon PostgreSQL + Upstash Redis + R2
# Memory: ~740MB app + 2GB swap safety net
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SSH_KEY="/Users/almabetter/Downloads/ssh-key-2026-06-14.key"
SSH_USER="ubuntu"
SSH_HOST="92.4.87.24"
REMOTE_DIR="/home/ubuntu/samaa-ai"
DOMAIN="cxsamaa.store"

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   SAMAA Production Deploy (1GB)      ║${NC}"
echo -e "${BLUE}║   Domain: ${DOMAIN}             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# --- Step 1: Verify prerequisites ---
echo -e "${YELLOW}[1/7] Verifying prerequisites...${NC}"

if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}  ✗ SSH key not found: $SSH_KEY${NC}"
    exit 1
fi

if [ ! -f ".env.prod" ]; then
    echo -e "${RED}  ✗ .env.prod not found in current directory${NC}"
    exit 1
fi

chmod 600 "$SSH_KEY"
echo -e "${GREEN}  ✓ Prerequisites verified${NC}"
echo ""

# --- Step 2: Test SSH connection ---
echo -e "${YELLOW}[2/7] Testing SSH connection...${NC}"

if ! ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 "$SSH_USER@$SSH_HOST" "echo 'SSH OK'" 2>/dev/null; then
    echo -e "${RED}  ✗ SSH connection failed to $SSH_HOST${NC}"
    echo -e "${RED}    Check: VM running? SSH ingress rule? Firewall?${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ SSH connection works${NC}"
echo ""

# --- Step 3: Create remote directory ---
echo -e "${YELLOW}[3/7] Preparing remote directory...${NC}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" "mkdir -p $REMOTE_DIR"
echo -e "${GREEN}  ✓ Remote directory ready${NC}"
echo ""

# --- Step 4: Upload code ---
echo -e "${YELLOW}[4/7] Uploading code to VM...${NC}"
echo "  This may take a few minutes..."

rsync -avz --delete \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='.next' \
    --exclude='__pycache__' \
    --exclude='.DS_Store' \
    --exclude='htmlcov' \
    --exclude='.coverage' \
    --exclude='.pytest_cache' \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    ./ "$SSH_USER@$SSH_HOST:$REMOTE_DIR/"

echo -e "${GREEN}  ✓ Code uploaded${NC}"
echo ""

# --- Step 5: Upload .env.prod ---
echo -e "${YELLOW}[5/7] Uploading .env.prod...${NC}"

scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    .env.prod "$SSH_USER@$SSH_HOST:$REMOTE_DIR/.env.prod"

echo -e "${GREEN}  ✓ .env.prod uploaded${NC}"
echo ""

# --- Step 6: Install dependencies and build ---
echo -e "${YELLOW}[6/7] Installing dependencies & building...${NC}"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" << 'ENDSSH'
set -e
cd /home/ubuntu/samaa-ai

echo "════════════════════════════════════════"
echo "  Building Application (1GB VM)"
echo "════════════════════════════════════════"
echo ""

# Memory check
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_FREE=$(free -m | awk '/^Mem:/{print $7}')
echo "  Memory: ${MEM_TOTAL}MB total, ${MEM_FREE}MB free"

# Setup 2GB swap if not already configured
if [ "$(swapon --show | wc -l)" -eq 0 ]; then
    echo ""
    echo "  Creating 2GB swap file..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
    echo 10 | sudo tee /proc/sys/vm/swappiness
    echo "  ✓ Swap enabled (2GB)"
fi
echo ""

# Backend setup
echo "Setting up Backend..."
cd apps/api

if ! command -v uv &> /dev/null; then
    echo "  Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "  ✓ uv installed"
fi

if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    uv venv .venv
fi

source .venv/bin/activate

echo "  Installing Python dependencies..."
uv pip install -e '.[prod]' --quiet 2>/dev/null || uv pip install -e . --quiet
echo "  ✓ Backend ready"
echo ""

# Run migrations
echo "Running database migrations..."
set -a
grep -v '^\s*#' /home/ubuntu/samaa-ai/.env.prod | grep -v '^\s*$' | while IFS='=' read -r key value; do
    export "$key=$value" 2>/dev/null || true
done
set +a

if [[ "${DATABASE_URL:-}" == *"YOUR_"* ]] || [[ -z "${DATABASE_URL:-}" ]]; then
    echo "  ⚠ DATABASE_URL not set — skipping migrations"
else
    alembic upgrade head 2>&1 | sed 's/^/  /' || echo "  (Migration failed — continuing)"
fi
echo ""

# Frontend setup
echo "Setting up Frontend..."
cd ../web

if ! command -v node &> /dev/null; then
    echo "  Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo "  ✓ Node.js installed: $(node --version)"
fi

echo "  Installing Node.js dependencies..."
npm ci --prefer-offline --no-audit --quiet 2>/dev/null || npm install --quiet

echo "  Building Next.js (standalone mode)..."
npm run build 2>&1 | tail -10

# Copy static + public into standalone
mkdir -p .next/standalone/.next/static
cp -r .next/static/* .next/standalone/.next/static/
if [ -d "public" ]; then
    mkdir -p .next/standalone/public
    cp -r public/* .next/standalone/public/
fi

echo "  ✓ Frontend built (standalone, ~50MB runtime)"
echo ""

cd ../..
echo "  ✅ Build Complete!"
ENDSSH

echo -e "${GREEN}  ✓ Build successful${NC}"
echo ""

# --- Step 7: Setup systemd services, Nginx & restart ---
echo -e "${YELLOW}[7/7] Setting up services, Nginx & restarting...${NC}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" << 'ENDSSH'
set -e

# ── Systemd services (1GB optimized) ──
echo "Creating/updating systemd services..."

# FastAPI — 256MB max
sudo tee /etc/systemd/system/samaa-api.service > /dev/null << 'EOF'
[Unit]
Description=SAMAA FastAPI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/samaa-ai/apps/api
Environment=PATH=/home/ubuntu/samaa-ai/apps/api/.venv/bin
ExecStart=/home/ubuntu/samaa-ai/apps/api/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000 --env-file ../../.env.prod --workers 1 --limit-concurrency 10 --limit-max-requests 1000
Restart=always
RestartSec=5
MemoryMax=256M
MemoryHigh=200M

[Install]
WantedBy=multi-user.target
EOF

# Celery — 384MB max (solo pool, no torch loaded)
sudo tee /etc/systemd/system/samaa-celery.service > /dev/null << 'EOF'
[Unit]
Description=SAMAA Celery Worker
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/samaa-ai/apps/api
Environment=PATH=/home/ubuntu/samaa-ai/apps/api/.venv/bin
ExecStart=/home/ubuntu/samaa-ai/apps/api/.venv/bin/celery -A src.workers.celery_app worker --loglevel=info --pool=solo --concurrency=1 --max-tasks-per-child=10
EnvironmentFile=/home/ubuntu/samaa-ai/.env.prod
Restart=always
RestartSec=5
MemoryMax=384M
MemoryHigh=320M

[Install]
WantedBy=multi-user.target
EOF

# Next.js — 100MB max (standalone)
sudo tee /etc/systemd/system/samaa-web.service > /dev/null << 'EOF'
[Unit]
Description=SAMAA Next.js Frontend (Standalone)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/samaa-ai/apps/web/.next/standalone
ExecStart=/usr/bin/node apps/web/server.js
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=HOSTNAME=0.0.0.0
Restart=always
RestartSec=5
MemoryMax=100M
MemoryHigh=80M

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable samaa-api samaa-celery samaa-web
echo "✓ Services created (API=256M, Celery=384M, Web=100M)"

# ── Nginx ──
echo ""
echo "Configuring Nginx..."

sudo tee /etc/nginx/conf.d/samaa.conf > /dev/null << 'EOF'
upstream samaa_frontend {
    server 127.0.0.1:3000;
}
upstream samaa_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    listen [::]:80;
    server_name cxsamaa.store www.cxsamaa.store;
    client_max_body_size 500M;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://samaa_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }

    location /api/ {
        proxy_pass http://samaa_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /docs {
        proxy_pass http://samaa_backend;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://samaa_backend;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://samaa_backend;
        proxy_set_header Host $host;
    }
}

# Catch-all for direct IP access
server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 500M;

    location / {
        proxy_pass http://samaa_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }

    location /api/ {
        proxy_pass http://samaa_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /docs {
        proxy_pass http://samaa_backend;
    }

    location /health {
        proxy_pass http://samaa_backend;
    }
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

if sudo nginx -t 2>&1; then
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    echo "✓ Nginx configured"
else
    echo "✗ Nginx config test failed!"
fi

# Install certbot for SSL
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq certbot python3-certbot-nginx
    echo "✓ Certbot installed"
fi

# ── Restart services ──
echo ""
echo "Restarting services..."
for service in samaa-api samaa-celery samaa-web; do
    sudo systemctl restart $service 2>/dev/null || echo "  ⚠ Failed to restart $service"
    sleep 2
    status=$(systemctl is-active $service 2>/dev/null)
    if [ "$status" = "active" ]; then
        echo "  ✅ $service: running"
    else
        echo "  ❌ $service: $status"
        sudo journalctl -u $service -n 5 --no-pager
    fi
done

echo ""
echo "Waiting 5s for services to stabilize..."
sleep 5

# Health checks
echo "Checking health..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null || echo "000")
if [ "$HEALTH" = "200" ]; then
    echo "  ✅ API: healthy (HTTP 200)"
else
    echo "  ⚠ API: HTTP $HEALTH (check logs)"
fi

WEB=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000 2>/dev/null || echo "000")
if [ "$WEB" = "200" ]; then
    echo "  ✅ Web: healthy (HTTP 200)"
else
    echo "  ⚠ Web: HTTP $WEB (check logs)"
fi

# SSL setup
echo ""
echo "Setting up SSL certificate..."
if command -v certbot &> /dev/null; then
    if [ -d "/etc/letsencrypt/live/cxsamaa.store" ]; then
        echo "  SSL certificate already exists, renewing..."
        sudo certbot renew --quiet 2>/dev/null || echo "  Renewal check complete"
    else
        echo "  Requesting new SSL certificate for cxsamaa.store..."
        sudo certbot --nginx -d cxsamaa.store -d www.cxsamaa.store --non-interactive --agree-tos --email admin@cxsamaa.store --redirect 2>&1 | sed 's/^/  /' || {
            echo ""
            echo "  NOTE: SSL setup requires DNS to be pointed first."
            echo "  Point cxsamaa.store A record to 92.4.87.24, then run:"
            echo "    sudo certbot --nginx -d cxsamaa.store -d www.cxsamaa.store"
        }
    fi
else
    echo "  Certbot not available — skipping SSL"
fi

echo ""
echo "════════════════════════════════════════"
echo "  Memory Budget (1GB VM):"
echo "    API:     256MB (FastAPI + uvicorn)"
echo "    Celery:  384MB (solo pool, no torch)"
echo "    Web:     100MB (Next.js standalone)"
echo "    Nginx:   ~20MB"
echo "    Total:   ~760MB + 2GB swap safety"
echo "════════════════════════════════════════"
ENDSSH

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Deployment Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Domain:${NC}    https://${DOMAIN}"
echo -e "  ${BLUE}Frontend:${NC}  http://${DOMAIN}  (HTTPS after SSL)"
echo -e "  ${BLUE}API Docs:${NC}  http://${DOMAIN}/docs"
echo -e "  ${BLUE}Health:${NC}    http://${DOMAIN}/health"
echo ""
echo -e "${YELLOW}DNS Setup (required for SSL):${NC}"
echo "  Add this A record in your domain registrar:"
echo "    Type: A"
echo "    Name: @  (or cxsamaa.store)"
echo "    Value: ${SSH_HOST}"
echo "    TTL: 300"
echo ""
echo "  For www subdomain:"
echo "    Type: A"
echo "    Name: www"
echo "    Value: ${SSH_HOST}"
echo "    TTL: 300"
echo ""
echo -e "${YELLOW}After DNS propagates, run SSL:${NC}"
echo "  ssh -i '$SSH_KEY' $SSH_USER@$SSH_HOST"
echo "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo ""
echo -e "${BLUE}SSH Commands:${NC}"
echo "  Connect:  ssh -i '$SSH_KEY' $SSH_USER@$SSH_HOST"
echo "  Logs:     ssh -i '$SSH_KEY' $SSH_USER@$SSH_HOST 'sudo journalctl -u samaa-api -f'"
echo "  Status:   ssh -i '$SSH_KEY' $SSH_USER@$SSH_HOST 'systemctl status samaa-api samaa-celery samaa-web'"
echo ""
