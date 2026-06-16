# Custom Domain Setup: cxsamaa.store

## 📋 Overview

This guide will help you map your custom domain `cxsamaa.store` to your GCP Cloud Run services.

### Planned URL Structure:
- **Landing Page**: `https://cxsamaa.store` (main marketing site)
- **Dashboard**: `https://app.cxsamaa.store` or `https://dashboard.cxsamaa.store`
- **API**: `https://api.cxsamaa.store`

---

## ⚠️ Prerequisites

### 1. Services Must Be Deployed First

Before mapping your domain, you need working Cloud Run services. Currently, your deployment is failing due to missing GitHub secrets.

**To fix the deployment, you need to:**

#### Option A: Fix GitHub Actions (Recommended)
1. Go to: https://github.com/userisaziz/samaa-ai/settings/actions
2. Under "Workflow permissions", select: **"Read and write permissions"**
3. Check: **"Allow GitHub Actions to create and approve pull requests"**
4. Add required repository secrets (see GITHUB_SECRETS_SETUP.md)
5. Push to main to trigger deployment

#### Option B: Manual Deploy (Faster for testing)
```bash
# Set up secrets locally
cp apps/api/.env.prod.example apps/api/.env.prod
cp apps/web/.env.prod.example apps/web/.env.prod

# Edit the files with your actual credentials
# Then run:
./deploy.sh
```

---

## 🌐 Domain Configuration Steps

### Step 1: Verify Domain Ownership

Before creating domain mappings, you need to verify you own `cxsamaa.store`:

```bash
# Go to Google Cloud Console
# Navigate to: Cloud Run > Domain Mappings
# Click "Verify domain ownership"
# Follow the instructions to add a TXT record to your DNS
```

### Step 2: Create Domain Mappings

Once services are deployed, create these domain mappings:

#### Landing Page (Main Domain)
```bash
gcloud beta run domain-mappings create \
  --service=samaa-landing \
  --domain=cxsamaa.store \
  --region=us-central1
```

#### Dashboard (Subdomain)
```bash
gcloud beta run domain-mappings create \
  --service=samaa-web \
  --domain=app.cxsamaa.store \
  --region=us-central1
```

#### API (Subdomain)
```bash
gcloud beta run domain-mappings create \
  --service=samaa-api \
  --domain=api.cxsamaa.store \
  --region=us-central1
```

### Step 3: Configure DNS Records

After creating the domain mappings, Google will provide you with DNS records to add at your domain registrar (where you bought `cxsamaa.store`).

**Expected DNS configuration:**

```
# For cxsamaa.store (landing page)
Type: A
Name: @
Value: [Google-provided IP]
TTL: 300

# For app.cxsamaa.store (dashboard)
Type: CNAME
Name: app
Value: ghs.googlehosted.com
TTL: 300

# For api.cxsamaa.store (API)
Type: CNAME
Name: api
Value: ghs.googlehosted.com
TTL: 300
```

**Note:** The exact values will be shown after you create the domain mappings.

---

## 🚀 Quick Start: Deploy & Configure Domain

### 1. Fix GitHub Actions Workflow Permissions

The workflow needs ID token permissions for Workload Identity Federation:

**Update `.github/workflows/deploy-gcp.yml`:**

Add this at the top level (after `name:`):
```yaml
permissions:
  id-token: write
  contents: read
```

### 2. Add Required GitHub Secrets

Go to: https://github.com/userisaziz/samaa-ai/settings/secrets/actions

Add these secrets:
- `GCP_PROJECT_ID` = `cxsamaa`
- `NEON_DATABASE_URL` (from Neon dashboard)
- `NEON_DATABASE_URL_SYNC` (from Neon dashboard)
- `JWT_SECRET` (generate with: `openssl rand -hex 32`)
- `R2_ACCOUNT_ID` (from Cloudflare)
- `R2_ACCESS_KEY_ID` (from Cloudflare)
- `R2_SECRET_ACCESS_KEY` (from Cloudflare)
- `R2_BUCKET` (your bucket name)
- `CORS_ORIGINS` = `https://cxsamaa.store,https://app.cxsamaa.store,https://api.cxsamaa.store`

### 3. Trigger Deployment

```bash
git add .github/workflows/deploy-gcp.yml
git commit -m "fix: add workflow permissions for workload identity"
git push origin main
```

### 4. Wait for Deployment (~8 minutes)

Monitor at: https://github.com/userisaziz/samaa-ai/actions

### 5. Verify Services Are Running

```bash
gcloud run services list --region=us-central1
```

### 6. Create Domain Mappings

```bash
# Landing page
gcloud beta run domain-mappings create \
  --service=samaa-landing \
  --domain=cxsamaa.store \
  --region=us-central1

# Dashboard
gcloud beta run domain-mappings create \
  --service=samaa-web \
  --domain=app.cxsamaa.store \
  --region=us-central1

# API
gcloud beta run domain-mappings create \
  --service=samaa-api \
  --domain=api.cxsamaa.store \
  --region=us-central1
```

### 7. Update DNS at Your Registrar

Log in to where you bought `cxsamaa.store` and add the DNS records provided by Google.

### 8. Wait for SSL Certificate (~10-30 minutes)

Google will automatically provision SSL certificates. You'll see:
```
✅ Domain mapping verified
✅ SSL certificate active
```

---

## 🔍 Verify Setup

### Check Domain Mappings
```bash
gcloud beta run domain-mappings list --region=us-central1
```

### Test HTTPS
```bash
curl -I https://cxsamaa.store
curl -I https://app.cxsamaa.store
curl -I https://api.cxsamaa.store
```

### Check SSL Certificate Status
```bash
gcloud beta run domain-mappings describe \
  --domain=cxsamaa.store \
  --region=us-central1
```

---

## 📝 Important Notes

1. **DNS Propagation**: Can take 5 minutes to 48 hours (usually < 30 minutes)
2. **SSL Certificates**: Google provisions automatically, takes ~10-30 minutes
3. **WWW Redirect**: If you want `www.cxsamaa.store` to redirect to `cxsamaa.store`, create a separate domain mapping for `www`
4. **CORS Origins**: Make sure to include all your domains in the `CORS_ORIGINS` secret

---

## 🆘 Troubleshooting

### Domain Mapping Fails
- Ensure the service exists and is running
- Verify domain ownership in Google Cloud Console
- Check that you have permission to manage the domain

### SSL Certificate Pending
- Wait 10-30 minutes
- Verify DNS records are correct
- Check domain verification status

### 404 Errors
- Ensure the service is deployed and healthy
- Check service URLs with: `gcloud run services describe <service-name>`
- Verify domain mapping points to correct service

---

## 🎯 Next Steps

After domain setup:
1. Test all three services via their custom domains
2. Update CORS settings if needed
3. Set up CDN caching for the landing page
4. Configure monitoring and alerting
5. Set up custom domain in your app's environment variables
