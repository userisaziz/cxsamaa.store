#!/usr/bin/env bash
# ============================================
# Setup GitHub Secrets for GCP Deployment
# ============================================
# This script helps you add required secrets to your GitHub repository
# ============================================

set -e

echo "╔══════════════════════════════════════════════╗"
echo "║   GitHub Secrets Setup for GCP Deployment   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "This script will guide you through adding secrets to:"
echo "Repository: userisaziz/samaa-ai"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "Install it: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Generate JWT Secret
echo "🔐 Step 1: Generate JWT Secret"
JWT_SECRET=$(openssl rand -hex 32)
echo "Generated JWT_SECRET: $JWT_SECRET"
echo ""
read -p "Add this secret to GitHub? (y/n): " add_jwt
if [ "$add_jwt" = "y" ]; then
    gh secret set JWT_SECRET --body="$JWT_SECRET"
    echo "✅ JWT_SECRET added"
fi
echo ""

# GCP Project ID
echo "📦 Step 2: Set GCP Project ID"
echo "GCP_PROJECT_ID: cxsamaa"
read -p "Add this secret to GitHub? (y/n): " add_gcp
if [ "$add_gcp" = "y" ]; then
    gh secret set GCP_PROJECT_ID --body="cxsamaa"
    echo "✅ GCP_PROJECT_ID added"
fi
echo ""

# Database credentials
echo "🗄️  Step 3: Database Credentials (Neon)"
echo "You need to get these from your Neon dashboard:"
echo "  - NEON_DATABASE_URL (async)"
echo "  - NEON_DATABASE_URL_SYNC (sync)"
echo ""
echo "Go to: https://console.neon.tech"
read -p "Have your Neon credentials ready? (y/n): " has_neon
if [ "$has_neon" = "y" ]; then
    read -p "Enter NEON_DATABASE_URL: " neon_url
    read -p "Enter NEON_DATABASE_URL_SYNC: " neon_url_sync
    
    gh secret set NEON_DATABASE_URL --body="$neon_url"
    echo "✅ NEON_DATABASE_URL added"
    
    gh secret set NEON_DATABASE_URL_SYNC --body="$neon_url_sync"
    echo "✅ NEON_DATABASE_URL_SYNC added"
fi
echo ""

# R2 Storage credentials
echo "☁️  Step 4: Cloudflare R2 Storage"
echo "You need to get these from Cloudflare R2 dashboard:"
echo "  - R2_ACCOUNT_ID"
echo "  - R2_ACCESS_KEY_ID"
echo "  - R2_SECRET_ACCESS_KEY"
echo "  - R2_BUCKET (create a bucket if you haven't)"
echo ""
echo "Go to: Cloudflare Dashboard > R2 Storage"
read -p "Have your R2 credentials ready? (y/n): " has_r2
if [ "$has_r2" = "y" ]; then
    read -p "Enter R2_ACCOUNT_ID: " r2_account
    read -p "Enter R2_ACCESS_KEY_ID: " r2_access
    read -p "Enter R2_SECRET_ACCESS_KEY: " r2_secret
    read -p "Enter R2_BUCKET: " r2_bucket
    
    gh secret set R2_ACCOUNT_ID --body="$r2_account"
    echo "✅ R2_ACCOUNT_ID added"
    
    gh secret set R2_ACCESS_KEY_ID --body="$r2_access"
    echo "✅ R2_ACCESS_KEY_ID added"
    
    gh secret set R2_SECRET_ACCESS_KEY --body="$r2_secret"
    echo "✅ R2_SECRET_ACCESS_KEY added"
    
    gh secret set R2_BUCKET --body="$r2_bucket"
    echo "✅ R2_BUCKET added"
fi
echo ""

# CORS Origins
echo "🌐 Step 5: CORS Origins"
CORS_ORIGINS="https://cxsamaa.store,https://app.cxsamaa.store,https://api.cxsamaa.store"
echo "CORS_ORIGINS: $CORS_ORIGINS"
read -p "Add this secret to GitHub? (y/n): " add_cors
if [ "$add_cors" = "y" ]; then
    gh secret set CORS_ORIGINS --body="$CORS_ORIGINS"
    echo "✅ CORS_ORIGINS added"
fi
echo ""

# Summary
echo "══════════════════════════════════════════════"
echo "✅ Secrets Setup Complete!"
echo "══════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Push to main to trigger deployment"
echo "   git push origin main"
echo ""
echo "2. Monitor deployment:"
echo "   gh run list --workflow=deploy-gcp.yml"
echo ""
echo "3. After deployment succeeds, set up custom domain:"
echo "   See: CUSTOM_DOMAIN_SETUP.md"
echo ""
echo "View all secrets: https://github.com/userisaziz/samaa-ai/settings/secrets/actions"
