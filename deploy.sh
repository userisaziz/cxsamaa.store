#!/usr/bin/env bash
# ============================================
# SAMAA — Production Deploy to Google Cloud Run
# ============================================
# Domain: cxsamaa.store
# Stack:  Cloud SQL + Upstash Redis + R2
# Architecture: API + Worker + Frontend
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
GCP_PROJECT="${GCP_PROJECT_ID:?Error: GCP_PROJECT_ID environment variable is required}"
GCP_REGION="${GCP_REGION:-us-central1}"
TAG="${TAG:-latest}"
DOMAIN="${DOMAIN:-cxsamaa.store}"

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   SAMAA Cloud Run Deploy             ║${NC}"
echo -e "${BLUE}║   Domain: ${DOMAIN}             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# --- Step 1: Verify prerequisites ---
echo -e "${YELLOW}[1/8] Verifying prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}  ✗ gcloud CLI not installed${NC}"
    exit 1
fi

if [ ! -f "apps/api/.env.prod" ]; then
    echo -e "${RED}  ✗ apps/api/.env.prod not found${NC}"
    echo -e "${YELLOW}    Copy from apps/api/.env.prod.example and fill in values${NC}"
    exit 1
fi

if [ ! -f "apps/web/.env.prod" ]; then
    echo -e "${RED}  ✗ apps/web/.env.prod not found${NC}"
    echo -e "${YELLOW}    Copy from apps/web/.env.prod.example and fill in values${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Prerequisites verified${NC}"
echo ""

# --- Step 2: Set GCP project ---
echo -e "${YELLOW}[2/8] Setting GCP project...${NC}"

gcloud config set project "${GCP_PROJECT}"
gcloud config set run/region "${GCP_REGION}"

echo -e "${GREEN}  ✓ Project: ${GCP_PROJECT}${NC}"
echo -e "${GREEN}  ✓ Region: ${GCP_REGION}${NC}"
echo ""

# --- Step 3: Verify infrastructure ---
echo -e "${YELLOW}[3/8] Verifying GCP infrastructure...${NC}"

# Check if Cloud SQL instance exists
if gcloud sql instances describe samaa-db --region="${GCP_REGION}" &>/dev/null; then
    echo -e "${GREEN}  ✓ Cloud SQL: samaa-db exists${NC}"
else
    echo -e "${YELLOW}  ⚠ Cloud SQL not found. Run setup-gcp-infrastructure.sh first${NC}"
    exit 1
fi

# Check if Cloud Tasks queue exists
if gcloud tasks queues describe pipeline-queue --location="${GCP_REGION}" &>/dev/null; then
    echo -e "${GREEN}  ✓ Cloud Tasks Queue: pipeline-queue exists${NC}"
else
    echo -e "${YELLOW}  ⚠ Cloud Tasks Queue not found. Run setup-gcp-infrastructure.sh first${NC}"
    exit 1
fi

# Check if service account exists
if gcloud iam service-accounts describe samaa-worker-sa@${GCP_PROJECT}.iam.gserviceaccount.com &>/dev/null; then
    echo -e "${GREEN}  ✓ Service Account: samaa-worker-sa exists${NC}"
else
    echo -e "${YELLOW}  ⚠ Service Account not found. Run setup-gcp-infrastructure.sh first${NC}"
    exit 1
fi

echo ""

# --- Step 4: Run database migrations ---
echo -e "${YELLOW}[4/8] Running database migrations...${NC}"

gcloud run jobs deploy samaa-migrations \
  --image="gcr.io/${GCP_PROJECT}/samaa-api:${TAG}" \
  --region="${GCP_REGION}" \
  --args="alembic","upgrade","head" \
  --set-env-vars="APP_ENV=production" \
  --env-vars-file=apps/api/.env.prod \
  --wait

echo -e "${GREEN}  ✓ Database migrations complete${NC}"
echo ""

# --- Step 5: Deploy Worker (Cloud Run Service) ---
echo -e "${YELLOW}[5/8] Deploying Worker service...${NC}"

gcloud run deploy samaa-worker \
  --image="gcr.io/${GCP_PROJECT}/samaa-worker:${TAG}" \
  --region="${GCP_REGION}" \
  --platform=managed \
  --port=8000 \
  --cpu=4 \
  --memory=8Gi \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=1 \
  --timeout=600 \
  --set-env-vars="APP_ENV=production,APP_DEBUG=false" \
  --env-vars-file=apps/api/.env.prod \
  --no-allow-unauthenticated

WORKER_URL=$(gcloud run services describe samaa-worker --region="${GCP_REGION}" --format="value(status.url)")
echo -e "${GREEN}  ✓ Worker deployed: ${WORKER_URL}${NC}"
echo ""

# --- Step 6: Deploy API (Cloud Run Service) ---
echo -e "${YELLOW}[6/8] Deploying API service...${NC}"

# Update .env.prod with worker URL before deploying API
sed -i.bak "s|WORKER_URL=.*|WORKER_URL=${WORKER_URL}|g" apps/api/.env.prod

gcloud run deploy samaa-api \
  --image="gcr.io/${GCP_PROJECT}/samaa-api:${TAG}" \
  --region="${GCP_REGION}" \
  --platform=managed \
  --port=8000 \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=5 \
  --concurrency=50 \
  --timeout=300 \
  --set-env-vars="APP_ENV=production,APP_DEBUG=false" \
  --env-vars-file=apps/api/.env.prod \
  --allow-unauthenticated

API_URL=$(gcloud run services describe samaa-api --region="${GCP_REGION}" --format="value(status.url)")
echo -e "${GREEN}  ✓ API deployed: ${API_URL}${NC}"
echo ""

# --- Step 7: Deploy Frontend (Cloud Run Service) ---
echo -e "${YELLOW}[7/8] Deploying Frontend service...${NC}"

# Update frontend .env.prod with API URL
sed -i.bak "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=${API_URL}|g" apps/web/.env.prod

gcloud run deploy samaa-web \
  --image="gcr.io/${GCP_PROJECT}/samaa-web:${TAG}" \
  --region="${GCP_REGION}" \
  --platform=managed \
  --port=3000 \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=5 \
  --concurrency=80 \
  --timeout=60 \
  --env-vars-file=apps/web/.env.prod \
  --allow-unauthenticated

WEB_URL=$(gcloud run services describe samaa-web --region="${GCP_REGION}" --format="value(status.url)")
echo -e "${GREEN}  ✓ Frontend deployed: ${WEB_URL}${NC}"
echo ""

# --- Step 8: Setup custom domain ---
echo -e "${YELLOW}[8/8] Setting up custom domain...${NC}"

if gcloud run domain-mappings describe --domain="${DOMAIN}" --region="${GCP_REGION}" &>/dev/null; then
    echo -e "${GREEN}  ✓ Domain mapping exists: ${DOMAIN}${NC}"
else
    echo "  Creating domain mapping for ${DOMAIN}..."
    gcloud run domain-mappings create \
      --service=samaa-web \
      --domain="${DOMAIN}" \
      --region="${GCP_REGION}" \
      || echo -e "${YELLOW}  ⚠ Domain mapping requires DNS verification${NC}"
    
    echo ""
    echo -e "${YELLOW}  DNS Setup (required for HTTPS):${NC}"
    echo "    Add these DNS records at your domain registrar:"
    echo ""
    echo "    A record:"
    echo "      Type: A"
    echo "      Name: @"
    echo "      Value: $(gcloud run services describe samaa-web --region="${GCP_REGION}" --format="value(status.address.url)")"
    echo "      TTL: 300"
    echo ""
    echo "    TXT record (for verification):"
    echo "      (Google will provide this after domain mapping creation)"
    echo ""
    echo "    Wait 5-30 minutes for DNS propagation"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Deployment Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC}  https://${DOMAIN}"
echo -e "  ${BLUE}API:${NC}       ${API_URL}"
echo -e "  ${BLUE}Worker:${NC}    ${WORKER_URL}"
echo -e "  ${BLUE}Docs:${NC}      ${API_URL}/docs"
echo ""
echo -e "${BLUE}Services Deployed:${NC}"
echo "  - samaa-api (1 CPU, 1GB RAM, 50 concurrency, 5 min timeout)"
echo "  - samaa-worker (4 CPU, 8GB RAM, 1 concurrency, 10 min timeout)"
echo "  - samaa-web (1 CPU, 512MB RAM, 80 concurrency)"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:     gcloud run services logs read samaa-api --region=${GCP_REGION}"
echo "  Worker logs:   gcloud run services logs read samaa-worker --region=${GCP_REGION}"
echo "  Task queue:    gcloud tasks queues describe pipeline-queue --location=${GCP_REGION}"
echo "  List services: gcloud run services list --region=${GCP_REGION}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Test upload at: https://${DOMAIN}/upload"
echo "  2. Monitor tasks:  gcloud tasks queues list --location=${GCP_REGION}"
echo "  3. View metrics:   gcloud run services describe samaa-api --region=${GCP_REGION}"
echo ""
