#!/bin/bash
# GCP Infrastructure Setup Script for SAMAA AI Pipeline
# Creates all required GCP resources for Cloud Run deployment

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:?Error: GCP_PROJECT_ID environment variable is required}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_ACCOUNT_EMAIL="${GCP_WORKER_SA_EMAIL:-samaa-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com}"
CLOUD_TASKS_QUEUE="pipeline-queue"
DOMAIN="${DOMAIN:-cxsamaa.store}"

echo "=========================================="
echo "SAMAA AI - GCP Infrastructure Setup"
echo "=========================================="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Worker Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo "Domain: ${DOMAIN}"
echo "=========================================="

# Set project
echo ""
echo "📦 Setting GCP project..."
gcloud config set project "${PROJECT_ID}"

# Enable required APIs
echo ""
echo "🔧 Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudtasks.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com

echo "✅ APIs enabled successfully"

# Create Service Account for Worker
echo ""
echo "🔐 Creating Worker Service Account..."
gcloud iam service-accounts create samaa-worker-sa \
  --display-name="SAMAA Worker Service Account" \
  --description="Service account for SAMAA pipeline worker with Cloud Tasks access"

# Grant required roles to the service account
echo "🔑 Granting roles to service account..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/run.invoker" \
  --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/cloudtasks.enqueuer" \
  --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/storage.objectViewer" \
  --quiet

echo "✅ Service account created and configured"

# Create Cloud Tasks Queue
echo ""
echo "📋 Creating Cloud Tasks Queue..."
gcloud tasks queues create "${CLOUD_TASKS_QUEUE}" \
  --location="${REGION}" \
  --max-attempts=3 \
  --max-retry-duration=1h \
  --max-backoff=300s \
  --min-backoff=10s \
  --max-doublings=5

echo "✅ Cloud Tasks Queue created: ${CLOUD_TASKS_QUEUE}"

# Create Artifact Registry (optional, if you want to use it instead of GCR)
echo ""
echo "🗂️ Creating Artifact Registry repository..."
gcloud artifacts repositories create samaa-images \
  --repository-format=docker \
  --location="${REGION}" \
  --description="SAMAA AI container images" \
  || echo "Artifact repository already exists"

echo "✅ Artifact Registry configured"

# Create Cloud SQL Database (PostgreSQL)
echo ""
echo "🗄️ Creating Cloud SQL PostgreSQL instance..."
gcloud sql instances create samaa-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region="${REGION}" \
  --storage-size=10GB \
  --storage-type=SSD \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04:00 \
  --no-insights-config \
  || echo "Cloud SQL instance already exists"

# Create database
gcloud sql databases create samaa \
  --instance=samaa-db \
  || echo "Database already exists"

# Create database user
gcloud sql users create samaa \
  --instance=samaa-db \
  --password="${DB_PASSWORD:-samaa_production_password}" \
  || echo "Database user already exists"

echo "✅ Cloud SQL database configured"

# Create Secret Manager secrets
echo ""
echo "🔒 Creating Secret Manager secrets..."

# Database URL
echo -n "postgresql+asyncpg://samaa:${DB_PASSWORD:-samaa_production_password}@/samaa?host=/cloudsql/${PROJECT_ID}:${REGION}:samaa-db" | \
  gcloud secrets create database-url \
  --data-file=- \
  --replication-policy="automatic" \
  || echo "Secret 'database-url' already exists"

# JWT Secret
openssl rand -hex 32 | \
  gcloud secrets create jwt-secret \
  --data-file=- \
  --replication-policy="automatic" \
  || echo "Secret 'jwt-secret' already exists"

echo "✅ Secret Manager configured"

# Grant Cloud Run access to secrets
echo "🔓 Granting Cloud Run access to secrets..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet

# Setup Cloud Run custom domain (optional)
echo ""
echo "🌐 Setting up custom domain mapping..."
gcloud run domain-mappings create \
  --service=samaa-web \
  --domain="${DOMAIN}" \
  --region="${REGION}" \
  || echo "Domain mapping already exists or requires manual verification"

echo "✅ Domain mapping configured (may require DNS verification)"

echo ""
echo "=========================================="
echo "✅ GCP Infrastructure Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Create apps/api/.env.prod with your production configuration"
echo "2. Create apps/web/.env.prod with your frontend production configuration"
echo "3. Update DATABASE_URL to use the Cloud SQL connection string"
echo "4. Run: gcloud builds submit --config cloudbuild.yaml --substitutions=_TAG=v1.0.0"
echo "5. Verify deployment: gcloud run services list"
echo ""
echo "Worker Service URL (needed for .env.prod):"
gcloud run services describe samaa-worker --region="${REGION}" --format="value(status.url)" 2>/dev/null || echo "  (deploy worker first)"
echo ""
echo "API Service URL:"
gcloud run services describe samaa-api --region="${REGION}" --format="value(status.url)" 2>/dev/null || echo "  (deploy API first)"
echo ""
echo "Frontend Service URL:"
gcloud run services describe samaa-web --region="${REGION}" --format="value(status.url)" 2>/dev/null || echo "  (deploy frontend first)"
echo ""
