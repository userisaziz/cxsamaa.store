#!/bin/bash

# CXSAMAA Public Share Script
# Builds frontend, starts all services, and launches ngrok tunnel

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════╗"
echo "║   CXSAMAA Public Share Setup           ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Kill existing services on ports
echo -e "${YELLOW}[1/6] Cleaning up existing services...${NC}"
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓ Ports cleared${NC}"
echo ""

# Check Docker
echo -e "${YELLOW}[2/6] Checking Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running. Starting Docker Desktop...${NC}"
    open -a Docker
    echo "Waiting for Docker to start..."
    for i in {1..30}; do
        if docker info > /dev/null 2>&1; then
            break
        fi
        sleep 2
    done
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}✗ Docker failed to start. Please start Docker Desktop manually.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Start infrastructure (PostgreSQL + Redis)
echo -e "${YELLOW}[3/6] Starting infrastructure (PostgreSQL + Redis)...${NC}"
docker compose up -d postgres redis 2>/dev/null || {
    echo -e "${RED}✗ Failed to start Docker services${NC}"
    exit 1
}
sleep 3
echo -e "${GREEN}✓ Infrastructure started${NC}"
echo ""

# Check database exists
echo -e "${YELLOW}[4/6] Checking database...${NC}"
if ! psql -U postgres -lqt | cut -d \| -f 1 | grep -qw samaa; then
    echo "Creating database..."
    psql -U postgres -c "CREATE ROLE samaa WITH LOGIN SUPERUSER PASSWORD 'samaa';" 2>/dev/null || true
    psql -U postgres -c "CREATE DATABASE samaa OWNER samaa;"
    psql -U postgres -d samaa -c "CREATE EXTENSION IF NOT EXISTS vector;"
    echo -e "${GREEN}✓ Database created${NC}"
else
    echo -e "${GREEN}✓ Database exists${NC}"
fi
echo ""

# Start backend
echo -e "${YELLOW}[5/6] Starting backend API...${NC}"
cd apps/api
nohup uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

echo "Waiting for backend to start..."
for i in {1..20}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend API running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    exit 1
fi
echo ""

# Build and start frontend
echo -e "${YELLOW}[6/6] Building and starting frontend...${NC}"
cd apps/web

echo "Building production bundle..."
npm run build > /dev/null 2>&1

echo "Starting Next.js server..."
nohup npm run start > /dev/null 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

echo "Waiting for frontend to start..."
for i in {1..15}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend running (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}✗ Frontend failed to start${NC}"
    exit 1
fi
echo ""

# Start ngrok
echo "╔══════════════════════════════════════╗"
echo "║   Starting ngrok tunnel...           ║"
echo "╚══════════════════════════════════════╝"
echo ""

ngrok http 3000 &
NGROK_PID=$!

sleep 5

# Get ngrok URL
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null)

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                                                      ║"
echo -e "║  ${GREEN}✓ CXSAMAA is now publicly accessible!${NC}              ║"
echo "║                                                      ║"
echo -e "║  ${YELLOW}Public URL:${NC}                                     ║"
echo -e "║  ${GREEN}$NGROK_URL${NC}     ║"
echo "║                                                      ║"
echo "║  Test Credentials:                                   ║"
echo "║  ┌─────────────────────────────────────────────┐    ║"
echo "║  │ Super Admin:  admin@samaa.com / admin123    │    ║"
echo "║  │ Brand Admin:  brand@retailmax.com / brand123│    ║"
echo "║  │ Store Mgr:    manager@retailmax.com / m...  │    ║"
echo "║  │ Salesperson:  alice@retailmax.com / sales123│    ║"
echo "║  │ Operator:     ops@samaa.com / ops123        │    ║"
echo "║  └─────────────────────────────────────────────┘    ║"
echo "║                                                      ║"
echo "║  Press Ctrl+C to stop all services                   ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Cleanup on exit
cleanup() {
    echo ""
    echo "Stopping all services..."
    kill $FRONTEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    kill $NGROK_PID 2>/dev/null || true
    docker compose down 2>/dev/null || true
    echo "✓ All services stopped"
    exit 0
}

trap cleanup INT TERM

# Wait for user to press Ctrl+C
wait
