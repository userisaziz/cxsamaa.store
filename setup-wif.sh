#!/bin/bash
# setup-wif.sh — Set up Workload Identity Federation for GitHub Actions
# This is the SECURE way to authenticate (no service account keys needed)

set -e

PROJECT_ID="cxsamaa"
REGION="us-central1"
SA_EMAIL="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
POOL_ID="github-actions-pool"
PROVIDER_ID="github-provider"

echo "═══════════════════════════════════════════════════"
echo "  Workload Identity Federation Setup"
echo "═══════════════════════════════════════════════════"
echo ""

# Check gcloud auth
echo "[1/5] Checking GCP authentication..."
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
if [ -z "$ACCOUNT" ]; then
  echo "  ❌ Not authenticated. Run: gcloud auth login"
  exit 1
fi
echo "  ✅ Authenticated as: $ACCOUNT"

# Enable APIs
echo "[2/5] Enabling APIs..."
gcloud services enable \
  iam.googleapis.com \
  sts.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project=$PROJECT_ID
echo "  ✅ APIs enabled"

# Create Workload Identity Pool
echo "[3/5] Creating Workload Identity Pool..."
gcloud iam workload-identity-pools create $POOL_ID \
  --location="global" \
  --description="GitHub Actions Pool" \
  --project=$PROJECT_ID 2>/dev/null || echo "  ℹ️  Pool already exists"

# Create Workload Identity Provider
echo "[4/5] Creating Workload Identity Provider..."
gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID \
  --location="global" \
  --workload-identity-pool=$POOL_ID \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --project=$PROJECT_ID 2>/dev/null || echo "  ℹ️  Provider already exists"

# Allow GitHub repo to impersonate service account
echo "  Linking provider to service account..."
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --project=$PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/$POOL_ID/attribute.repository/userisaziz/samaa-ai" \
  --quiet

echo "  ✅ Workload Identity configured"

# Generate the resource path
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
WIF_RESOURCE="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

echo ""
echo "[5/5] Setting GitHub secrets..."
echo ""

# Ask for credentials
echo "  ⚠️  Enter your credentials (from .env.prod):"
echo ""
read -p "  Database URL (Neon): " DB_URL
read -p "  Database URL Sync: " DB_URL_SYNC
read -p "  JWT Secret: " JWT_SECRET
read -p "  R2 Account ID: " R2_ACCOUNT_ID
read -p "  R2 Access Key ID: " R2_ACCESS_KEY
read -p "  R2 Secret Access Key: " R2_SECRET_KEY
read -p "  R2 Bucket Name: " R2_BUCKET
echo ""

# Set GitHub secrets
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER <<< "$WIF_RESOURCE"
gh secret set GCP_SERVICE_ACCOUNT_EMAIL <<< "$SA_EMAIL"
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
echo "  ✅ Workload Identity Federation configured!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Resource: $WIF_RESOURCE"
echo "  Service Account: $SA_EMAIL"
echo ""
echo "  Next: I'll update the workflow to use WIF instead of keys"
echo ""
