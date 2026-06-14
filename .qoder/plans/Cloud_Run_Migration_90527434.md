# Cloud Run Migration Plan (Revised)

## Current Architecture
- Oracle Free VM (1 CPU, 1GB RAM) running FastAPI + Celery + Next.js + Nginx
- 15 Celery tasks across 9 worker files, using chord/group for parallel chunk processing
- Managed services: Neon PostgreSQL, Upstash Redis, Cloudflare R2

## Target Architecture
```
Next.js (Cloud Run Service) -- 1 CPU, 1 GB RAM
        |
        v
FastAPI (Cloud Run Service) -- 1 CPU, 1 GB RAM
        |
        v
Cloud Tasks (HTTP target)
        |
        v
Pipeline Worker (Cloud Run Service) -- 4 CPU, 8 GB RAM
        |
        +--> R2 (audio storage)
        +--> Neon PostgreSQL (data)
        +--> Upstash Redis (optional caching)
        +--> NVIDIA NIM APIs (STT/LLM)

Custom domain: cxsamaa.store (Cloud Run domain mapping)
```

**Why Cloud Tasks over Pub/Sub + Jobs:**
- Cloud Tasks directly invokes a Cloud Run Service via HTTP -- no intermediary needed
- Built-in retry policies, rate limiting, and dead-letter queues
- Simpler to operate than Pub/Sub subscription -> Job orchestration
- Worker is a regular Cloud Run Service (easier to debug, logs in Cloud Logging)

---

## Task 1: Add tenacity dependency and retry utility

Add `tenacity` to `apps/api/pyproject.toml`.

Create `apps/api/src/workers/retry.py`:
```python
"""Shared retry decorator for pipeline operations."""
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

pipeline_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True,
)
```

---

## Task 2: Refactor Celery tasks to plain Python functions (preserve parallelism)

**Scope**: 15 Celery tasks in 9 files under `apps/api/src/workers/`

### Chunk dispatchers -- use ThreadPoolExecutor (preserve parallelism)

**`transcription.py`** -- Replace `dispatch_transcription` chord/group:
```python
from concurrent.futures import ThreadPoolExecutor

def dispatch_transcription(recording_id: str) -> dict:
    """Process chunks in parallel, preserving Celery chord semantics."""
    manifest = load_manifest(recording_id)
    num_chunks = manifest["num_chunks"]

    if num_chunks == 1:
        return transcribe_chunk(recording_id, 0)

    with ThreadPoolExecutor(max_workers=min(num_chunks, 4)) as executor:
        futures = [
            executor.submit(transcribe_chunk, recording_id, chunk_id)
            for chunk_id in range(num_chunks)
        ]
        results = [f.result() for f in futures]

    return merge_transcription_results(results, recording_id)
```

**`diarization.py`** -- Same ThreadPoolExecutor pattern for `dispatch_diarization`.

### Individual tasks -- remove decorators, add tenacity

All 9 worker files:
- Remove `@celery_app.task(bind=True, ...)` decorators
- Remove `self` parameter from function signatures
- Replace `self.retry(exc=...)` with `@pipeline_retry` decorator or plain try/except
- Replace `Ignore()` returns with plain exceptions

Files affected: `preprocessing.py`, `transcription.py`, `diarization.py`, `turn_builder.py`, `role_classification.py`, `segmentation.py`, `audio_stitcher.py`, `analysis.py`, `scoring.py`

### Pipeline control

**`pipeline_control.py`** -- Remove `Ignore()` import. `PipelineHalted` stays as a plain exception. Callers catch it and log + exit cleanly.

### Celery app

**`celery_app.py`** -- Mark as deprecated. Remove after migration is verified.

---

## Task 3: Rewrite pipeline.py with explicit stages

Replace `chain(...).apply_async()` with an explicit, debuggable pipeline:

```python
"""Pipeline orchestration for audio processing -- Cloud Run edition."""
import logging
from src.workers.pipeline_control import PipelineHalted

logger = logging.getLogger(__name__)

def process_recording(recording_id: str) -> None:
    """Run the full audio processing pipeline for a single recording.

    Each stage is explicit for easier debugging and monitoring.
    """
    logger.info("[%s] Pipeline started", recording_id)

    try:
        # Stage 1: Normalize, resample, split into chunks
        preprocess_audio(recording_id)

        # Stage 2: Parallel chunk STT (ThreadPoolExecutor)
        transcription_result = dispatch_transcription(recording_id)

        # Stage 3: Parallel chunk diarization (ThreadPoolExecutor)
        diarization_result = dispatch_diarization(recording_id)

        # Stage 4: Merge words into speaker turns
        turns = build_conversation_turns(recording_id, transcription_result, diarization_result)

        # Stage 5: Identify Salesperson vs Customer
        classify_speaker_roles(recording_id, turns)

        # Stage 6: Split into discrete conversations
        conversations = segment_conversations(recording_id)

        # Stage 7: Extract per-conversation audio files
        stitch_conversation_audio(recording_id, conversations)

        # Stage 8: Llama 3.3 analysis
        analyze_conversations(recording_id, conversations)

        # Stage 9: Performance scoring
        score_salesperson(recording_id)

        logger.info("[%s] Pipeline completed successfully", recording_id)

    except PipelineHalted as e:
        logger.warning("[%s] Pipeline halted: %s", recording_id, e)
    except Exception as e:
        logger.error("[%s] Pipeline failed: %s", recording_id, e, exc_info=True)
        _update_recording_status(recording_id, "FAILED", str(e))
        raise
```

---

## Task 4: Create Cloud Run worker service

Create `apps/api/src/workers/worker_service.py` -- a lightweight FastAPI app that Cloud Tasks calls:

```python
"""Pipeline Worker -- Cloud Run Service triggered by Cloud Tasks."""
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import logging

worker_app = FastAPI(title="SAMAA Pipeline Worker")
logger = logging.getLogger(__name__)

class PipelineTask(BaseModel):
    recording_id: str
    pipeline_version: str = "v1"  # Future-proofing for prompt/scoring model changes

@worker_app.post("/process")
async def process(task: PipelineTask, request: Request):
    # Verify Cloud Tasks auth header
    auth_header = request.headers.get("X-CloudTasks-QueueName")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info("Processing recording %s (pipeline %s)", task.recording_id, task.pipeline_version)

    from src.workers.pipeline import process_recording
    process_recording(task.recording_id)

    return {"status": "completed", "recording_id": task.recording_id}
```

This runs as a separate Cloud Run Service with 4 CPU / 8 GB RAM, auto-scaling from 0.

---

## Task 5: Create Cloud Tasks integration in FastAPI

Replace the 2 `start_processing_pipeline()` call sites in `apps/api/src/services/recording.py`:

```python
from google.cloud import tasks_v2

def enqueue_pipeline(recording_id: str, pipeline_version: str = "v1"):
    """Queue a pipeline task via Cloud Tasks."""
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(settings.gcp_project, settings.gcp_region, "samaa-pipeline")

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{settings.worker_url}/process",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "recording_id": recording_id,
                "pipeline_version": pipeline_version,
            }).encode(),
            "oidc_token": {
                "service_account_email": settings.gcp_worker_sa_email,
            },
        },
        "dispatch_deadline": {"seconds": 3600},  # 60 min
    }
    client.create_task(parent=parent, task=task)
```

Add to `apps/api/pyproject.toml`: `google-cloud-tasks`.

Add to `.env.prod`:
```
GCP_PROJECT=your-gcp-project-id
GCP_REGION=us-central1
WORKER_URL=https://samaa-worker-xxxxx-uc.a.run.app
GCP_WORKER_SA_EMAIL=samaa-worker@your-gcp-project-id.iam.gserviceaccount.com
PIPELINE_VERSION=v1
```

---

## Task 6: Create Dockerfiles

**`apps/api/Dockerfile`** (FastAPI service -- 1 CPU, 1 GB):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN pip install uv && uv sync --no-dev --frozen
COPY apps/api/src ./src
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**`apps/api/Dockerfile.worker`** (Pipeline Worker -- 4 CPU, 8 GB):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN pip install uv && uv sync --no-dev --frozen
COPY apps/api/src ./src
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "src.workers.worker_service:worker_app", "--host", "0.0.0.0", "--port", "8080"]
```

**`apps/web/Dockerfile`** (Next.js -- 1 CPU, 1 GB):
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

---

## Task 7: Create cloudbuild.yaml for CI/CD

```yaml
steps:
  # Build all 3 images
  - name: gcr.io/cloud-builders/docker
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/samaa/api:$SHORT_SHA', '-f', 'apps/api/Dockerfile', '.']
  - name: gcr.io/cloud-builders/docker
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/samaa/worker:$SHORT_SHA', '-f', 'apps/api/Dockerfile.worker', '.']
  - name: gcr.io/cloud-builders/docker
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/samaa/web:$SHORT_SHA', '-f', 'apps/web/Dockerfile', '.']

  # Push
  - name: gcr.io/cloud-builders/docker
    args: ['push', '--all-tags', 'us-central1-docker.pkg.dev/$PROJECT_ID/samaa']

  # Deploy API (1 CPU, 1 GB)
  - name: gcr.io/cloud-builders/gcloud
    args: ['run', 'deploy', 'samaa-api',
      '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/samaa/api:$SHORT_SHA',
      '--region', 'us-central1',
      '--cpu', '1', '--memory', '1Gi',
      '--min-instances', '0', '--max-instances', '10',
      '--timeout', '300']

  # Deploy Worker (4 CPU, 8 GB)
  - name: gcr.io/cloud-builders/gcloud
    args: ['run', 'deploy', 'samaa-worker',
      '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/samaa/worker:$SHORT_SHA',
      '--region', 'us-central1',
      '--cpu', '4', '--memory', '8Gi',
      '--min-instances', '0', '--max-instances', '5',
      '--timeout', '3600',
      '--concurrency', '1']

  # Deploy Web (1 CPU, 1 GB)
  - name: gcr.io/cloud-builders/gcloud
    args: ['run', 'deploy', 'samaa-web',
      '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/samaa/web:$SHORT_SHA',
      '--region', 'us-central1',
      '--cpu', '1', '--memory', '1Gi',
      '--min-instances', '0', '--max-instances', '10']

images:
  - us-central1-docker.pkg.dev/$PROJECT_ID/samaa/api:$SHORT_SHA
  - us-central1-docker.pkg.dev/$PROJECT_ID/samaa/worker:$SHORT_SHA
  - us-central1-docker.pkg.dev/$PROJECT_ID/samaa/web:$SHORT_SHA

options:
  logging: CLOUD_LOGGING_ONLY
```

Update `.github/workflows/deploy.yml` to trigger Cloud Build via `gcloud builds submit`.

---

## Task 8: GCP Infrastructure Setup (one-time)

1. Create GCP project (or use existing)
2. Enable APIs: `run`, `cloudtasks`, `artifactregistry`, `cloudbuild`, `secretmanager`
3. Create Artifact Registry: `gcloud artifacts repositories create samaa --repository-format=docker --location=us-central1`
4. Create Cloud Tasks queue:
   ```bash
   gcloud tasks queues create samaa-pipeline \
     --location=us-central1 \
     --max-dispatches-per-second=10 \
     --max-concurrent-dispatches=5 \
     --max-attempts=3 \
     --min-backoff=10s \
     --max-backoff=300s
   ```
5. Create service accounts:
   - `samaa-api` -- can create Cloud Tasks, read Secret Manager
   - `samaa-worker` -- can read Secret Manager, invoked by Cloud Tasks
6. Add secrets to Secret Manager: `DATABASE_URL`, `REDIS_URL`, `R2_*`, `NVIDIA_API_KEY`, `JWT_SECRET`
7. Grant service accounts access to secrets
8. Set up Cloud Run domain mappings for `cxsamaa.store`
9. Update DNS CNAME to point to Cloud Run URL (not Oracle VM)

---

## Task 9: Update environment configuration

`.env.prod` additions:
```
GCP_PROJECT=your-gcp-project-id
GCP_REGION=us-central1
WORKER_URL=https://samaa-worker-xxxxx-uc.a.run.app
GCP_WORKER_SA_EMAIL=samaa-worker@your-gcp-project-id.iam.gserviceaccount.com
PIPELINE_VERSION=v1
```

Remove (no longer needed):
- `CELERY_*` variables (if any)
- Upstash Redis is optional (keep for caching, drop if not needed)

---

## Task 10: Rewrite deploy.sh for Cloud Run

Replace SSH-based deploy.sh with gcloud commands:
```bash
gcloud builds submit --config cloudbuild.yaml .
gcloud run services update samaa-api --region us-central1 --update-env-vars ...
gcloud run services update samaa-worker --region us-central1 --update-env-vars ...
gcloud run services update samaa-web --region us-central1 --update-env-vars ...
```

---

## Task 11: Testing strategy

1. Test refactored pipeline locally with `ThreadPoolExecutor` (no Celery)
2. Deploy API service to Cloud Run, verify `/health` and CRUD endpoints
3. Deploy worker service, trigger manually with Cloud Tasks `gcloud tasks queues force-run`
4. Deploy frontend, verify full upload -> process -> view flow
5. Verify Cloud Tasks auto-dispatch from API -> Worker
6. Test with a long recording (60+ min audio) to verify timeout handling
7. Verify horizontal scaling: queue 10 recordings simultaneously

---

## Estimated effort

| Task | Complexity | Files |
|------|-----------|-------|
| 1. Retry utility (tenacity) | Low | 2 files |
| 2. Refactor tasks (ThreadPoolExecutor) | High | 11 files in `src/workers/` |
| 3. Explicit pipeline stages | Medium | `pipeline.py`, `pipeline_control.py` |
| 4. Worker service (FastAPI) | Low | 1 new file |
| 5. Cloud Tasks integration | Medium | `recording.py`, `config.py`, `pyproject.toml` |
| 6. Dockerfiles | Low | 3 new files |
| 7. cloudbuild.yaml + deploy.yml | Medium | 2 files |
| 8. GCP infrastructure | Medium | Manual gcloud commands |
| 9. Environment config | Low | `.env.prod` |
| 10. deploy.sh rewrite | Medium | 1 file |
| 11. Testing | High | End-to-end |

## Key decisions to confirm

1. **Region**: `us-central1` (Iowa) -- cheapest Cloud Run region
2. **Keep Oracle VM** as fallback during migration, or decommission immediately?
3. **Worker concurrency**: `--concurrency 1` (one recording at a time per instance, scale to 5 instances) -- good trade-off?
