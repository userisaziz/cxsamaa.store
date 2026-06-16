# CXSAMAA — Architecture & Design Document

**Version:** 1.0  
**Status:** Approved  
**Date:** 2026-06-09  

---

## 1. Executive Summary

CXSAMAA (Sales Audio Management & AI Analysis) is an enterprise intelligence platform that transforms raw retail store audio recordings into structured business intelligence. This document defines the complete system architecture, technology choices, folder structure, database schema, API design, AI pipeline, and frontend design.

### Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Repository structure | Monorepo (Turborepo) | Shared types, single PR workflow, easier refactoring |
| Backend framework | FastAPI (Python) | AI/ML ecosystem native, async performance, Celery integration |
| ORM | SQLAlchemy + Alembic | Mature, powerful, best Python ORM for complex schemas |
| Job queue | Celery + Redis | Battle-tested for heavy multi-stage data pipelines |
| AI runtime | NVIDIA hosted APIs (NIM) | No GPU infrastructure needed for MVP, pay-per-use |
| File storage | Local FS + storage abstraction | Fast local dev, swap to S3/R2 via interface later |
| Frontend | Next.js + TypeScript | SSR, App Router, great DX |
| UI components | shadcn/ui + Tailwind CSS | Modern, accessible, customizable |
| State management | Zustand + TanStack Query | Lightweight client state, powerful server state caching |
| Database | PostgreSQL + pgvector | Relational data + vector similarity search |

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                     │
│              Port 3000 · App Router · SSR                │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────┐
│                   API Server (FastAPI)                    │
│              Port 8000 · REST endpoints                  │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │   Auth   │  Brands  │  Stores  │  Recordings      │  │
│  │  Module  │  Module  │  Module  │  Module          │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
└──────────┬───────────────────────────────┬──────────────┘
           │                               │
    ┌──────▼──────┐              ┌─────────▼─────────┐
    │ PostgreSQL  │              │     Redis          │
    │  + pgvector │              │  (Celery broker)   │
    │  Port 5432  │              │  Port 6379         │
    └─────────────┘              └─────────┬─────────┘
                                           │
                           ┌───────────────▼───────────────┐
                           │     Celery Workers             │
                           │  (AI Pipeline Processing)      │
                           │  ┌─────────┐ ┌─────────────┐  │
                           │  │Preprocess│ │ Transcribe  │  │
                           │  └─────────┘ └─────────────┘  │
                           │  ┌─────────┐ ┌─────────────┐  │
                           │  │ Diarize │ │  Segment    │  │
                           │  └─────────┘ └─────────────┘  │
                           │  ┌─────────┐ ┌─────────────┐  │
                           │  │ Analyze │ │   Score     │  │
                           │  └─────────┘ └─────────────┘  │
                           └───────────────┬───────────────┘
                                           │ HTTPS
                           ┌───────────────▼───────────────┐
                           │    NVIDIA NIM APIs             │
                           │  Parakeet STT · NeMo Diarize  │
                           │  Llama 3.3 Analysis           │
                           └───────────────────────────────┘
```

### Sub-Project Decomposition

| Sub-Project | Description | Dependencies |
|---|---|---|
| **Backend Platform** | FastAPI server, DB schema, auth, CRUD APIs, file upload, Celery workers | None (foundation) |
| **AI Pipeline** | NVIDIA API integrations, processing workers, conversation analysis | Backend Platform |
| **Frontend Platform** | Next.js dashboards, recording viewer, search, coaching | Backend Platform APIs |

---

## 3. Monorepo Folder Structure

```
xsamaa-ai-pipeline/
├── turbo.json                          ← Turborepo config
├── package.json                        ← Root monorepo (workspaces)
├── docker-compose.yml                  ← PostgreSQL + Redis + MinIO
├── .env.example                        ← Environment variables template
├── .gitignore
│
├── apps/
│   ├── api/                            ← FastAPI backend application
│   │   ├── pyproject.toml              ← Python deps (Poetry or uv)
│   │   ├── Dockerfile
│   │   ├── alembic.ini                 ← Alembic config
│   │   ├── alembic/                    ← DB migrations
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── main.py                 ← FastAPI app entrypoint
│   │       ├── config.py              ← pydantic-settings config
│   │       ├── database.py            ← SQLAlchemy engine & session
│   │       │
│   │       ├── models/                ← SQLAlchemy ORM models
│   │       │   ├── __init__.py
│   │       │   ├── user.py
│   │       │   ├── brand.py
│   │       │   ├── store.py
│   │       │   ├── salesperson.py
│   │       │   ├── recording.py
│   │       │   ├── transcript.py
│   │       │   ├── conversation.py
│   │       │   └── metrics.py
│   │       │
│   │       ├── schemas/               ← Pydantic request/response schemas
│   │       │   ├── __init__.py
│   │       │   ├── auth.py
│   │       │   ├── brand.py
│   │       │   ├── store.py
│   │       │   ├── salesperson.py
│   │       │   ├── recording.py
│   │       │   └── conversation.py
│   │       │
│   │       ├── api/                   ← Route handlers
│   │       │   ├── __init__.py
│   │       │   ├── deps.py            ← Dependencies (auth, db session)
│   │       │   └── v1/
│   │       │       ├── __init__.py
│   │       │       ├── router.py      ← V1 API router aggregation
│   │       │       ├── auth.py
│   │       │       ├── brands.py
│   │       │       ├── stores.py
│   │       │       ├── salespeople.py
│   │       │       ├── recordings.py
│   │       │       ├── conversations.py
│   │       │       └── search.py
│   │       │
│   │       ├── services/              ← Business logic layer
│   │       │   ├── __init__.py
│   │       │   ├── auth.py
│   │       │   ├── brand.py
│   │       │   ├── store.py
│   │       │   ├── salesperson.py
│   │       │   ├── recording.py
│   │       │   ├── conversation.py
│   │       │   └── metrics.py
│   │       │
│   │       ├── workers/               ← Celery tasks (AI pipeline)
│   │       │   ├── __init__.py
│   │       │   ├── celery_app.py      ← Celery instance config
│   │       │   ├── pipeline.py        ← Pipeline chain orchestration
│   │       │   ├── preprocessing.py   ← Audio normalization
│   │       │   ├── transcription.py   ← Parakeet STT call
│   │       │   ├── diarization.py     ← NeMo diarization call
│   │       │   ├── segmentation.py    ← Conversation segmentation
│   │       │   ├── analysis.py        ← Llama 3.3 analysis
│   │       │   └── scoring.py         ← Salesperson scoring
│   │       │
│   │       ├── ai/                    ← NVIDIA API client wrappers
│   │       │   ├── __init__.py
│   │       │   ├── nvidia_client.py   ← Base HTTP client for NIM
│   │       │   ├── stt.py             ← Parakeet STT wrapper
│   │       │   ├── diarizer.py        ← NeMo diarization wrapper
│   │       │   └── analyzer.py        ← Llama 3.3 analysis wrapper
│   │       │
│   │       └── storage/               ← File storage abstraction
│   │           ├── __init__.py
│   │           ├── base.py            ← Abstract Storage interface
│   │           ├── local.py           ← Local filesystem implementation
│   │           └── s3.py              ← S3/R2 implementation (future)
│   │
│   └── web/                           ← Next.js frontend application
│       ├── package.json
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       ├── components.json            ← shadcn/ui config
│       └── src/
│           ├── app/                   ← App Router pages
│           │   ├── layout.tsx         ← Root layout
│           │   ├── page.tsx           ← Landing/redirect
│           │   ├── globals.css
│           │   │
│           │   ├── (auth)/            ← Auth route group
│           │   │   └── login/
│           │   │       └── page.tsx
│           │   │
│           │   ├── (dashboard)/       ← Protected dashboard routes
│           │   │   ├── layout.tsx     ← Dashboard layout (sidebar, nav)
│           │   │   ├── brand/
│           │   │   │   └── page.tsx   ← Brand Admin dashboard
│           │   │   ├── store/
│           │   │   │   ├── page.tsx   ← Store Manager dashboard
│           │   │   │   └── [id]/
│           │   │   │       └── page.tsx
│           │   │   └── salesperson/
│           │   │       ├── page.tsx   ← Salesperson dashboard
│           │   │       └── [id]/
│           │   │           └── page.tsx
│           │   │
│           │   ├── recordings/
│           │   │   ├── page.tsx       ← Recording listing
│           │   │   └── [id]/
│           │   │       └── page.tsx   ← Recording detail
│           │   │
│           │   ├── search/
│           │   │   └── page.tsx       ← Semantic search
│           │   │
│           │   └── coaching/
│           │       └── page.tsx       ← Coaching dashboard
│           │
│           ├── components/
│           │   ├── ui/                ← shadcn/ui components
│           │   ├── charts/            ← Recharts wrapper components
│           │   │   ├── trend-chart.tsx
│           │   │   ├── radar-chart.tsx
│           │   │   └── bar-chart.tsx
│           │   └── features/          ← Feature-specific components
│           │       ├── recording/
│           │       ├── conversation/
│           │       ├── transcript/
│           │       └── coaching/
│           │
│           ├── lib/
│           │   ├── api-client.ts      ← Fetch wrapper for backend API
│           │   ├── auth.ts            ← Auth utilities
│           │   └── utils.ts           ← General utilities
│           │
│           └── stores/                ← Zustand state stores
│               ├── auth-store.ts
│               ├── filter-store.ts
│               └── dashboard-store.ts
│
├── packages/
│   └── shared/                        ← Shared contracts between apps
│       ├── package.json
│       └── src/
│           ├── api-types.ts           ← TypeScript types matching Pydantic schemas
│           ├── constants.ts           ← Shared constants (roles, statuses)
│           └── index.ts
│
└── plan/                              ← Design & planning documents
    ├── 00-architecture-design.md      ← This document
    └── 01-implementation-plan.md      ← Sprint-by-sprint implementation plan
```

---

## 4. Database Schema

### Tables

#### users
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | NOT NULL |
| role | ENUM | NOT NULL (SUPER_ADMIN, BRAND_ADMIN, STORE_MANAGER, SALESPERSON) |
| brand_id | UUID | FK → brands.id, NULLABLE |
| store_id | UUID | FK → stores.id, NULLABLE |
| is_active | BOOLEAN | DEFAULT true |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | DEFAULT now() |

#### brands
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | NOT NULL |
| description | TEXT | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | DEFAULT now() |

#### stores
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| brand_id | UUID | FK → brands.id, NOT NULL |
| name | VARCHAR(255) | NOT NULL |
| location | VARCHAR(500) | NULLABLE |
| working_hours | JSONB | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | DEFAULT now() |

#### salespeople
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| store_id | UUID | FK → stores.id, NOT NULL |
| name | VARCHAR(255) | NOT NULL |
| email | VARCHAR(255) | NULLABLE |
| role | VARCHAR(100) | NULLABLE |
| shift | VARCHAR(50) | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | DEFAULT now() |

#### recordings
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| salesperson_id | UUID | FK → salespeople.id, NOT NULL |
| file_url | TEXT | NOT NULL |
| file_size | BIGINT | NULLABLE |
| duration_seconds | INTEGER | NULLABLE |
| format | VARCHAR(10) | NOT NULL (WAV, MP3, M4A) |
| status | ENUM | NOT NULL (UPLOADED, PREPROCESSING, TRANSCRIBING, DIARIZING, SEGMENTING, ANALYZING, SCORING, COMPLETED, FAILED) |
| error_message | TEXT | NULLABLE |
| uploaded_at | TIMESTAMPTZ | DEFAULT now() |
| processed_at | TIMESTAMPTZ | NULLABLE |

#### transcript_segments
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| recording_id | UUID | FK → recordings.id, NOT NULL |
| speaker_label | VARCHAR(20) | NOT NULL |
| start_time | FLOAT | NOT NULL (seconds) |
| end_time | FLOAT | NOT NULL (seconds) |
| text | TEXT | NOT NULL |
| embedding | VECTOR(768) | NULLABLE (for semantic search) |

#### conversations
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| recording_id | UUID | FK → recordings.id, NOT NULL |
| start_time | FLOAT | NOT NULL |
| end_time | FLOAT | NOT NULL |
| segment_count | INTEGER | NOT NULL |
| summary | TEXT | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |

#### conversation_analysis
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| conversation_id | UUID | FK → conversations.id, UNIQUE |
| intent | TEXT | NULLABLE |
| products | JSONB | DEFAULT '[]' |
| budget | VARCHAR(100) | NULLABLE |
| objections | JSONB | DEFAULT '[]' |
| competitors | JSONB | DEFAULT '[]' |
| closing_attempt | BOOLEAN | DEFAULT false |
| outcome | VARCHAR(50) | NULLABLE (SALE_MADE, LOST, FOLLOW_UP_NEEDED) |
| confidence | INTEGER | NULLABLE (0-100) |
| scores | JSONB | NULLABLE (greeting, discovery, product_knowledge, objection_handling, closing) |
| summary | TEXT | NULLABLE |
| coaching_notes | TEXT | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |

#### metrics_daily
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| entity_id | UUID | NOT NULL |
| entity_type | VARCHAR(20) | NOT NULL (brand, store, salesperson) |
| date | DATE | NOT NULL |
| conversation_count | INTEGER | DEFAULT 0 |
| avg_score | FLOAT | NULLABLE |
| conversion_rate | FLOAT | NULLABLE |
| UNIQUE | (entity_id, entity_type, date) | |

#### metrics_weekly
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| entity_id | UUID | NOT NULL |
| entity_type | VARCHAR(20) | NOT NULL |
| week_start | DATE | NOT NULL |
| conversation_count | INTEGER | DEFAULT 0 |
| avg_score | FLOAT | NULLABLE |
| conversion_rate | FLOAT | NULLABLE |
| top_objection | TEXT | NULLABLE |
| UNIQUE | (entity_id, entity_type, week_start) | |

### Indexes
- `transcript_segments.recording_id` — for transcript retrieval
- `transcript_segments.embedding` — pgvector IVFFlat index for semantic search
- `conversations.recording_id` — for listing conversations
- `recordings.salesperson_id` — for salesperson recording list
- `recordings.status` — for filtering by processing status
- `metrics_daily.entity_id + date` — for dashboard time series

---

## 5. API Design

### Authentication

| Method | Endpoint | Description | Request | Response |
|---|---|---|---|---|
| POST | /api/v1/auth/login | Login | `{ email, password }` | `{ access_token, refresh_token, user }` |
| POST | /api/v1/auth/refresh | Refresh token | `{ refresh_token }` | `{ access_token, refresh_token }` |
| POST | /api/v1/auth/logout | Logout | — | `{ message }` |

### Brands

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /api/v1/brands | List all brands | SUPER_ADMIN |
| POST | /api/v1/brands | Create brand | SUPER_ADMIN |
| GET | /api/v1/brands/:id | Get brand details | BRAND_ADMIN+ |
| PUT | /api/v1/brands/:id | Update brand | SUPER_ADMIN |

### Stores

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /api/v1/stores | List stores (filtered by brand) | BRAND_ADMIN+ |
| POST | /api/v1/stores | Create store | BRAND_ADMIN |
| GET | /api/v1/stores/:id | Get store details | STORE_MANAGER+ |
| GET | /api/v1/stores/:id/metrics | Aggregated store metrics | STORE_MANAGER+ |

### Salespeople

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /api/v1/salespeople | List salespeople (filtered by store) | STORE_MANAGER+ |
| POST | /api/v1/salespeople | Add salesperson | STORE_MANAGER |
| GET | /api/v1/salespeople/:id | Get salesperson profile | SALESPERSON+ |
| GET | /api/v1/salespeople/:id/performance | Performance metrics | SALESPERSON+ |

### Recordings

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | /api/v1/recordings/upload | Upload audio + queue processing | SALESPERSON+ |
| GET | /api/v1/recordings/:id | Get recording metadata & status | SALESPERSON+ |
| GET | /api/v1/recordings/:id/status | Poll pipeline stage | SALESPERSON+ |
| GET | /api/v1/recordings/:id/transcript | Full timestamped transcript | SALESPERSON+ |
| GET | /api/v1/recordings/:id/conversations | List conversations in recording | SALESPERSON+ |

### Conversations

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /api/v1/conversations/:id | Conversation details | SALESPERSON+ |
| GET | /api/v1/conversations/:id/analysis | Full AI analysis | SALESPERSON+ |

### Search

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /api/v1/search | Semantic search | STORE_MANAGER+ |

Query params: `q` (search text), `date_from`, `date_to`, `store_id`, `salesperson_id`, `outcome`

---

## 6. AI Pipeline Design

### Pipeline Stages

```
┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌────────────┐
│ UPLOADED │───▶│ PREPROCESSING│───▶│TRANSCRIBING│───▶│ DIARIZING  │
└──────────┘    └──────────────┘    └────────────┘    └────────────┘
                                                              │
┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌──────▼─────┐
│COMPLETED │◀───│   SCORING    │◀───│  ANALYZING │◀───│ SEGMENTING │
└──────────┘    └──────────────┘    └────────────┘    └────────────┘
```

### Stage Details

| Stage | Input | Output | NVIDIA API |
|---|---|---|---|
| **Preprocessing** | Raw audio file | Normalized 16kHz mono WAV | None (local ffmpeg) |
| **Transcription** | Normalized audio | Timestamped word-level JSON | Parakeet 1.1B RNNT via NIM |
| **Diarization** | Normalized audio + transcript | Speaker-labeled segments | NeMo Speaker Diarization via NIM |
| **Segmentation** | Speaker-labeled transcript | Discrete conversation objects | None (rule-based) |
| **Analysis** | Single conversation transcript | Structured JSON (intent, products, objections, outcome) | Llama 3.3 70B via NIM |
| **Scoring** | Conversation analysis results | 5-dimension scores per salesperson | Llama 3.3 70B via NIM |

### Celery Task Chain

```python
# pipeline.py
from celery import chain

processing_chain = chain(
    preprocess_audio.s(recording_id),
    transcribe_audio.s(),
    diarize_audio.s(),
    segment_conversations.s(),
    analyze_conversations.s(),  # fans out to multiple conversations
    score_salesperson.s(),
    aggregate_metrics.s(),
)
```

### Error Handling

- Each task has `max_retries=3` with `retry_backoff=60` (exponential)
- Failed tasks update recording status to `FAILED` with `error_message`
- Partial results are preserved (e.g., transcript exists even if analysis fails)

### Segmentation Rules

| Signal | Rule |
|---|---|
| Silence gap | Gap > 30 seconds → conversation boundary |
| Greeting detection | Salesperson greeting → new conversation start |
| Departure detection | Farewell phrases → conversation end |
| New speaker entry | New speaker after silence → new conversation |

---

## 7. Frontend Design

### Route Structure

| Route | Page | Primary Users |
|---|---|---|
| `/login` | Login page | All |
| `/brand` | Brand dashboard | Brand Admin |
| `/store` | Store dashboard | Store Manager |
| `/store/[id]` | Store detail | Brand Admin |
| `/salesperson` | Salesperson dashboard | Salesperson |
| `/salesperson/[id]` | Salesperson detail | Store Manager |
| `/recordings` | Recording listing | All |
| `/recordings/[id]` | Recording detail + transcript | All |
| `/search` | Semantic search | Store Manager+ |
| `/coaching` | Coaching dashboard | Salesperson, Store Manager |

### Page Components

#### Brand Dashboard (`/brand`)
- Summary cards: total stores, salespeople, conversations, conversion score
- Store ranking table (sorted by avg performance score)
- Trend charts: conversation volume + conversion rate over time
- Top objections across all stores
- Coaching alerts: flagged stores and salespeople

#### Store Dashboard (`/store`)
- Store header: location, contact info
- KPI cards: performance score, conversation volume, top objection
- Salesperson performance table with drill-down links
- Daily/weekly trend charts
- Recent recordings status table

#### Salesperson Dashboard (`/salesperson`)
- Profile header: name, role, shift
- KPI cards: conversations handled, closing rate, avg score
- Skill radar chart (5 dimensions)
- Recordings list with score preview + status badge
- Coaching recommendations panel

#### Recording Detail (`/recordings/[id]`)
- Header: date, salesperson, duration, status
- Summary cards: conversation count, top intent, top objection
- Conversation timeline (interactive)
- Split view: transcript (left) + AI insights (right)
- Conversation detail drawer (slide-over)

#### Conversation Detail Drawer
- Full transcript with speaker-colored labels
- AI summary paragraph
- Objections list with suggested responses
- Products discussed
- Coaching notes

#### Coaching Dashboard (`/coaching`)
- Skill scores with trend vs prior period (5 dimensions)
- Improvement areas with specific conversation examples
- Prioritized action items
- Historical trend: 30/60/90 day score charts

#### Search (`/search`)
- Natural language search input
- Results as conversation cards with highlighted snippets
- Filters: date range, store, salesperson, outcome
- Powered by pgvector semantic similarity

### Design System

| Element | Choice |
|---|---|
| Component library | shadcn/ui |
| CSS framework | Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |
| Fonts | Inter (default shadcn) |
| Color scheme | Light/dark mode support |
| Status badge colors | Green=Completed, Blue=Processing, Red=Failed, Yellow=Uploaded |

---

## 8. Authentication & Authorization

### JWT Flow
1. User logs in with email/password
2. Server validates credentials, returns access_token (15min) + refresh_token (7 days)
3. Access token sent in `Authorization: Bearer <token>` header
4. Refresh token stored in HTTP-only secure cookie
5. On access token expiry, client calls `/auth/refresh` automatically

### Role Hierarchy

```
SUPER_ADMIN > BRAND_ADMIN > STORE_MANAGER > SALESPERSON
```

Each role inherits permissions from roles below it. Middleware checks role before allowing API access.

### Data Scoping
- **SUPER_ADMIN**: Access to all brands
- **BRAND_ADMIN**: Access to own brand's stores, salespeople, recordings
- **STORE_MANAGER**: Access to own store's salespeople and recordings
- **SALESPERSON**: Access to own recordings and analysis only

---

## 9. File Storage Abstraction

```python
# storage/base.py
from abc import ABC, abstractmethod
from pathlib import Path

class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, file_data: bytes, destination: str) -> str:
        """Upload file and return URL/path"""
    
    @abstractmethod
    async def download(self, source: str) -> bytes:
        """Download file and return bytes"""
    
    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file"""
    
    @abstractmethod
    async def get_signed_url(self, path: str, expires_in: int = 900) -> str:
        """Generate time-limited access URL (15 min default)"""
```

Local implementation stores files in `./uploads/` directory. S3 implementation swaps in later with zero code changes to services.

---

## 10. Development Environment

### Docker Compose Services

| Service | Port | Purpose |
|---|---|---|
| PostgreSQL + pgvector | 5432 | Primary database |
| Redis | 6379 | Celery broker + result backend |
| MinIO | 9000 | S3-compatible local storage (optional) |

### Local Development

```bash
# Start infrastructure
docker-compose up -d postgres redis

# Backend
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn src.main:app --reload

# Celery worker (separate terminal)
celery -A src.workers.celery_app worker --loglevel=info

# Frontend
cd apps/web
npm install
npm run dev
```

---

## 11. Technology Stack Summary

| Layer | Technology | Version |
|---|---|---|
| **Monorepo** | Turborepo | Latest |
| **Backend API** | FastAPI | 0.110+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Migrations** | Alembic | Latest |
| **Validation** | Pydantic | 2.0+ |
| **Task Queue** | Celery | 5.3+ |
| **Broker** | Redis | 7+ |
| **Database** | PostgreSQL + pgvector | 16+ |
| **AI STT** | NVIDIA Parakeet 1.1B (NIM API) | — |
| **AI Diarization** | NVIDIA NeMo (NIM API) | — |
| **AI Analysis** | Llama 3.3 70B (NIM API) | — |
| **Audio Processing** | ffmpeg (via pydub or subprocess) | — |
| **Frontend** | Next.js | 15+ |
| **Language** | TypeScript | 5+ |
| **Styling** | Tailwind CSS | 3+ |
| **UI Components** | shadcn/ui | Latest |
| **Charts** | Recharts | 2+ |
| **State** | Zustand + TanStack Query | Latest |
| **Icons** | Lucide React | Latest |
| **Containerization** | Docker + Docker Compose | — |
