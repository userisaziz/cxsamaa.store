#!/bin/bash

# ============================================
# SAMAA - Complete Oracle Cloud Setup Script
# ============================================
# Just run: bash setup-oracle.sh
# ============================================

set -e

ORACLE_IP="92.4.68.96"
ORACLE_USER="opc"
REPO_URL="https://github.com/userisaziz/xsamaa-ai-pipeline.git"

echo "════════════════════════════════════════"
echo "  🚀 SAMAA Oracle Cloud Setup"
echo "════════════════════════════════════════"
echo ""

# Step 1: Test SSH connection
echo "📋 Step 1: Testing SSH connection..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/samaa_deploy $ORACLE_USER@$ORACLE_IP "echo '✅ SSH connection works!'"
echo ""

# Step 2: Install system dependencies (need git first!)
echo "🔧 Step 2: Installing system dependencies (this takes 5-10 minutes)..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/samaa_deploy $ORACLE_USER@$ORACLE_IP << 'REMOTE_SCRIPT'
set -e

# Create swap space (critical for 1GB RAM!)
if [ ! -f /swapfile ]; then
    echo "Creating swap space..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✅ Swap created"
else
    echo "✅ Swap already exists"
fi

# Update system
echo "Updating system packages..."
sudo dnf update -y -q

# Install essentials (including git!)
echo "Installing dependencies..."
sudo dnf install -y git wget curl gcc make openssl-devel nginx ffmpeg

# Install Node.js 20
if ! command -v node &> /dev/null; then
    echo "Installing Node.js 20..."
    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
    sudo dnf install -y nodejs
    echo "✅ Node.js installed"
else
    echo "✅ Node.js already installed"
fi

# Install Python 3.12
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3.12..."
    sudo dnf install -y python3.12 python3.12-devel
    echo "✅ Python installed"
else
    echo "✅ Python already installed"
fi

# Install uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    source ~/.bashrc
    echo "✅ uv installed"
else
    echo "✅ uv already installed"
fi

# Configure firewall
sudo firewall-cmd --permanent --add-service=ssh 2>/dev/null || true
sudo firewall-cmd --permanent --add-service=http 2>/dev/null || true
sudo firewall-cmd --permanent --add-service=https 2>/dev/null || true
sudo firewall-cmd --reload 2>/dev/null || true

# Verify
echo ""
echo "📊 Installed versions:"
echo "  Node.js: $(node --version)"
echo "  Python: $(python3 --version)"
echo "  Git: $(git --version)"
echo "  uv: $(uv --version)"
echo "  Nginx: $(nginx -v 2>&1 | cut -d'/' -f2)"

echo "✅ All system dependencies installed"

REMOTE_SCRIPT
echo ""

# Step 3: Clone repository (now that git is installed)
echo "📦 Step 3: Setting up repository on Oracle VM..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/samaa_deploy $ORACLE_USER@$ORACLE_IP << 'REMOTE_SCRIPT'
set -e

export PATH="$HOME/.local/bin:$PATH"

cd ~

# Clone if not exists
if [ ! -d "xsamaa-ai-pipeline" ]; then
    echo "Cloning repository..."
    git clone https://github.com/userisaziz/xsamaa-ai-pipeline.git
    echo "✅ Repository cloned"
else
    echo "✅ Repository already exists"
    cd xsamaa-ai-pipeline
    git pull origin main 2>/dev/null || echo "Note: Pull failed (might be first setup)"
fi

# Create uploads directory
mkdir -p ~/xsamaa-ai-pipeline/apps/api/uploads

REMOTE_SCRIPT
echo ""

# Step 4: Copy .env.prod (now that repo exists)
echo "📝 Step 4: Uploading .env.prod..."
scp -o StrictHostKeyChecking=no .env.prod $ORACLE_USER@$ORACLE_IP:~/xsamaa-ai-pipeline/.env.prod
echo "✅ .env.prod uploaded"
echo ""

# Step 5: Install Python dependencies and build
echo "🐍 Step 5: Installing Python dependencies and building frontend..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/samaa_deploy $ORACLE_USER@$ORACLE_IP << 'REMOTE_SCRIPT'
set -e

export PATH="$HOME/.local/bin:$PATH"

cd ~/xsamaa-ai-pipeline

# Setup Python venv and install dependencies
cd apps/api
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
    echo "✅ Venv created"
fi

echo "Installing Python dependencies..."
uv pip install -e .
echo "✅ Python dependencies installed"

# Build frontend
echo ""
echo "Building Next.js frontend..."
cd ../web
if [ ! -d "node_modules" ]; then
    npm install
    npm run build
    echo "✅ Frontend built"
else
    echo "✅ Frontend already built"
    npm run build
fi

cd ../..

REMOTE_SCRIPT
echo ""

# Step 6: Run database migrations
echo "🗄️ Step 6: Running database migrations..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/samaa_deploy $ORACLE_USER@$ORACLE_IP << 'REMOTE_SCRIPT'
set -e

cd ~/xsamaa-ai-pipeline/apps/api
source .venv/bin/activate
export $(cat ../../.env.prod | xargs)

alembic upgrade head
echo "✅ Migrations complete"

REMOTE_SCRIPT
echo ""

# Step 7: Create systemd services
echo "⚙️  Step 7: Creating systemd services..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/samaa_deploy $ORACLE_USER@$ORACLE_IP << 'REMOTE_SCRIPT'
set -e

# FastAPI service
sudo tee /etc/systemd/system/samaa-api.service > /dev/null << 'EOF'
[Unit]
Description=SAMAA FastAPI Backend
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=/home/opc/xsamaa-ai-pipeline/apps/api
Environment=PATH=/home/opc/xsamaa-ai-pipeline/apps/api/.venv/bin
ExecStart=/home/opc/xsamaa-ai-pipeline/apps/api/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --env-file ../../.env.prod --workers 1
Restart=always
RestartSec=5
MemoryMax=400M

[Install]
WantedBy=multi-user.target
EOF

# Celery service
sudo tee /etc/systemd/system/samaa-celery.service > /dev/null << 'EOF'
[Unit]
Description=SAMAA Celery Worker
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=/home/opc/xsamaa-ai-pipeline/apps/api
Environment=PATH=/home/opc/xsamaa-ai-pipeline/apps/api/.venv/bin
ExecStart=/home/opc/xsamaa-ai-pipeline/apps/api/.venv/bin/celery -A src.workers.celery_app worker --loglevel=info --pool=solo --concurrency=1
EnvironmentFile=/home/opc/xsamaa-ai-pipeline/.env.prod
Restart=always
RestartSec=5
MemoryMax=300M

[Install]
WantedBy=multi-user.target
EOF

# Next.js service
sudo tee /etc/systemd/system/samaa-web.service > /dev/null << 'EOF'
[Unit]
Description=SAMAA Next.js Frontend
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=/home/opc/xsamaa-ai-pipeline/apps/web
ExecStart=/usr/bin/node server.js
Environment=NODE_ENV=production
Environment=PORT=3000
Restart=always
RestartSec=5
MemoryMax=300M

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd services created"

REMOTE_SCRIPT
echo ""

# Step 8: Configure Nginx
echo "🌐 Step 8: Configuring Nginx..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/samaa_deploy $ORACLE_USER@$ORACLE_IP << 'REMOTE_SCRIPT'
set -e

sudo tee /etc/nginx/conf.d/samaa.conf > /dev/null << 'EOF'
upstream frontend {
    server 127.0.0.1:3000;
}

upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 2G;

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

    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Test and start
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl start nginx

echo "✅ Nginx configured and started"

REMOTE_SCRIPT
echo ""

# Step 9: Start all services
echo "🚀 Step 9: Starting all services..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/samaa_deploy $ORACLE_USER@$ORACLE_IP << 'REMOTE_SCRIPT'
set -e

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable samaa-api samaa-celery samaa-web

# Start one by one
echo "Starting FastAPI..."
sudo systemctl start samaa-api
sleep 5

echo "Starting Celery..."
sudo systemctl start samaa-celery
sleep 5

echo "Starting Next.js..."
sudo systemctl start samaa-web
sleep 5

# Check status
echo ""
echo "📊 Service Status:"
for service in samaa-api samaa-celery samaa-web; do
    if systemctl is-active --quiet $service; then
        echo "  ✅ $service is running"
    else
        echo "  ❌ $service failed"
    fi
done

REMOTE_SCRIPT
echo ""

# Step 10: Test endpoints
echo "🧪 Step 10: Testing endpoints..."
sleep 3

API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://$ORACLE_IP:8000/health 2>/dev/null || echo "000")
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$ORACLE_IP:3000 2>/dev/null || echo "000")

if [ "$API_HEALTH" = "200" ]; then
    echo "  ✅ FastAPI: Running (http://$ORACLE_IP:8000/health)"
else
    echo "  ⚠️  FastAPI: Status $API_HEALTH (might need a moment to start)"
fi

if [ "$WEB_STATUS" = "200" ]; then
    echo "  ✅ Next.js: Running (http://$ORACLE_IP:3000)"
else
    echo "  ⚠️  Next.js: Status $WEB_STATUS (might need a moment to start)"
fi

echo ""
echo "════════════════════════════════════════"
echo "  🎉 Setup Complete!"
echo "════════════════════════════════════════"
echo ""
echo "📍 Access your application:"
echo "   API:     http://$ORACLE_IP:8000"
echo "   Web:     http://$ORACLE_IP:3000"
echo "   API Docs: http://$ORACLE_IP:8000/docs"
echo ""
echo "📝 Next steps:"
echo "   1. Add GitHub secrets (see CI_CD_DEPLOYMENT_GUIDE.md)"
echo "   2. Setup custom domain (Cloudflare DNS)"
echo "   3. Push to main to trigger auto-deployment!"
echo ""
