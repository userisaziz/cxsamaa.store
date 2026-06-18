#!/bin/bash
# verify-wif.sh — Verify Workload Identity Federation setup
# Run this to diagnose authentication issues
#
# USAGE: ./verify-wif.sh
# This script is SAFE to commit - it only reads configuration, no secrets.
# Contains project-specific values: cxsamaa, userisaziz/samaa-ai

set -e

PROJECT_ID="cxsamaa"
POOL_ID="github-actions-pool"
PROVIDER_ID="github-provider"
SA_EMAIL="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

echo "═══════════════════════════════════════════════════"
echo "  WIF Configuration Verification"
echo "═══════════════════════════════════════════════════"
echo ""

# Check gcloud auth
echo "[1/6] Checking GCP authentication..."
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
if [ -z "$ACCOUNT" ]; then
  echo "  ❌ Not authenticated. Run: gcloud auth login"
  exit 1
fi
echo "  ✅ Authenticated as: $ACCOUNT"

# Check project
echo "[2/6] Verifying project..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
  echo "  ⚠️  Current project: $CURRENT_PROJECT (expected: $PROJECT_ID)"
  echo "  Fix: gcloud config set project $PROJECT_ID"
else
  echo "  ✅ Project: $PROJECT_ID"
fi

# Check pool exists
echo "[3/6] Checking Workload Identity Pool..."
POOL_EXISTS=$(gcloud iam workload-identity-pools describe $POOL_ID \
  --location="global" \
  --project=$PROJECT_ID \
  --format="value(name)" 2>/dev/null || echo "")

if [ -z "$POOL_EXISTS" ]; then
  echo "  ❌ Pool '$POOL_ID' not found!"
  echo "  Fix: Run setup-wif.sh"
  exit 1
fi
echo "  ✅ Pool exists: $POOL_EXISTS"

# Check provider exists
echo "[4/6] Checking Workload Identity Provider..."
PROVIDER_EXISTS=$(gcloud iam workload-identity-pools providers describe $PROVIDER_ID \
  --location="global" \
  --workload-identity-pool=$POOL_ID \
  --project=$PROJECT_ID \
  --format="value(name)" 2>/dev/null || echo "")

if [ -z "$PROVIDER_EXISTS" ]; then
  echo "  ❌ Provider '$PROVIDER_ID' not found!"
  echo "  Fix: Run setup-wif.sh"
  exit 1
fi
echo "  ✅ Provider exists: $PROVIDER_EXISTS"

# Check service account
echo "[5/6] Checking service account..."
SA_EXISTS=$(gcloud iam service-accounts describe $SA_EMAIL \
  --project=$PROJECT_ID \
  --format="value(email)" 2>/dev/null || echo "")

if [ -z "$SA_EXISTS" ]; then
  echo "  ❌ Service account '$SA_EMAIL' not found!"
  echo "  Fix: Create it in GCP IAM console"
  exit 1
fi
echo "  ✅ Service account exists: $SA_EXISTS"

# Check IAM binding
echo "[6/6] Checking IAM policy binding..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
EXPECTED_MEMBER="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/userisaziz/samaa-ai"

BINDING_EXISTS=$(gcloud iam service-accounts get-iam-policy $SA_EMAIL \
  --project=$PROJECT_ID \
  --format="table(bindings.role,bindings.members)" | grep -F "$EXPECTED_MEMBER" || echo "")

if [ -z "$BINDING_EXISTS" ]; then
  echo "  ❌ Repository not authorized to impersonate service account!"
  echo "  Expected member: $EXPECTED_MEMBER"
  echo ""
  echo "  Fix: Run this command:"
  echo "  gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \\"
  echo "    --project=$PROJECT_ID \\"
  echo "    --role='roles/iam.workloadIdentityUser' \\"
  echo "    --member='$EXPECTED_MEMBER' \\"
  echo "    --quiet"
  exit 1
fi
echo "  ✅ Repository authorized"

# Generate WIF resource path
WIF_RESOURCE="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ All checks passed!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  GitHub Secret Values (copy these exactly):"
echo ""
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER:"
echo "    $WIF_RESOURCE"
echo ""
echo "  GCP_SERVICE_ACCOUNT_EMAIL:"
echo "    $SA_EMAIL"
echo ""
echo "  GCP_PROJECT_ID:"
echo "    $PROJECT_ID"
echo ""
echo "  ⚠️  Make sure these match your GitHub repository secrets exactly!"
echo ""
