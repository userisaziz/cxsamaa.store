#!/usr/bin/env bash
# ============================================
# CXSAMAA — Start all development services
# ============================================
# Usage:
#   chmod +x start_servers.sh
#   ./start_servers.sh
#
# Starts: FastAPI, Celery worker, Next.js
# Optional: PostgreSQL+Redis (Docker) for local development
# Press Ctrl+C to stop all services.
#
# Architecture Options:
#   Local Dev:     Docker (PostgreSQL + Redis)
#   Production:    Neon PostgreSQL + Upstash Redis (set env vars)
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT_DIR/apps/api"
LOG_DIR="$ROOT_DIR/.logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Track PIDs for cleanup
PIDS=()

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down all services...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    # Also kill docker compose if we started it
    if [ "$STARTED_DOCKER" = true ]; then
        cd "$ROOT_DIR" && docker compose down 2>/dev/null || true
    fi
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   CXSAMAA Development Server Launcher  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# --- Step 1: Check prerequisites ---
echo -e "${YELLOW}[1/5] Checking prerequisites...${NC}"

command -v docker >/dev/null 2>&1 || { echo -e "${RED}docker not found. Install Docker first.${NC}"; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e "${RED}node not found. Install Node.js first.${NC}"; exit 1; }
command -v uvicorn >/dev/null 2>&1 || {
    if [ ! -f "$API_DIR/.venv/bin/uvicorn" ]; then
        echo -e "${RED}API dependencies not installed. Run:${NC}"
        echo "  cd apps/api && uv venv .venv && source .venv/bin/activate && uv pip install -e '.[dev]'"
        exit 1
    fi
}

echo -e "${GREEN}  ✓ All prerequisites found${NC}"

# --- Step 2: Check .env ---
echo -e "${YELLOW}[2/5] Checking environment...${NC}"

if [ ! -f "$ROOT_DIR/.env" ]; then
    echo -e "${YELLOW}  .env not found, copying from .env.example...${NC}"
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo -e "${YELLOW}  ⚠  Edit .env and set NVIDIA_API_KEY before using the pipeline${NC}"
fi

# Symlink .env into apps/api if not present
if [ ! -e "$API_DIR/.env" ]; then
    ln -sf ../../.env "$API_DIR/.env"
fi

echo -e "${GREEN}  ✓ Environment configured${NC}"

# --- Step 3: Start Infrastructure (Optional Docker) ---
echo -e "${YELLOW}[3/5] Checking infrastructure...${NC}"

STARTED_DOCKER=false

# Check if using managed services (Neon/Upstash) or local Docker
if [[ "$DATABASE_URL" == *"neon.tech"* ]] || [[ "$DATABASE_URL" == *"supabase.co"* ]]; then
    echo -e "${GREEN}  ✓ Using managed PostgreSQL (Neon/Supabase)${NC}"
elif [[ "$REDIS_URL" == *"upstash.io"* ]]; then
    echo -e "${GREEN}  ✓ Using managed Redis (Upstash)${NC}"
else
    # Use local Docker for development
    echo -e "${YELLOW}  Starting local Docker services (PostgreSQL + Redis)...${NC}"
    
    if docker compose ps --services 2>/dev/null | grep -q postgres; then
        # Check if services are actually running
        if docker compose ps 2>/dev/null | grep -q "Up\|running"; then
            echo -e "${GREEN}  ✓ Docker services already running${NC}"
        else
            cd "$ROOT_DIR" && docker compose up -d
            STARTED_DOCKER=true
            echo -e "${GREEN}  ✓ Docker services started${NC}"
        fi
    else
        cd "$ROOT_DIR" && docker compose up -d
        STARTED_DOCKER=true
        echo -e "${GREEN}  ✓ Docker services started${NC}"
    fi

    # Wait for PostgreSQL to be ready
    echo -n "  Waiting for PostgreSQL"
    for i in $(seq 1 15); do
        if docker compose exec -T postgres pg_isready -U samaa >/dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}  ✓ PostgreSQL ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""

    # Wait for Redis
    echo -n "  Waiting for Redis"
    for i in $(seq 1 10); do
        if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}  ✓ Redis ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""
fi

# --- Step 4: Run migrations ---
echo -e "${YELLOW}[4/5] Running database migrations...${NC}"
cd "$API_DIR"
source .venv/bin/activate
alembic upgrade head 2>&1 | sed 's/^/  /'
echo -e "${GREEN}  ✓ Migrations complete${NC}"

# --- Step 5: Start application servers ---
echo -e "${YELLOW}[5/5] Starting application servers...${NC}"

# FastAPI
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/api.log" 2>&1 &
PIDS+=($!)
echo -e "${GREEN}  ✓ FastAPI      → http://localhost:8000  (docs: /docs)${NC}"

# Celery worker (solo pool for macOS fork safety)
celery -A src.workers.celery_app worker --loglevel=info --pool=solo \
    > "$LOG_DIR/celery.log" 2>&1 &
PIDS+=($!)
echo -e "${GREEN}  ✓ Celery       → processing pipeline tasks${NC}"

# Next.js frontend
cd "$ROOT_DIR"
npm run dev:web > "$LOG_DIR/web.log" 2>&1 &
PIDS+=($!)
echo -e "${GREEN}  ✓ Next.js      → http://localhost:3000${NC}"

echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}  All services running!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC}   http://localhost:3000"
echo -e "  ${BLUE}API:${NC}        http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}   http://localhost:8000/docs"
echo -e "  ${BLUE}Logs:${NC}       $LOG_DIR/"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all background processes
wait
