# SAMAA — Sales Audio Management & AI Analysis

SAMAA is a full-stack platform for uploading, transcribing, diarizing, analyzing, and scoring sales call recordings. It uses NVIDIA NIM APIs for STT/diarization/LLM and provides a dashboard for browsing conversations, metrics, and exports.

---

## Screenshots

### Authentication

![Login View](screenshots/auth-view/auth.png)

### Interaction Details

![Interaction Details 1](screenshots/dashboard-view/interaction-details-1.png)
![Interaction Details 2](screenshots/dashboard-view/interaction-details-2.png)
![Recording Details](screenshots/dashboard-view/interaction-recording-details.png)
![Coaching View](screenshots/dashboard-view/coaching.png)

### Features

![Recording List](screenshots/dashboard-view/recording-list.png)
![Conversation List](screenshots/dashboard-view/conversation-list.png)
![Salespeople List](screenshots/dashboard-view/salespeople-list.png)
![Stores List](screenshots/dashboard-view/stores-list.png)


### Dashboard Views

![Brand Dashboard 1](screenshots/dashboard-view/brand-1.png)
![Brand Dashboard 2](screenshots/dashboard-view/brand-2.png)
![Brand Dashboard 3](screenshots/dashboard-view/brand-3.png)




### Operations

![Operations Page](screenshots/ops-view/ops-page.png)

---

## Architecture

```
xsamaa-ai-pipeline/
├── apps/
│   ├── api/        ← FastAPI backend (Python 3.12+, Celery workers)
│   └── web/        ← Next.js 16 frontend (React 19, Tailwind CSS, shadcn/ui)
├── packages/
│   └── shared/     ← Shared TypeScript types between web and monorepo
├── docker-compose.yml   ← PostgreSQL (pgvector) + Redis
└── turbo.json           ← Turborepo config
```

### Processing Pipeline

Audio uploads flow through a Celery-based pipeline:

**Preprocessing → Transcription (STT) → Diarization → Segmentation → Analysis (LLM) → Scoring**

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | ≥ 3.12 | Backend API & workers |
| Node.js | ≥ 20 | Frontend (Next.js) |
| npm | ≥ 10 | Workspaces + Turborepo |
| Docker & Docker Compose | v2+ | PostgreSQL + Redis |
| ffmpeg | latest | Audio preprocessing (pydub) |
| uv | latest | Python package manager for the API |

---

## Quick Start

### 1. Clone & install infrastructure

```bash
git clone <repo-url> && cd xsamaa-ai-pipeline

# Start PostgreSQL (pgvector/pgvector:pg16) and Redis 7
docker compose up -d
```

### 2. Configure environment variables

```bash
# Root .env — copy from example and edit
cp .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Required | Default |
|----------|----------|---------|
| `DATABASE_URL` | No | `postgresql+asyncpg://samaa:samaa_dev_password@localhost:5432/samaa` |
| `REDIS_URL` | No | `redis://localhost:6379/0` |
| `NVIDIA_API_KEY` | **Yes** | — (get from [NVIDIA NIM](https://build.nvidia.com/)) |
| `JWT_SECRET` | **Yes** (prod) | `change-me-to-a-random-secret-in-production` |
| `STORAGE_BACKEND` | No | `local` |
| `LOCAL_UPLOAD_DIR` | No | `./uploads` |

The frontend reads its API URL from `apps/web/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Set up the API

```bash
cd apps/api

# Create a virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Symlink the root .env so the API can read it
ln -sf ../../.env .env

# Run database migrations
alembic upgrade head

# (Optional) Seed the database with sample data
python scripts/seed.py
```

> **Note:** The API's config (`pydantic-settings`) reads `.env` from the current working directory.
> The symlink ensures it picks up the root-level `.env` you created in step 2.

### 4. Set up the frontend

```bash
# From the repo root
npm install
```

---

## Running the Apps

### Option A: Auto-start everything (recommended)

```bash
./start_servers.sh
```

This single command handles everything:
1. Checks prerequisites (Docker, Node.js, Python deps)
2. Copies `.env.example` → `.env` if missing
3. Symlinks `.env` into `apps/api/`
4. Starts PostgreSQL + Redis via Docker Compose
5. Waits for databases to be ready
6. Runs Alembic migrations
7. Launches FastAPI, Celery worker, and Next.js
8. Logs go to `.logs/` directory

Press **Ctrl+C** to stop all services.

### Option B: Manual (separate terminals)

You need **4 processes** running. Open separate terminals:

#### Terminal 1 — Infrastructure (if not already running)

```bash
docker compose up -d
```

#### Terminal 2 — FastAPI server

```bash
cd apps/api
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Terminal 3 — Celery worker (pipeline processing)

```bash
cd apps/api
source .venv/bin/activate
celery -A src.workers.celery_app worker --loglevel=info --concurrency=4
```

#### Terminal 4 — Next.js frontend

```bash
# From the repo root
npm run dev:web
```

Frontend: [http://localhost:3000](http://localhost:3000)

### Default Login (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Super Admin | `admin@samaa.com` | `admin123` |
| Brand Admin | `brand@retailmax.com` | `brand123` |
| Store Manager | `manager@retailmax.com` | `manager123` |
| Salesperson | `alice@retailmax.com` | `sales123` |

---

## Project Structure

### Backend (`apps/api/`)

| Directory | Purpose |
|-----------|---------|
| `src/api/v1/` | Route handlers (auth, brands, conversations, recordings, etc.) |
| `src/models/` | SQLAlchemy ORM models |
| `src/schemas/` | Pydantic request/response schemas |
| `src/services/` | Business logic layer |
| `src/ai/` | NVIDIA NIM API clients (STT, diarization, analysis, scoring) |
| `src/workers/` | Celery tasks for the async processing pipeline |
| `src/storage/` | File storage abstraction (local / S3) |
| `alembic/` | Database migrations |

### Frontend (`apps/web/`)

| Directory | Purpose |
|-----------|---------|
| `src/app/` | Next.js App Router pages (auth, dashboard) |
| `src/components/` | React components (features, layout, UI primitives) |
| `src/lib/` | API client, utilities |
| `src/store/` | Zustand state management (auth) |

### Shared (`packages/shared/`)

TypeScript types shared between the frontend and the monorepo. Imported as `@samaa/shared`.

---

## Database Migrations

```bash
cd apps/api
source .venv/bin/activate

# Create a new migration after changing models
alembic revision --autogenerate -m "describe your change"

# Apply pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

---

## Testing

```bash
cd apps/api
source .venv/bin/activate
pytest
```

---

## Storage

By default, audio files are stored locally in `./uploads` (configurable via `LOCAL_UPLOAD_DIR`).

To use S3-compatible storage (AWS S3, Cloudflare R2, etc.), set in `.env`:

```env
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_S3_BUCKET=<your-bucket>
AWS_S3_REGION=us-east-1
AWS_S3_ENDPOINT=<optional-endpoint-for-r2>
```

---

## Tech Stack

**Backend:** FastAPI · SQLAlchemy (async) · Celery · Redis · PostgreSQL + pgvector · Alembic · NVIDIA NIM APIs · pydub

**Frontend:** Next.js 16 · React 19 · Tailwind CSS 4 · shadcn/ui · TanStack Query · Zustand · Recharts

**Monorepo:** Turborepo · npm workspaces

---

## Environment Reference

<details>
<summary>Full <code>.env</code> variable list</summary>

```env
# Database
DATABASE_URL=postgresql+asyncpg://samaa:samaa_dev_password@localhost:5432/samaa
DATABASE_URL_SYNC=postgresql://samaa:samaa_dev_password@localhost:5432/samaa

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=change-me-to-a-random-secret-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Storage (local or s3)
STORAGE_BACKEND=local
LOCAL_UPLOAD_DIR=./uploads

# S3 (when STORAGE_BACKEND=s3)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_S3_BUCKET=
# AWS_S3_REGION=us-east-1
# AWS_S3_ENDPOINT=

# NVIDIA NIM
NVIDIA_API_KEY=
NVIDIA_STT_MODEL=parakeet-rnnt-1.1b
NVIDIA_DIARIZATION_MODEL=streusand-rnnt
NVIDIA_LLM_MODEL=meta/llama-3.3-70b-instruct

# Application
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000

# CORS
CORS_ORIGINS=http://localhost:3000
```

</details>
