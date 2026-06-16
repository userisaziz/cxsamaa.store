# CXSAMAA — Implementation Plan

**Based on:** [00-architecture-design.md](./00-architecture-design.md)  
**Status:** Ready for Execution  
**Date:** 2026-06-09  

---

## Overview

6 sprints, bottom-up build order: Infrastructure → Backend Foundations → AI Pipeline → Frontend Core → Detail Experience → Intelligence Layer. Each sprint produces a shippable increment.

---

## Sprint 1: Backend Foundations

**Goal:** Working API server with auth, CRUD endpoints, database schema, file upload, and Celery worker skeleton.  
**Definition of Done:** All CRUD endpoints tested, audio upload functional, DB migrations applied, Docker dev environment working.

### Task 1.1: Monorepo & Dev Environment Setup
- Initialize Turborepo monorepo with `apps/api`, `apps/web`, `packages/shared`
- Create `docker-compose.yml` with PostgreSQL (pgvector), Redis
- Create `.env.example` with all required environment variables
- Set up root `.gitignore` for Python, Node, Docker artifacts
- **Verify:** `docker-compose up` starts PostgreSQL and Redis

### Task 1.2: FastAPI Project Skeleton
- Initialize `apps/api` with pyproject.toml (FastAPI, SQLAlchemy, Alembic, Celery, Redis, pydantic-settings, python-jose, passlib, python-multipart)
- Create `src/main.py` with FastAPI app, CORS middleware, health check endpoint
- Create `src/config.py` with pydantic-settings (DATABASE_URL, REDIS_URL, JWT_SECRET, STORAGE_BACKEND)
- Create `src/database.py` with async SQLAlchemy engine + session factory
- **Verify:** `uvicorn src.main:app --reload` starts and `/health` returns 200

### Task 1.3: Database Models & Migrations
- Initialize Alembic in `apps/api`
- Create all SQLAlchemy models: `user.py`, `brand.py`, `store.py`, `salesperson.py`, `recording.py`, `transcript.py`, `conversation.py`, `metrics.py`
- Create initial migration with all tables + indexes + pgvector extension
- Create seed script for test data (1 brand, 2 stores, 3 salespeople, 1 admin user)
- **Verify:** `alembic upgrade head` applies cleanly, seed script populates DB

### Task 1.4: Authentication System
- Implement `services/auth.py`: password hashing (bcrypt), JWT creation/validation, token refresh
- Implement `api/deps.py`: `get_current_user` dependency, role-based access checker
- Implement `api/v1/auth.py`: POST `/auth/login`, POST `/auth/refresh`, POST `/auth/logout`
- Create Pydantic schemas: `schemas/auth.py`
- **Verify:** Login returns JWT, protected endpoints reject unauthenticated requests, refresh works

### Task 1.5: Brand & Store CRUD APIs
- Implement `services/brand.py` and `services/store.py` with CRUD operations
- Implement `api/v1/brands.py`: GET `/brands`, POST `/brands`, GET `/brands/:id`, PUT `/brands/:id`
- Implement `api/v1/stores.py`: GET `/stores`, POST `/stores`, GET `/stores/:id`, GET `/stores/:id/metrics`
- Create Pydantic schemas for request/response validation
- Wire up role-based access (SUPER_ADMIN for brand CRUD, BRAND_ADMIN for store CRUD)
- **Verify:** CRUD operations work, data scoping enforced by role

### Task 1.6: Salesperson CRUD APIs
- Implement `services/salesperson.py` with CRUD + performance query
- Implement `api/v1/salespeople.py`: GET `/salespeople`, POST `/salespeople`, GET `/salespeople/:id`, GET `/salespeople/:id/performance`
- Performance endpoint returns aggregated scores from conversation_analysis
- **Verify:** Salespeople can be created, listed, and performance data returned

### Task 1.7: File Storage Abstraction
- Implement `storage/base.py` with abstract `StorageBackend` interface
- Implement `storage/local.py` for local filesystem (stores in `./uploads/`)
- Create upload directory configuration in settings
- **Verify:** Files can be uploaded and retrieved via the storage interface

### Task 1.8: Recording Upload API
- Implement `services/recording.py`: upload handling, metadata storage, job enqueue
- Implement `api/v1/recordings.py`: POST `/recordings/upload`, GET `/recordings/:id`, GET `/recordings/:id/status`
- Upload endpoint: validate file format (WAV/MP3/M4A), validate duration (1min-12hr), store file, create DB record, enqueue Celery job
- Return `recordingId` with `status: UPLOADED`
- **Verify:** Audio file upload works, recording record created, Celery job queued

### Task 1.9: Celery Worker Skeleton
- Configure `workers/celery_app.py` with Redis broker
- Create placeholder tasks for each pipeline stage
- Implement `workers/pipeline.py` with the chain orchestration
- Implement status update logic (update recording status at each stage)
- **Verify:** Upload triggers Celery chain, status progresses through stages (even if tasks are no-ops)

### Task 1.10: API Router Aggregation & Testing
- Wire all v1 routers into `api/v1/router.py`
- Add OpenAPI documentation tags and descriptions
- Write integration tests for all CRUD endpoints
- **Verify:** Full API docs at `/docs`, all tests pass

---

## Sprint 2: AI Pipeline

**Goal:** Real AI processing — audio preprocessing, STT, diarization, and conversation segmentation working end-to-end.  
**Definition of Done:** 8-hour audio processed to transcript in < 10 min; speaker labels accurate.

### Task 2.1: Audio Preprocessing Worker
- Implement `workers/preprocessing.py`
- Convert to mono, normalize volume, resample to 16kHz (using pydub/ffmpeg)
- Detect silence gaps > 30 seconds
- Handle corrupt/unreadable segments gracefully
- Save preprocessed audio, update recording status to PREPROCESSING → TRANSCRIBING
- **Verify:** Preprocessing produces valid 16kHz mono WAV from any input format

### Task 2.2: NVIDIA NIM API Client
- Implement `ai/nvidia_client.py`: base HTTP client with retry logic, rate limiting, error handling
- Configure API key and endpoint URLs via environment variables
- Add request/response logging and error categorization
- **Verify:** Client can authenticate and make test calls to NVIDIA NIM

### Task 2.3: Speech-to-Text Integration
- Implement `ai/stt.py`: Parakeet 1.1B RNNT wrapper via NVIDIA NIM API
- Implement `workers/transcription.py`: send preprocessed audio to STT, receive timestamped transcript
- Parse response into transcript_segments and store in DB
- Update recording status to DIARIZING
- **Verify:** Audio file produces timestamped transcript stored in DB

### Task 2.4: Speaker Diarization Integration
- Implement `ai/diarizer.py`: NeMo Speaker Diarization wrapper via NVIDIA NIM API
- Implement `workers/diarization.py`: send audio + transcript, receive speaker labels
- Merge speaker labels with existing transcript_segments
- Handle overlapping speech, assign Speaker A/B/C labels
- **Verify:** Transcript segments have speaker labels, distinct speakers identified

### Task 2.5: Conversation Segmentation
- Implement `workers/segmentation.py`
- Apply segmentation rules: silence gaps > 30s, greeting detection, departure detection, new speaker entry
- Create `conversations` records with start/end times and segment counts
- Generate basic summary per conversation
- **Verify:** Long recording split into discrete conversations, boundaries make sense

### Task 2.6: Pipeline Integration Test
- Upload a real audio file end-to-end through the full pipeline
- Verify each stage transitions correctly
- Verify transcript_segments, conversations records created properly
- Measure processing time against target (< 10 min for 8-hour audio)
- **Verify:** Full pipeline runs without errors, results are correct

---

## Sprint 3: LLM Analysis & Scoring

**Goal:** Conversation analysis with Llama 3.3, salesperson scoring, and metric aggregation.  
**Definition of Done:** 95%+ of conversations produce valid structured JSON analysis output.

### Task 3.1: Conversation Analysis with Llama 3.3
- Implement `ai/analyzer.py`: Llama 3.3 70B wrapper via NVIDIA NIM API
- Design prompt template for structured analysis output (intent, products, budget, objections, competitors, closing_attempt, outcome, confidence)
- Implement `workers/analysis.py`: process each conversation, parse JSON response, store in `conversation_analysis`
- Enforce minimum 85% confidence threshold
- Implement retry with re-prompting for malformed responses
- **Verify:** Conversations produce valid structured analysis JSON

### Task 3.2: Salesperson Performance Scoring
- Implement `workers/scoring.py`
- Design scoring prompt for 5 dimensions: greeting, discovery, product_knowledge, objection_handling, closing
- Score each conversation, store in `conversation_analysis.scores`
- Aggregate scores per salesperson per recording
- **Verify:** Each conversation has 5-dimension scores, salesperson averages computed

### Task 3.3: Metrics Aggregation
- Implement `services/metrics.py`
- Compute daily metrics: conversation_count, avg_score, conversion_rate per entity
- Compute weekly metrics: rollup with top_objection
- Implement `workers/aggregation.py`: triggered after scoring completes
- Update `metrics_daily` and `metrics_weekly` tables
- **Verify:** Metrics tables populated after pipeline completion

### Task 3.4: Recording Summary & Status
- Update recording status to COMPLETED after all stages finish
- Populate `processed_at` timestamp
- Implement recording summary: total conversations, top intent, top objection, missed opportunities
- Implement `GET /recordings/:id/conversations` endpoint with real data
- Implement `GET /recordings/:id/transcript` endpoint with real data
- Implement `GET /conversations/:id` and `GET /conversations/:id/analysis` endpoints
- **Verify:** All recording and conversation endpoints return real AI-processed data

### Task 3.5: Error Handling & Retry
- Implement comprehensive error handling for NVIDIA API failures
- Add exponential backoff retry (3 attempts per task)
- Implement partial failure handling (transcript exists even if analysis fails)
- Add FAILED status with descriptive error_message
- Add re-processing endpoint: `POST /recordings/:id/reprocess`
- **Verify:** Pipeline recovers from transient failures, failed recordings can be reprocessed

---

## Sprint 4: Frontend Core

**Goal:** Working Next.js frontend with authentication, dashboards, and recording listing.  
**Definition of Done:** All dashboard pages load with real data, navigation drill-down working.

### Task 4.1: Next.js Project Setup
- Initialize `apps/web` with Next.js 15, TypeScript, Tailwind CSS
- Install and configure shadcn/ui, Recharts, Lucide React, Zustand, TanStack Query
- Set up API client (`lib/api-client.ts`) with JWT auth interceptor
- Configure environment variables (NEXT_PUBLIC_API_URL)
- Set up `packages/shared` with TypeScript types matching backend schemas
- **Verify:** `npm run dev` starts, shadcn components render

### Task 4.2: Auth Flow & Layout
- Implement login page (`(auth)/login/page.tsx`)
- Implement auth store (Zustand): token management, user state, login/logout
- Implement protected route middleware (redirect to /login if unauthenticated)
- Implement dashboard layout with sidebar navigation
- Role-based redirect after login (Brand Admin → /brand, Store Manager → /store, etc.)
- **Verify:** Login works, role-based redirect works, protected routes guarded

### Task 4.3: Brand Dashboard
- Implement `/brand` page
- Summary cards: total stores, salespeople, conversations, conversion score
- Store ranking table (sorted by avg performance score, clickable rows)
- Trend charts: conversation volume + conversion rate (Recharts)
- Top objections list
- Coaching alerts section
- **Verify:** Brand dashboard loads real data from API, charts render

### Task 4.4: Store Dashboard
- Implement `/store` page and `/store/[id]` page
- Store header with location info
- KPI cards: performance score, conversation volume, top objection
- Salesperson performance table with drill-down links to `/salesperson/[id]`
- Daily/weekly trend charts
- Recent recordings status table
- **Verify:** Store dashboard shows real data, drill-down to salesperson works

### Task 4.5: Salesperson Dashboard
- Implement `/salesperson` and `/salesperson/[id]` pages
- Profile header: name, role, shift
- KPI cards: conversations handled, closing rate, avg score
- Skill radar chart (5 dimensions, Recharts RadarChart)
- Recordings list with score preview and status badge
- Coaching recommendations panel
- **Verify:** Salesperson dashboard shows real data, radar chart renders

### Task 4.6: Recording Listing Page
- Implement `/recordings` page
- Filter bar: date range, processing status, duration range
- Table columns: date, duration, conversations detected, avg score, status badge
- Status badges with color coding (Green=Completed, Blue=Processing, Red=Failed, Yellow=Uploaded)
- Actions: View Details, Download Audio, Re-process
- Pagination
- **Verify:** Recordings listed with filters, status badges correct, pagination works

---

## Sprint 5: Detail Experience

**Goal:** Recording detail page, transcript viewer, AI insights, and coaching dashboard.  
**Definition of Done:** Recording detail page shows transcript + AI insights inline; coaching visible.

### Task 5.1: Recording Detail Page
- Implement `/recordings/[id]` page
- Recording header: date, salesperson, duration, processing status
- Summary cards: conversation count, top intent, top objection, missed opportunities
- Interactive conversation timeline (visual bar showing each conversation's position in the recording)
- **Verify:** Recording detail loads, timeline renders conversations

### Task 5.2: Transcript Viewer
- Implement transcript viewer component (`components/features/transcript/`)
- Display speaker-labeled segments with timestamps
- Speaker-colored labels (Speaker A = blue, Speaker B = green, etc.)
- Clickable timestamps that highlight the corresponding conversation
- Auto-scroll sync with conversation selection
- **Verify:** Transcript displays with speaker labels, timestamps clickable

### Task 5.3: AI Insights Panel
- Implement AI insights panel (right side of recording detail)
- Display per-conversation: intent, budget, objections, outcome, confidence
- Products discussed section
- Closing attempt indicator
- Score breakdown per conversation
- **Verify:** AI insights display correctly for each conversation

### Task 5.4: Conversation Detail Drawer
- Implement slide-over drawer component
- Full conversation transcript with speaker-colored labels
- AI-generated summary paragraph
- Objections list with suggested responses
- Products discussed section
- Coaching notes from conversation behavior
- **Verify:** Drawer opens on conversation click, all content displays

### Task 5.5: Coaching Dashboard
- Implement `/coaching` page
- Skill scores section: 5 dimensions with numerical scores + trend arrows vs prior period
- Improvement areas: AI-identified weakest areas with specific conversation examples
- Recommendations: prioritized action items
- Historical trend: score charts for 30/60/90 day periods
- **Verify:** Coaching dashboard shows real scores and trends

---

## Sprint 6: Intelligence Layer

**Goal:** Semantic search, store/brand aggregations, and export/reporting.  
**Definition of Done:** Brand and store dashboards aggregate correctly; search returns relevant results.

### Task 6.1: Semantic Search Backend
- Generate embeddings for transcript segments (store in `transcript_segments.embedding`)
- Implement `GET /search` endpoint with pgvector similarity search
- Support filters: date range, store, salesperson, outcome
- Return conversation cards with relevant transcript snippets
- **Verify:** Search returns relevant results for test queries

### Task 6.2: Search Frontend
- Implement `/search` page
- Natural language search input
- Results displayed as conversation cards with highlighted transcript snippets
- Filter sidebar: date range, store, salesperson, outcome
- **Verify:** Search UI works end-to-end, results are relevant

### Task 6.3: Store & Brand Aggregations
- Implement `GET /stores/:id/metrics` with real aggregated data
- Implement brand-level aggregation: store comparisons, regional trends
- Top objections across stores, coaching needs, revenue risks
- Wire aggregation data into Brand and Store dashboards
- **Verify:** Brand dashboard shows cross-store comparisons, store metrics accurate

### Task 6.4: Export & Reporting
- Add CSV export for recordings list, conversation analysis, metrics
- Add PDF export for salesperson performance reports
- Implement date range selection for all exports
- **Verify:** CSV and PDF exports generate correctly with filtered data

### Task 6.5: Polish & Performance
- Add loading states and skeleton screens for all pages
- Implement optimistic updates for status polling
- Add error boundaries and graceful error states
- Performance optimization: lazy load charts, virtualize long lists
- Responsive design pass for tablet/mobile
- **Verify:** All pages have loading states, no janky renders, Lighthouse score > 80

---

## Dependency Graph

```
Sprint 1 (Backend)
    ├── Sprint 2 (AI Pipeline) ──▶ Sprint 3 (LLM Analysis)
    │                                      │
    └── Sprint 4 (Frontend Core) ◀─────────┘
                │
                └── Sprint 5 (Detail Experience)
                              │
                              └── Sprint 6 (Intelligence Layer)
                │
                └── Sprint 7 (Custom Model Training) ← Future Phase
```

Sprints 2 and 4 can partially overlap — frontend scaffolding (Task 4.1-4.2) can begin while AI pipeline is being built, using mock data.

Sprint 7 is a **future phase** — begins after collecting sufficient labeled retail audio data (Arabic/Hindi/English). Depends on all prior sprints being complete.

---

## Key Technical Notes

### NVIDIA NIM API Integration
- All AI calls go through `ai/nvidia_client.py` base client
- Rate limiting and retry logic centralized in base client
- API keys stored in environment variables, never committed

### Celery Pipeline Reliability
- Each task is idempotent (can be safely retried)
- Partial results preserved on failure (e.g., transcript saved even if analysis fails)
- Pipeline chain uses Celery's `chain()` primitive for sequential execution
- Analysis fans out per-conversation (group of tasks)

### Frontend Data Fetching
- TanStack Query for all API calls with appropriate cache times
- Status polling for recordings uses `refetchInterval` (5 seconds while processing)
- Optimistic updates for non-critical mutations

### Security Checklist
- JWT in Authorization header (access token, 15min expiry)
- Refresh token in HTTP-only secure cookie (7 day expiry)
- All passwords hashed with bcrypt
- Role-based access enforced at route level
- Data scoping enforced at service level (users only see their brand/store data)
- File uploads validated (format, MIME type, size, duration)

---

## Sprint 7: Custom Model Training (Future Phase)

**Goal:** Train domain-specific ASR and diarization models on retail store audio (English, Arabic, Hindi) to replace hosted NVIDIA APIs with self-hosted models for better accuracy and cost control.  
**Prerequisites:** Minimum 500+ hours of labeled retail audio collected from production pipeline.  
**Definition of Done:** Custom ASR model achieves lower WER than Parakeet on retail test set; custom diarization model achieves lower DER than Streusand on retail test set; pipeline seamlessly switches to self-hosted models.

### Task 7.1: Data Collection & Annotation Pipeline
- Build data collection pipeline: automatically save preprocessed audio + transcripts from production runs
- Implement quality filtering: exclude low-confidence transcripts (< 85%), corrupt audio, too-short segments
- Build annotation review UI (optional): allow humans to correct transcripts for training ground truth
- Store training dataset with metadata: language, duration, speaker count, store, quality score
- **Verify:** Production audio flows into training dataset automatically, quality filters work

### Task 7.2: Speech Data Processing & Dataset Preparation
- Use NVIDIA Speech Data Processor for large-scale audio cleaning
- Resample, normalize, and segment audio into training-ready clips
- Split dataset: train (80%), validation (10%), test (10%) — stratified by language and store
- Generate manifests in NeMo format (audio_filepath, text, duration, speaker)
- Handle code-switching and mixed-language segments (Gulf Arabic + English, Hindi + English)
- **Verify:** Training manifests generated, dataset balanced across languages

### Task 7.3: Speech Self-Supervised Learning (SSL) Pre-training
- Use NeMo Speech SSL to pre-train base model on unlabeled retail audio
- Leverage all collected audio (including unlabeled) for self-supervised representation learning
- This creates a strong foundation model that understands retail audio characteristics (background noise, acoustics, dialect patterns)
- **Verify:** SSL pre-training completes, loss converges, representations capture speech patterns

### Task 7.4: ASR Model Fine-tuning
- Fine-tune SSL pre-trained model on labeled transcript data using CTC/RNNT objective
- Start from NVIDIA Canary or Parakeet weights as initialization (transfer learning)
- Train separately for each language, then create multilingual final model
- Use NeMo Forced Aligner to generate word-level alignments for training data
- **Verify:** Fine-tuned model produces transcripts, WER measured on test set

### Task 7.5: Diarization Model Fine-tuning
- Fine-tune speaker diarization model on retail audio with known speaker segments
- Train on retail-specific scenarios: 2-4 speakers, store acoustics, overlapping speech
- Use CTC-Segmentation tool to create training clips from long recordings
- **Verify:** Fine-tuned diarization model produces speaker segments, DER measured on test set

### Task 7.6: Model Evaluation & Comparison
- Use ASR Evaluator to benchmark custom model vs. Parakeet on retail test set
- Use Comparison Tool for side-by-side analysis of transcription differences
- Measure: WER (word error rate), CER (character error rate), processing speed
- Measure diarization: DER (diarization error rate), speaker confusion
- Test specifically on Arabic and Hindi audio quality
- **Verify:** Custom model meets or exceeds hosted API accuracy on retail domain

### Task 7.7: Model Serving & Pipeline Integration
- Deploy custom models via NVIDIA Triton Inference Server (or NeMo inference scripts)
- Update `ai/stt.py` to support both NIM API and self-hosted model (feature flag)
- Update `ai/diarizer.py` to support both NIM API and self-hosted model (feature flag)
- Add model version tracking: which model version processed each recording
- Implement A/B testing: route percentage of recordings to custom model vs. hosted API
- **Verify:** Pipeline runs with self-hosted models, results match or exceed hosted API quality

### Task 7.8: Continuous Training Loop
- Implement automated retraining trigger: when N hours of new labeled data accumulated
- Build model registry: track versions, metrics, deployment status
- Add rollback capability: if new model performs worse, revert to previous version
- Monitor production quality metrics: track WER/DER trends over time
- **Verify:** New data triggers retraining, model registry tracks versions, rollback works

### Task 7.9: Infrastructure Setup
- GPU infrastructure for training (cloud GPU instances or on-premise)
- Model storage: versioned model artifacts (MLflow or simple S3/R2 bucket)
- Training pipeline orchestration (can extend Celery or use separate training scheduler)
- Monitoring: GPU utilization, training loss, evaluation metrics dashboard
- **Verify:** Training infrastructure provisioned, model artifacts stored and versioned
