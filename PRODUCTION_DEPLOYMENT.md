# Production Deployment Guide: Managed Services Architecture

## Architecture Overview

```
Users
   │
   ▼
Nginx (Oracle VM)
   │
   ├── Next.js (Frontend)
   │
   └── FastAPI (Backend)
           │
           ├── Neon PostgreSQL (managed)
           │
           ├── Upstash Redis (managed)
           │
           └── Cloudflare R2 (audio storage)
```

**Oracle VM runs:**
- Nginx (reverse proxy)
- Next.js (frontend)
- FastAPI (backend API)
- Celery (worker for audio processing)

**Managed Services:**
- Neon PostgreSQL (database)
- Upstash Redis (message broker + cache)
- Cloudflare R2 (audio file storage)
- NVIDIA Riva / Groq (speech-to-text)
- DeepSeek (LLM analysis)

---

## Step 1: Configure Neon PostgreSQL

### 1.1 Create Neon Project

1. Go to [neon.tech](https://neon.tech)
2. Sign up and create a new project
3. Copy the connection string:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname?sslmode=require
DATABASE_URL_SYNC=postgresql://user:password@host/dbname?sslmode=require
```

### 1.2 Test Connection

```bash
cd apps/api
source .venv/bin/activate
alembic upgrade head
```

If migrations succeed, Neon is connected.

---

## Step 2: Configure Upstash Redis

### 2.1 Create Upstash Database

1. Go to [upstash.com](https://upstash.com)
2. Create a new Redis database
3. Copy credentials:

```env
UPSTASH_REDIS_REST_URL=https://your-org.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token
REDIS_URL=rediss://default:password@host:port
```

### 2.2 Verify Redis Connection

```python
import redis
r = redis.from_url("rediss://default:password@host:port")
r.ping()  # Should return True
```

---

## Step 3: Configure Cloudflare R2

### 3.1 Create R2 Bucket

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Navigate to R2 Storage
3. Create bucket: `samaa-audio`
4. Create API token with R2 access

### 3.2 Get Credentials

```env
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET=samaa-audio
```

### 3.3 Test Upload

```python
import boto3
from botocore.config import Config

s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version='s3v4')
)

s3.upload_file('test.wav', R2_BUCKET, 'test.wav')
```

---

## Step 4: Direct R2 Upload from Client

**Recommended architecture:** Upload audio files directly from mobile/web app to R2, bypassing the Oracle VM.

### Benefits:
- Less VM bandwidth usage
- Faster uploads (direct to Cloudflare edge)
- Scales better with concurrent users
- Reduces VM storage requirements

### Implementation:

1. **Backend generates presigned URL:**

```python
from fastapi import APIRouter
import boto3

router = APIRouter()

@router.post("/recordings/upload-url")
async def get_upload_url(filename: str):
    s3 = boto3.client('s3', ...)
    url = s3.generate_presigned_post(
        Bucket=R2_BUCKET,
        Key=f"recordings/{filename}",
        ExpiresIn=3600
    )
    return url
```

2. **Client uploads directly to R2:**

```javascript
// Mobile/Web app uploads directly
const response = await fetch(`${API_URL}/recordings/upload-url`, {
  method: 'POST',
  body: JSON.stringify({ filename: 'recording.wav' })
});

const { url, fields } = await response.json();

const formData = new FormData();
Object.entries(fields).forEach(([key, value]) => {
  formData.append(key, value);
});
formData.append('file', audioFile);

await fetch(url, {
  method: 'POST',
  body: formData
});
```

3. **Client notifies backend:**

```javascript
await fetch(`${API_URL}/recordings`, {
  method: 'POST',
  body: JSON.stringify({
    r2_key: `recordings/${filename}`,
    metadata: { ... }
  })
});
```

---

## Step 5: Celery Worker Configuration

### Where Transcription Runs

**Option A: Oracle VM orchestrates (Recommended initially)**

```
Upload → R2 → Celery → Groq/NVIDIA API → Results saved
```

- Oracle VM runs Celery worker
- Celery downloads audio from R2
- Sends to Groq/NVIDIA for STT
- Saves results back to Neon

**Option B: Run Parakeet locally (Not recommended)**

Oracle Free VM (4 ARM CPUs, 24GB RAM) is too weak for real-time transcription.

**Option C: GPU worker (Best long-term)**

```
Oracle VM → Queue → RunPod GPU Worker → Results
```

- Oracle VM queues jobs
- Separate GPU worker (RunPod, Lambda Labs) processes audio
- Results sent back via webhook

### Systemd Service

Create `/etc/systemd/system/samaa-celery.service`:

```ini
[Unit]
Description=SAMAA Celery Worker
After=network.target

[Service]
Type=simple
User=samaa
Group=samaa
WorkingDirectory=/opt/samaa/apps/api
Environment="PATH=/opt/samaa/apps/api/.venv/bin"
ExecStart=/opt/samaa/apps/api/.venv/bin/celery -A src.workers.celery_app worker --loglevel=info --pool=solo
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable samaa-celery
sudo systemctl start samaa-celery
sudo systemctl status samaa-celery
```

---

## Step 6: Production Services (systemd)

### 6.1 FastAPI Service

`/etc/systemd/system/samaa-api.service`:

```ini
[Unit]
Description=SAMAA FastAPI Backend
After=network.target

[Service]
Type=simple
User=samaa
Group=samaa
WorkingDirectory=/opt/samaa/apps/api
Environment="PATH=/opt/samaa/apps/api/.venv/bin"
ExecStart=/opt/samaa/apps/api/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.2 Next.js Service

`/etc/systemd/system/samaa-web.service`:

```ini
[Unit]
Description=SAMAA Next.js Frontend
After=network.target

[Service]
Type=simple
User=samaa
Group=samaa
WorkingDirectory=/opt/samaa/apps/web
Environment="PATH=/opt/samaa/apps/web/node_modules/.bin"
ExecStart=/opt/samaa/apps/web/node_modules/.bin/next start -p 3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.3 Enable All Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable samaa-api samaa-web samaa-celery
sudo systemctl start samaa-api samaa-web samaa-celery
```

---

## Step 7: Nginx Configuration

### 7.1 Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

### 7.2 Configure Reverse Proxy

`/etc/nginx/sites-available/samaa.ai`:

```nginx
# Frontend (Next.js)
server {
    listen 80;
    server_name samaa.ai www.samaa.ai;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Backend (FastAPI)
server {
    listen 80;
    server_name api.samaa.ai;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 7.3 Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/samaa.ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7.4 SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d samaa.ai -d www.samaa.ai -d api.samaa.ai
```

---

## Step 8: Oracle Free VM Sizing

### Typical Resources

- **4 ARM CPUs** (Ampere Altra)
- **24 GB RAM**
- **200 GB Storage**

### Resource Allocation

| Service | CPU | RAM | Notes |
|---------|-----|-----|-------|
| Nginx | 0.1 | 50 MB | Minimal overhead |
| Next.js | 0.5 | 500 MB | SSR + static serving |
| FastAPI | 1.0 | 1 GB | 4 workers (uvicorn) |
| Celery | 1.5 | 2 GB | Audio processing |
| System | 0.5 | 500 MB | OS + monitoring |
| **Total** | **3.6** | **4.05 GB** | Well within limits |

**Bottleneck:** Transcription (CPU-bound), not web app.

---

## Deployment Checklist

### Pre-Deployment

- [ ] Neon PostgreSQL created and tested
- [ ] Upstash Redis created and tested
- [ ] Cloudflare R2 bucket created
- [ ] NVIDIA API key configured
- [ ] DeepSeek API key configured
- [ ] `.env.prod` filled with production values
- [ ] Domain DNS pointed to Oracle VM IP

### Deployment Steps

```bash
# 1. SSH to Oracle VM
ssh -i ~/.ssh/samaa_key ubuntu@<oracle-vm-ip>

# 2. Clone repository
git clone <repo-url> /opt/samaa
cd /opt/samaa

# 3. Setup Python environment
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 4. Run migrations
alembic upgrade head

# 5. Setup Next.js
cd ../web
npm install
npm run build

# 6. Copy production env
cp .env.prod /opt/samaa/.env

# 7. Setup systemd services
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable samaa-api samaa-web samaa-celery
sudo systemctl start samaa-api samaa-web samaa-celery

# 8. Setup Nginx
sudo cp nginx/samaa.ai /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/samaa.ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 9. Setup SSL
sudo certbot --nginx -d samaa.ai -d www.samaa.ai -d api.samaa.ai

# 10. Verify
curl https://api.samaa.ai/docs
curl https://samaa.ai
```

### Post-Deployment

- [ ] API docs accessible: `https://api.samaa.ai/docs`
- [ ] Frontend loads: `https://samaa.ai`
- [ ] Celery worker running: `sudo systemctl status samaa-celery`
- [ ] Database migrations applied
- [ ] Test upload → transcription pipeline
- [ ] Monitor logs: `journalctl -u samaa-api -f`

---

## Monitoring

### Check Service Status

```bash
sudo systemctl status samaa-api samaa-web samaa-celery
```

### View Logs

```bash
journalctl -u samaa-api -f
journalctl -u samaa-web -f
journalctl -u samaa-celery -f
```

### Database Health

```bash
cd apps/api
source .venv/bin/activate
alembic current
```

### Redis Health

```bash
redis-cli -u rediss://default:password@host:port ping
```

---

## Cost Breakdown (Approximate)

| Service | Tier | Cost |
|---------|------|------|
| Oracle VM | Always Free | $0 |
| Neon PostgreSQL | Free tier (0.5 GB) | $0 |
| Upstash Redis | Free tier (256 MB) | $0 |
| Cloudflare R2 | Free tier (10 GB) | $0 |
| NVIDIA NIM | Pay-per-use | ~$0.05/hr audio |
| DeepSeek | Pay-per-use | ~$0.001/request |
| **Total** | | **~$0-5/month** |

---

## Troubleshooting

### Database Connection Fails

```bash
# Check SSL mode
echo $DATABASE_URL

# Test direct connection
psql "postgresql://user:password@host/dbname?sslmode=require"
```

### Redis Connection Fails

```bash
# Check URL format (must be rediss:// for TLS)
echo $REDIS_URL

# Test with redis-cli
redis-cli -u rediss://default:password@host:port ping
```

### Celery Not Processing Tasks

```bash
# Check worker logs
journalctl -u samaa-celery -f

# Check queue
redis-cli -u rediss://... llen celery

# Restart worker
sudo systemctl restart samaa-celery
```

### Audio Upload Fails

```bash
# Check R2 credentials
echo $R2_ACCOUNT_ID
echo $R2_BUCKET

# Test upload manually
python -c "import boto3; ..."
```

---

## Next Steps

1. **Implement direct R2 upload** from mobile app (presigned URLs)
2. **Add monitoring** (Prometheus + Grafana, or hosted service)
3. **Setup CI/CD** (GitHub Actions for auto-deploy)
4. **Scale GPU workers** (RunPod/Lambda Labs for transcription)
5. **Add CDN** for audio playback (Cloudflare R2 already includes CDN)
