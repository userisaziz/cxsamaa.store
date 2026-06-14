#!/usr/bin/env bash
# ============================================
# SAMAA — Quick Deploy Script
# ============================================
# Uploads code and deploys to Oracle VM
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
REMOTE_DIR="/home/ubuntu/xsamaa-ai-pipeline"

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   SAMAA Quick Deployment             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# --- Step 1: Verify prerequisites ---
echo -e "${YELLOW}[1/6] Verifying prerequisites...${NC}"

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

# --- Step 2: Create remote directory ---
echo -e "${YELLOW}[2/6] Preparing remote directory...${NC}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" "mkdir -p $REMOTE_DIR"
echo -e "${GREEN}  ✓ Remote directory ready${NC}"
echo ""

# --- Step 3: Upload code ---
echo -e "${YELLOW}[3/6] Uploading code to VM...${NC}"
echo "  This may take a few minutes..."

# Upload everything except node_modules, .venv, and .git
rsync -avz --delete \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='.next' \
    --exclude='__pycache__' \
    --exclude='.DS_Store' \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    ./ "$SSH_USER@$SSH_HOST:$REMOTE_DIR/"

echo -e "${GREEN}  ✓ Code uploaded${NC}"
echo ""

# --- Step 4: Upload .env.prod ---
echo -e "${YELLOW}[4/6] Uploading .env.prod...${NC}"

scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    .env.prod "$SSH_USER@$SSH_HOST:$REMOTE_DIR/.env.prod"

echo -e "${GREEN}  ✓ .env.prod uploaded${NC}"
echo ""

# --- Step 5: Install dependencies and build ---
echo -e "${YELLOW}[5/6] Installing dependencies & building...${NC}"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" << 'ENDSSH'
set -e
cd /home/ubuntu/xsamaa-ai-pipeline

echo -e "\033[0;34m════════════════════════════════════════\033[0m"
echo -e "\033[0;34m  🚀 Building Application\033[0m"
echo -e "\033[0;34m════════════════════════════════════════\033[0m"
echo ""

# Backend setup
echo "🔧 Setting up Backend..."
cd apps/api

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "  Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "  ✓ uv installed"
fi

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    uv venv .venv
fi

source .venv/bin/activate

# Install dependencies
echo "  Installing Python dependencies..."
uv pip install -e '.[prod]' --quiet 2>/dev/null || uv pip install -e . --quiet
echo "  ✓ Backend ready"
echo ""

# Run migrations
echo "🗄️ Running database migrations..."
export $(cat ../../.env.prod | grep -v '^#' | xargs) 2>/dev/null || true
alembic upgrade head 2>&1 | sed 's/^/  /' || echo "  (Migration skipped or failed)"
echo ""

# Frontend setup
echo "🎨 Setting up Frontend..."
cd ../web

# Install Node.js if not present
if ! command -v node &> /dev/null; then
    echo "  Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - >/dev/null 2>&1
    sudo apt-get install -y nodejs >/dev/null 2>&1
    echo "  ✓ Node.js installed: $(node --version)"
fi

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "  Installing Node.js dependencies..."
    npm install --quiet
else
    echo "  Updating Node.js dependencies..."
    npm install --quiet
fi
echo "  ✓ Frontend dependencies ready"
echo ""

# Build
echo "  Building Next.js..."
npm run build 2>&1 | tail -10
echo "  ✓ Frontend built"
echo ""

cd ../..

echo -e "\033[0;32m  ✅ Build Complete!\033[0m"
ENDSSH

echo -e "${GREEN}  ✓ Build successful${NC}"
echo ""

# --- Step 6: Restart services ---
echo -e "${YELLOW}[6/6] Restarting services...${NC}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" << 'ENDSSH'
echo "🔄 Checking services..."

# Try to restart systemd services if they exist
for service in samaa-api samaa-web samaa-celery; do
    if systemctl list-unit-files 2>/dev/null | grep -q $service; then
        echo "  Restarting $service..."
        sudo systemctl restart $service 2>/dev/null || echo "    (Failed to restart)"
        status=$(systemctl is-active $service 2>/dev/null)
        if [ "$status" = "active" ]; then
            echo "  ✅ $service: running"
        else
            echo "  ⚠️  $service: $status"
        fi
    else
        echo "  ⚠️  $service: not installed (manual start needed)"
    fi
done

echo ""
echo "📊 Manual start commands (if services not configured):"
echo "  cd /home/ubuntu/xsamaa-ai-pipeline/apps/api"
echo "  source .venv/bin/activate"
echo "  uvicorn src.main:app --host 0.0.0.0 --port 8000 --env-file ../../.env.prod &"
echo ""
echo "  cd /home/ubuntu/xsamaa-ai-pipeline/apps/web"
echo "  npm start &"
ENDSSH

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Deployment Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "  🌐 Frontend:   http://$SSH_HOST:3000"
echo "  📝 Backend:    http://$SSH_HOST:8000"
echo "  📖 API Docs:   http://$SSH_HOST:8000/docs"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Wait 10-15 seconds for services to start"
echo "  2. Visit http://$SSH_HOST:3000"
echo "  3. Visit http://$SSH_HOST:8000/docs to test API"
echo ""
echo -e "${BLUE}SSH Commands:${NC}"
echo "  Connect:"
echo "    ssh -i '$SSH_KEY' $SSH_USER@$SSH_HOST"
echo ""
echo "  View logs:"
echo "    ssh -i '$SSH_KEY' $SSH_USER@$SSH_HOST 'tail -f $REMOTE_DIR/.logs/*.log'"
echo ""
echo "  Check processes:"
echo "    ssh -i '$SSH_KEY' $SSH_USER@$SSH_HOST 'ps aux | grep -E \"uvicorn|next|celery\"'"
echo ""
