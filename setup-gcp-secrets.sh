#!/bin/bash
# setup-gcp-secrets.sh — Create GCP service account and set GitHub secrets
# Run this once to enable GCP Cloud Run deployments from GitHub Actions

set -e

PROJECT_ID="cxsamaa"
REGION="us-central1"

echo "═══════════════════════════════════════════════════"
echo "  GCP + GitHub Secrets Setup for CXSAMAA"
echo "═══════════════════════════════════════════════════"
echo ""

# Step 1: Check gcloud auth
echo "[1/6] Checking GCP authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null; then
  echo "  ❌ Not authenticated. Run: gcloud auth login"
  exit 1
fi
echo "  ✅ Authenticated"

# Step 2: Check billing
echo "[2/6] Checking billing account..."
BILLING=$(gcloud projects describe $PROJECT_ID --format="value(billingEnabled)" 2>/dev/null)
if [ "$BILLING" != "True" ]; then
  echo "  ❌ Billing not enabled for project $PROJECT_ID"
  echo "  Enable at: https://console.cloud.google.com/billing"
  exit 1
fi
echo "  ✅ Billing enabled"

# Step 3: Enable APIs
echo "[3/6] Enabling GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com \
  --project=$PROJECT_ID
echo "  ✅ APIs enabled"

# Step 4: Create Artifact Registry
echo "[4/6] Creating Artifact Registry..."
gcloud artifacts repositories create samaa-registry \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID \
  --description="SAMAA container images" 2>/dev/null || echo "  ℹ️  Registry already exists"
echo "  ✅ Artifact Registry ready"

# Step 5: Create Service Account
echo "[5/6] Creating service account..."
SA_EMAIL="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create github-deployer \
  --display-name="GitHub Actions Deployer" \
  --project=$PROJECT_ID 2>/dev/null || echo "  ℹ️  Service account already exists"

# Grant roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin" --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.admin" --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser" --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin" --quiet 2>/dev/null || true

# Generate key
KEY_FILE="/tmp/gcp-sa-key.json"
gcloud iam service-accounts keys create $KEY_FILE \
  --iam-account=$SA_EMAIL \
  --project=$PROJECT_ID 2>/dev/null || echo "  ℹ️  Key file may already exist"
echo "  ✅ Service account key created at $KEY_FILE"

# Step 6: Set GitHub Secrets
echo "[6/6] Setting GitHub secrets..."

echo ""
echo "  ⚠️  You need to provide some values manually:"
echo ""
read -p "  Database URL (Neon): " DB_URL
read -p "  Database URL Sync (Neon): " DB_URL_SYNC
read -p "  JWT Secret: " JWT_SECRET
read -p "  R2 Account ID: " R2_ACCOUNT_ID
read -p "  R2 Access Key ID: " R2_ACCESS_KEY
read -p "  R2 Secret Access Key: " R2_SECRET_KEY
read -p "  R2 Bucket Name: " R2_BUCKET
echo ""

# Set secrets
gh secret set GCP_SA_KEY < $KEY_FILE
gh secret set GCP_PROJECT_ID <<< "$PROJECT_ID"
gh secret set NEON_DATABASE_URL <<< "$DB_URL"
gh secret set NEON_DATABASE_URL_SYNC <<< "$DB_URL_SYNC"
gh secret set JWT_SECRET <<< "$JWT_SECRET"
gh secret set R2_ACCOUNT_ID <<< "$R2_ACCOUNT_ID"
gh secret set R2_ACCESS_KEY_ID <<< "$R2_ACCESS_KEY"
gh secret set R2_SECRET_ACCESS_KEY <<< "$R2_SECRET_KEY"
gh secret set R2_BUCKET <<< "$R2_BUCKET"
gh secret set CORS_ORIGINS <<< '["https://cxsamaa.store","http://localhost:3000"]'
gh secret set API_BASE_URL <<< "https://api.cxsamaa.store"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ All secrets configured!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Next: Push to main to trigger deployment"
echo "  Or run: git commit -m 'trigger deploy' && git push origin main"
echo ""

# Cleanup
rm -f $KEY_FILE
