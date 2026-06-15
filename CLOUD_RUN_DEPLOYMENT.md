# Cloud Run Deployment Guide

## Overview

This guide covers deploying the SAMAA AI Pipeline to Google Cloud Run with the following architecture:

- **API Service** (1 CPU, 1GB RAM) - FastAPI backend serving the web app and handling uploads
- **Worker Service** (4 CPU, 8GB RAM) - Cloud Run service processing audio pipeline stages
- **Frontend Service** (1 CPU, 512MB RAM) - Next.js standalone web application
- **Cloud SQL** - PostgreSQL 15 managed database
- **Cloud Tasks** - Orchestration for chained pipeline stages
- **Upstash Redis** - Managed Redis for caching and session management
- **Cloudflare R2** - Object storage for audio files

## Architecture

### Chained Cloud Tasks Pattern

To bypass Cloud Run's 60-minute HTTP timeout, the audio processing pipeline uses **chained Cloud Tasks**:

```
Upload → Cloud Task (preprocess) → Cloud Task (STT) → Cloud Task (diarization) → ... → Complete
```

Each stage:
1. Receives an HTTP request from Cloud Tasks
2. Processes for ~2-10 minutes (well under 600s timeout)
3. Enqueues the next stage via Cloud Tasks API
4. Returns HTTP 200

This allows processing **9-hour recordings** without timeout issues.

### Pipeline Stages

1. **preprocess** - Audio validation and chunking
2. **STT** - Speech-to-text transcription (parallel chunks via ThreadPoolExecutor)
3. **diarization** - Speaker identification (parallel chunks via ThreadPoolExecutor)
4. **turns** - Conversation turn building
5. **roles** - Speaker role classification
6. **segmentation** - Conversation segmentation
7. **stitch** - Audio stitching
8. **analyze** - Conversation analysis
9. **scoring** - Salesperson performance scoring

## Prerequisites

1. **Google Cloud SDK** installed (`gcloud`)
2. **GCP Project** with billing enabled
3. **Docker** installed (for local testing)
4. **Node.js 20+** (for frontend)
5. **Python 3.11+** (for API)

## Quick Start

### 1. Setup GCP Infrastructure

```bash
# Set your GCP project ID
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1
export DOMAIN=cxsamaa.store
export DB_PASSWORD=your-secure-password

# Run infrastructure setup
./setup-gcp-infrastructure.sh
```

This script will:
- Enable required APIs
- Create Cloud SQL database
- Create Cloud Tasks queue
- Create service accounts
- Setup Secret Manager
- Create domain mapping

### 2. Configure Environment Variables

#### API Configuration

```bash
cp apps/api/.env.prod.example apps/api/.env.prod
```

Edit `apps/api/.env.prod` with your values:

```env
# Database (Cloud SQL)
DATABASE_URL=postgresql+asyncpg://samaa:YOUR_PASSWORD@/samaa?host=/cloudsql/YOUR_PROJECT:us-central1:samaa-db

# Redis (Upstash)
REDIS_URL=rediss://default:YOUR_PASSWORD@YOUR_REDIS.upstash.io:6379

# GCP Cloud Run & Cloud Tasks
GCP_PROJECT=your-project-id
GCP_REGION=us-central1
WORKER_URL=https://samaa-worker-xxxxx-uc.a.run.app  # Will be updated by deploy.sh
GCP_WORKER_SA_EMAIL=samaa-worker-sa@YOUR_PROJECT.iam.gserviceaccount.com
PIPELINE_VERSION=v1
CLOUD_TASKS_QUEUE=pipeline-queue

# ... (NVIDIA, Deepgram, R2, etc.)
```

#### Frontend Configuration

```bash
cp apps/web/.env.prod.example apps/web/.env.prod
```

Edit `apps/web/.env.prod`:

```env
NEXT_PUBLIC_API_URL=https://samaa-api-xxxxx-uc.a.run.app  # Will be updated by deploy.sh
```

### 3. Deploy

#### Option A: Using deploy.sh (Recommended)

```bash
export GCP_PROJECT_ID=your-project-id
export TAG=v1.0.0

./deploy.sh
```

This will:
1. Verify prerequisites
2. Run database migrations
3. Deploy Worker service
4. Deploy API service (with Worker URL injected)
5. Deploy Frontend service (with API URL injected)
6. Setup custom domain mapping

#### Option B: Using Cloud Build (CI/CD)

```bash
# Trigger Cloud Build
gcloud builds submit --config cloudbuild.yaml --substitutions=_TAG=v1.0.0,_REGION=us-central1
```

This will:
1. Build all 3 Docker images
2. Push to Google Container Registry
3. Deploy all services to Cloud Run
4. Run database migrations

### 4. Verify Deployment

```bash
# List all services
gcloud run services list --region=us-central1

# Check service URLs
gcloud run services describe samaa-api --region=us-central1 --format="value(status.url)"
gcloud run services describe samaa-worker --region=us-central1 --format="value(status.url)"
gcloud run services describe samaa-web --region=us-central1 --format="value(status.url)"

# View logs
gcloud run services logs read samaa-api --region=us-central1 --limit=50
gcloud run services logs read samaa-worker --region=us-central1 --limit=50

# Check Cloud Tasks queue
gcloud tasks queues describe pipeline-queue --location=us-central1
```

### 5. Test the Application

1. **Visit the frontend**: `https://cxsamaa.store`
2. **Upload a test audio file**
3. **Monitor pipeline progress**:
   ```bash
   # View task queue stats
   gcloud tasks queues list --location=us-central1
   ```

## Manual Deployment Steps

If you need to deploy services individually:

### Build Images Locally

```bash
# API
docker build -t gcr.io/YOUR_PROJECT/samaa-api:latest -f apps/api/Dockerfile apps/api/

# Worker
docker build -t gcr.io/YOUR_PROJECT/samaa-worker:latest -f apps/api/Dockerfile.worker apps/api/

# Frontend
docker build -t gcr.io/YOUR_PROJECT/samaa-web:latest -f apps/web/Dockerfile apps/web/
```

### Push to GCR

```bash
docker push gcr.io/YOUR_PROJECT/samaa-api:latest
docker push gcr.io/YOUR_PROJECT/samaa-worker:latest
docker push gcr.io/YOUR_PROJECT/samaa-web:latest
```

### Deploy Services

```bash
# Deploy Worker
gcloud run deploy samaa-worker \
  --image=gcr.io/YOUR_PROJECT/samaa-worker:latest \
  --region=us-central1 \
  --cpu=4 --memory=8Gi \
  --concurrency=1 --timeout=600 \
  --env-vars-file=apps/api/.env.prod \
  --no-allow-unauthenticated

# Deploy API
gcloud run deploy samaa-api \
  --image=gcr.io/YOUR_PROJECT/samaa-api:latest \
  --region=us-central1 \
  --cpu=1 --memory=1Gi \
  --concurrency=50 --timeout=300 \
  --env-vars-file=apps/api/.env.prod \
  --allow-unauthenticated

# Deploy Frontend
gcloud run deploy samaa-web \
  --image=gcr.io/YOUR_PROJECT/samaa-web:latest \
  --region=us-central1 \
  --cpu=1 --memory=512Mi \
  --concurrency=80 --timeout=60 \
  --env-vars-file=apps/web/.env.prod \
  --allow-unauthenticated
```

## DNS Setup

After deployment, you need to configure DNS for your domain:

1. **Get the Cloud Run domain verification code**:
   ```bash
   gcloud run domain-mappings describe --domain=cxsamaa.store --region=us-central1
   ```

2. **Add DNS records** at your domain registrar:
   - **A record**: Points to Cloud Run load balancer IP
   - **TXT record**: Google verification code

3. **Wait for propagation** (5-30 minutes)

4. **Verify HTTPS**:
   ```bash
   curl -I https://cxsamaa.store
   ```

## Monitoring

### Cloud Logging

```bash
# View all logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# API logs
gcloud logging read 'resource.type=cloud_run_revision resource.labels.service_name="samaa-api"' --limit=50

# Worker logs
gcloud logging read 'resource.type=cloud_run_revision resource.labels.service_name="samaa-worker"' --limit=50
```

### Cloud Tasks Monitoring

```bash
# Queue stats
gcloud tasks queues describe pipeline-queue --location=us-central1

# List pending tasks
gcloud tasks list --queue=pipeline-queue --location=us-central1
```

### Metrics

```bash
# Service metrics
gcloud run services describe samaa-api --region=us-central1

# View in GCP Console
open "https://console.cloud.google.com/run/detail/us-central1/samaa-api/metrics"
```

## Scaling

### Current Configuration

| Service | CPU | Memory | Min | Max | Concurrency | Timeout |
|---------|-----|--------|-----|-----|-------------|---------|
| API | 1 | 1GB | 0 | 5 | 50 | 5 min |
| Worker | 4 | 8GB | 0 | 10 | 1 | 10 min |
| Frontend | 1 | 512MB | 0 | 5 | 80 | 1 min |

### Cost Optimization

- **Scale to zero**: Min instances = 0 (no traffic = $0)
- **Pay per use**: Only charged during active requests
- **Estimated cost**: ~$1.80/mo fixed + $0.07/recording

### Scaling Up

For higher throughput:

```bash
# Increase Worker concurrency (if RAM allows)
gcloud run services update samaa-worker --concurrency=2 --region=us-central1

# Increase max instances
gcloud run services update samaa-api --max-instances=10 --region=us-central1

# Increase CPU/memory for Worker
gcloud run services update samaa-worker --cpu=8 --memory=16Gi --region=us-central1
```

## Troubleshooting

### Worker Timeout

If you see `HTTP 504` errors:

```bash
# Increase timeout
gcloud run services update samaa-worker --timeout=900 --region=us-central1
```

### Database Migration Failures

```bash
# Run migrations manually
gcloud run jobs run samaa-migrations --region=us-central1

# Check migration logs
gcloud run jobs logs read samaa-migrations --region=us-central1
```

### Cloud Tasks Failures

```bash
# Check failed tasks
gcloud tasks list --queue=pipeline-queue --location=us-central1 --filter="status:FAILED"

# Purge and recreate queue (if needed)
gcloud tasks queues delete pipeline-queue --location=us-central1
gcloud tasks queues create pipeline-queue --location=us-central1
```

### Service Unreachable

```bash
# Check service status
gcloud run services describe samaa-api --region=us-central1

# Check IAM permissions
gcloud run services get-iam-policy samaa-api --region=us-central1

# Verify service account has run.invoker role
gcloud projects get-iam-policy YOUR_PROJECT --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:samaa-worker-sa@YOUR_PROJECT.iam.gserviceaccount.com"
```

## Cleanup

To remove all deployed resources:

```bash
# Delete services
gcloud run services delete samaa-api --region=us-central1
gcloud run services delete samaa-worker --region=us-central1
gcloud run services delete samaa-web --region=us-central1

# Delete Cloud Tasks queue
gcloud tasks queues delete pipeline-queue --location=us-central1

# Delete Cloud SQL (caution: destroys data)
gcloud sql instances delete samaa-db --region=us-central1
```

## Local Development

### API

```bash
cd apps/api
uv pip install -e '.[dev]'
uvicorn src.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

### Test Pipeline Locally

```bash
# Start API
uvicorn src.main:app --reload --port 8000

# Upload audio file via web UI or API
curl -X POST http://localhost:8000/api/recordings/upload \
  -F "file=@test-recording.wav" \
  -F "title=Test Recording"
```

## Next Steps

1. **Setup CI/CD**: Connect Cloud Build to your Git repository
2. **Enable Cloud Monitoring**: Set up alerts for failures
3. **Configure backup**: Automated Cloud SQL backups
4. **Load testing**: Test with multiple concurrent uploads
5. **Domain migration**: Point cxsamaa.store DNS to Cloud Run

---

**Domain**: cxsamaa.store  
**Region**: us-central1  
**Last Updated**: 2025-02-15
