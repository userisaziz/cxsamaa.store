#!/usr/bin/env bash
# ============================================
# SAMAA — Seed the database with test data
# ============================================
# Usage:
#   chmod +x seed.sh
#   ./seed.sh
#
# Seeds: Brands, Stores, Salespeople, Users (including OPERATOR)
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

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      SAMAA Database Seeder           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# Check virtual environment
if [ ! -f "$API_DIR/.venv/bin/python" ]; then
    echo -e "${RED}Virtual environment not found.${NC}"
    echo "  Run: cd apps/api && uv venv .venv && source .venv/bin/activate && uv pip install -e '.[dev]'"
    exit 1
fi

# Check .env
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo -e "${YELLOW}.env not found, copying from .env.example...${NC}"
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

# Symlink .env into apps/api if not present
if [ ! -e "$API_DIR/.env" ]; then
    ln -sf ../../.env "$API_DIR/.env"
fi

# Check Docker / PostgreSQL
echo -e "${YELLOW}Checking PostgreSQL...${NC}"
if ! docker compose ps 2>/dev/null | grep -q "Up\|running"; then
    echo -e "${YELLOW}  PostgreSQL not running, starting Docker...${NC}"
    cd "$ROOT_DIR" && docker compose up -d

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
else
    echo -e "${GREEN}  ✓ PostgreSQL is running${NC}"
fi

# Run migrations first
echo -e "${YELLOW}Running migrations...${NC}"
cd "$API_DIR"
source .venv/bin/activate
alembic upgrade head 2>&1 | sed 's/^/  /'
echo -e "${GREEN}  ✓ Migrations complete${NC}"
echo ""

# Run seed
echo -e "${YELLOW}Seeding database...${NC}"
export PYTHONPATH="$API_DIR:$PYTHONPATH"
python scripts/seed.py
echo ""

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Done! You can now login with any of these credentials:${NC}"
    echo ""
    echo -e "  ${BLUE}Super Admin:${NC}  admin@samaa.com / admin123"
    echo -e "  ${BLUE}Brand Admin:${NC}  brand@retailmax.com / brand123"
    echo -e "  ${BLUE}Store Mgr:${NC}    manager@retailmax.com / manager123"
    echo -e "  ${BLUE}Salesperson:${NC}  alice@retailmax.com / sales123"
    echo -e "  ${BLUE}Operator:${NC}     ops@samaa.com / ops123"
    echo ""
fi
