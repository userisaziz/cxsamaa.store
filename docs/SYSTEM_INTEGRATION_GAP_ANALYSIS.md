# SAMAA — System Integration Gap Analysis

**Generated:** 2026-06-13  
**Scope:** Wire-up analysis comparing implemented code against architecture plans  
**Based on:** `plan/00-architecture-design.md`, `plan/01-implementation-plan.md`, `plan/02-decision-log.md`

---

## Executive Summary

This report identifies components that exist but aren't properly connected, planned features not yet exposed through APIs or UI, and configuration gaps that prevent the system from being fully functional. The analysis focuses on **wiring and integration** rather than missing code.

**Overall Status:** ~75% implemented. Core infrastructure is solid, but several advanced features exist in the codebase without API routes or frontend access.

---

## 1. Missing Integrations

### 1.1 Export Service — No API Endpoint

**Status:** Code exists, not wired to API  
**Location:** `apps/api/src/services/export.py`  
**Impact:** Users cannot export data as planned in Sprint 6 (Task 6.4)

**Details:**
- `export_recordings_csv()` and `export_conversations_csv()` are fully implemented
- No route in `apps/api/src/api/v1/` exposes these functions
- Architecture plan specifies CSV export for recordings, conversations, and metrics
- Architecture plan specifies PDF export for salesperson performance reports (not implemented)

**What needs to be done:**
1. Create `apps/api/src/api/v1/export.py` with endpoints:
   - `GET /api/v1/export/recordings.csv`
   - `GET /api/v1/export/conversations.csv`
   - `GET /api/v1/export/metrics.csv`
2. Add router to `apps/api/src/api/v1/router.py`
3. Add role-based access control (STORE_MANAGER+)
4. Implement PDF export service for performance reports

---

### 1.2 Voiceprint Engine — No API or Frontend Access

**Status:** Fully implemented, zero wiring  
**Location:** `apps/api/src/ai/voiceprint.py`  
**Impact:** Cross-conversation speaker tracking and automatic salesperson identification cannot be used

**Details:**
- Complete voiceprint enrollment system using pyannote/resemblyzer embeddings
- Functions: `create_voiceprint_record()`, `complete_enrollment()`, `match_speaker()`, `get_enrolled_voiceprints()`
- Database model `SpeakerVoiceprint` exists in `models/transcript.py`
- **No API endpoints** to enroll, manage, or query voiceprints
- **No frontend UI** for voiceprint management

**What needs to be done:**
1. Create API endpoints:
   - `POST /api/v1/voiceprints/enroll` — Create enrollment record
   - `GET /api/v1/voiceprints` — List enrolled voiceprints (filtered by store)
   - `POST /api/v1/voiceprints/{id}/complete` — Complete enrollment with embedding
   - `POST /api/v1/voiceprints/match` — Match audio sample against enrolled voiceprints
   - `DELETE /api/v1/voiceprints/{id}` — Remove voiceprint
2. Integrate voiceprint matching into preprocessing pipeline (auto-identify salesperson)
3. Build frontend UI for voiceprint enrollment management

---

### 1.3 Cross-Conversation Speaker Tracker — No Integration

**Status:** Fully implemented, isolated module  
**Location:** `apps/api/src/ai/cross_conversation_tracker.py`  
**Impact:** Cannot track the same speaker (customer or salesperson) across multiple recordings

**Details:**
- `find_cross_conversation_speakers()` clusters speakers across recordings using cosine similarity
- Uses text embeddings on `TranscriptSegment` to identify same speakers
- **Never called** from any API endpoint or worker task
- Not integrated into any analytics or dashboard feature

**What needs to be done:**
1. Create API endpoint:
   - `GET /api/v1/analytics/cross-conversation-speakers` — Find speakers across recordings
2. Integrate into brand/store dashboards (show returning customers)
3. Add to recording detail page (show if this customer appeared before)

---

### 1.4 Word-Level Attribution Engine — Not Used in Pipeline

**Status:** Implemented, but pipeline uses coarse segment-level attribution  
**Location:** `apps/api/src/ai/attribution.py`  
**Impact:** Word-level speaker accuracy is lower than it could be

**Details:**
- `assign_speaker_to_word()` maps diarization segments to individual words
- Current pipeline (`workers/transcription.py`, `workers/diarization.py`) assigns speaker labels at segment level
- This module would improve accuracy but is never called

**What needs to be done:**
1. Integrate into diarization worker after diarization completes
2. Update `WordTranscript` records with refined speaker labels
3. Add configuration flag to toggle word-level vs segment-level attribution

---

### 1.5 Speaker Role Corrections Audit Trail — Partially Wired

**Status:** Database model exists, API endpoint exists, but corrections don't cascade  
**Location:** `apps/api/src/models/transcript.py` (SpeakerRoleCorrection), `apps/api/src/api/v1/recordings.py` (PATCH endpoint)  
**Impact:** Role corrections are logged but don't update related transcript data

**Details:**
- `POST /api/v1/recordings/{id}/speaker-role` accepts correction requests
- Creates `SpeakerRoleCorrection` audit record
- **Does NOT update** `TranscriptSegment.speaker_label` or `WordTranscript.speaker_label`
- **Does NOT update** `ConversationTurn.role_label`
- Frontend swap button logs correction but downstream data remains stale

**What needs to be done:**
1. After creating correction record, cascade update to:
   - All `TranscriptSegment` records with that speaker label
   - All `WordTranscript` records with that speaker label
   - All `ConversationTurn` records with that speaker label
2. Optionally re-run analysis/scoring if role swap changes conversation understanding

---

## 2. Incomplete Wiring

### 2.1 Frontend Missing Zustand Stores

**Status:** Architecture specifies 3 stores, only 1 exists  
**Location:** `apps/web/src/store/`  
**Impact:** Client state management incomplete

**Details:**
- ✅ `auth.ts` — Auth store exists and works
- ❌ `filter-store.ts` — **Missing** (planned for dashboard filters)
- ❌ `dashboard-store.ts` — **Missing** (planned for dashboard state)

**What needs to be done:**
1. Create `filter-store.ts` for date range, store, salesperson filters
2. Create `dashboard-store.ts` for dashboard tab state, chart preferences
3. Wire stores to dashboard pages for persistent filter state across navigation

---

### 2.2 Frontend API Client — Not Using TanStack Query

**Status:** Raw fetch wrapper exists, but TanStack Query not integrated  
**Location:** `apps/web/src/lib/api-client.ts`  
**Impact:** No caching, no optimistic updates, no automatic refetching

**Details:**
- `api-client.ts` provides basic `get`, `post`, `put`, `patch`, `delete` methods
- `@tanstack/react-query` is installed in `package.json`
- **Not used** in any page or component
- Architecture plan (Sprint 4) specifies TanStack Query for all API calls with cache times
- Status polling for recordings should use `refetchInterval` (not implemented)

**What needs to be done:**
1. Wrap API client methods with `useQuery`, `useMutation` hooks
2. Configure query client with appropriate cache times
3. Implement status polling with `refetchInterval: 5000` while processing
4. Add optimistic updates for non-critical mutations

---

### 2.3 Analytics API — Incomplete Endpoint Coverage

**Status:** 2 of planned endpoints exist, metrics endpoint missing  
**Location:** `apps/api/src/api/v1/analytics.py`  
**Impact:** Some dashboard charts cannot load data

**Details:**
- ✅ `GET /api/v1/analytics/overview` — exists
- ✅ `GET /api/v1/analytics/salespeople-comparison` — exists
- ❌ `GET /api/v1/stores/{id}/metrics` — **Missing** (specified in architecture, but route in `stores.py` doesn't wire to analytics service)
- ❌ `GET /api/v1/brands/{id}/metrics` — **Missing**
- ❌ `GET /api/v1/analytics/funnel` — **Missing** (sales funnel chart exists in frontend, no backend)

**What needs to be done:**
1. Add metrics endpoints to `stores.py` and `brands.py`
2. Create funnel analytics endpoint
3. Wire to frontend chart components

---

### 2.4 Recording Audio Download — Endpoint Exists, Storage Integration Unclear

**Status:** Endpoint exists but storage backend not fully integrated  
**Location:** `apps/api/src/api/v1/recordings.py` (line 103: `/{recording_id}/audio`)  
**Impact:** Audio file downloads may fail if storage backend not configured correctly

**Details:**
- `GET /api/v1/recordings/{id}/audio` returns `FileResponse`
- Uses `get_storage()` from `src/storage/local.py`
- Storage backend selection is configured via `STORAGE_BACKEND` env var
- **S3 backend (`storage/s3.py`) not implemented** (only `local.py` exists)
- Architecture plan specifies storage abstraction for future S3/R2 swap

**What needs to be done:**
1. Implement `storage/s3.py` with `boto3` or `aiobotocore`
2. Add factory pattern in `storage/__init__.py` to select backend based on config
3. Test audio download with both local and S3 backends

---

### 2.5 Conversation Audio Extraction — Endpoint Exists, Implementation Incomplete

**Status:** Endpoint exists but service logic not wired  
**Location:** `apps/api/src/api/v1/conversations.py` (line 71: `/{conversation_id}/audio`)  
**Impact:** Cannot extract audio segment for a specific conversation

**Details:**
- `GET /api/v1/conversations/{id}/audio` endpoint defined
- Should extract audio segment from recording based on conversation `start_time` and `end_time`
- **No service function** to extract audio segment from recording file
- Requires ffmpeg/pydub integration to slice audio

**What needs to be done:**
1. Create `services/conversation.py` function `extract_conversation_audio()`
2. Use pydub to slice audio file by conversation timestamps
3. Return sliced audio as `FileResponse` or temporary file

---

### 2.6 Celery Pipeline — Metrics Aggregation Task Missing

**Status:** Pipeline chain incomplete  
**Location:** `apps/api/src/workers/pipeline.py`  
**Impact:** Daily/weekly metrics not automatically computed after pipeline completion

**Details:**
- Architecture plan (Task 3.3) specifies `workers/aggregation.py` triggered after scoring
- `services/metrics.py` exists with `compute_daily_metrics()` and `compute_weekly_metrics()`
- **No Celery task** for metrics aggregation
- Pipeline chain in `pipeline.py` ends at `score_salesperson.s()`, no aggregation step

**What needs to be done:**
1. Create `workers/aggregation.py` with Celery task `aggregate_metrics`
2. Add to pipeline chain after `score_salesperson.s()`
3. Ensure metrics tables are populated after each recording completes

---

## 3. Planned Features Not Implemented

### 3.1 Semantic Search — Backend Exists, Frontend Incomplete

**Status:** Backend endpoint exists, frontend search page incomplete  
**Location:** `apps/api/src/api/v1/search.py`, `apps/web/src/app/(dashboard)/search/page.tsx`  
**Impact:** Semantic search functionality not fully accessible

**Details:**
- ✅ Backend: `GET /api/v1/search` with pgvector similarity search implemented
- ✅ Frontend: Search page exists with input and filters
- ❌ **Embedding generation** not automated — `TranscriptSegment.embedding` field exists but embeddings are not generated during pipeline
- ❌ Search results should show highlighted snippets (not implemented)

**What needs to be done:**
1. Add embedding generation to transcription or preprocessing worker
2. Use sentence-transformers or NVIDIA embedding API to generate 768-dim vectors
3. Store in `TranscriptSegment.embedding`
4. Implement snippet highlighting in search results

---

### 3.2 PDF Export — Not Started

**Status:** Not implemented  
**Impact:** Cannot export performance reports as planned in Sprint 6 (Task 6.4)

**Details:**
- Architecture plan specifies PDF export for salesperson performance reports
- Only CSV export service exists
- No PDF library installed (e.g., `reportlab`, `weasyprint`, `pdfkit`)

**What needs to be done:**
1. Add PDF generation library to `pyproject.toml`
2. Create `services/export.py` function `export_performance_report_pdf()`
3. Create API endpoint `GET /api/v1/export/salesperson/{id}.pdf`
4. Design PDF template with charts, scores, trends

---

### 3.3 Coaching Dashboard — Backend Data Gaps

**Status:** Frontend exists, backend data incomplete  
**Location:** `apps/web/src/app/(dashboard)/coaching/page.tsx`  
**Impact:** Coaching recommendations may not show actionable insights

**Details:**
- Frontend coaching page displays skill scores, trends, recommendations
- Backend `ConversationAnalysis` has `coaching_notes` field
- **No dedicated coaching analytics service** to aggregate coaching insights
- **No endpoint** for coaching-specific metrics (improvement areas, prioritized action items)

**What needs to be done:**
1. Create `services/coaching.py` with coaching analytics functions
2. Create API endpoint `GET /api/v1/coaching/insights`
3. Aggregate coaching notes across conversations
4. Generate prioritized action items from low-scoring dimensions

---

### 3.4 Store/Brand Comparison Analytics — Partial

**Status:** Some data exists, comparison views incomplete  
**Impact:** Brand admin cannot see cross-store comparisons as planned

**Details:**
- `GET /api/v1/analytics/salespeople-comparison` exists
- **No endpoint** for store-to-store comparison
- **No endpoint** for brand-level trend aggregation
- Architecture plan (Task 6.3) specifies store comparisons, regional trends, top objections across stores

**What needs to be done:**
1. Create `GET /api/v1/analytics/stores-comparison`
2. Create `GET /api/v1/analytics/brand-trends`
3. Aggregate objections, coaching needs, revenue risks across stores

---

### 3.5 Recording Reprocessing — Exists, But Not in Frontend

**Status:** Backend endpoint exists, frontend not wired  
**Location:** `apps/api/src/api/v1/recordings.py` (line 228: `POST /{recording_id}/reprocess`)  
**Impact:** Users cannot reprocess failed recordings from UI

**Details:**
- `POST /api/v1/recordings/{id}/reprocess` endpoint implemented
- Frontend recordings list page mentions "Re-process" action in architecture plan (Task 4.6)
- **No button or action** in frontend to trigger reprocessing

**What needs to be done:**
1. Add "Re-process" button to recordings list table
2. Add "Re-process" button to recording detail page
3. Wire to API endpoint with loading state and success notification

---

## 4. Dependency Issues

### 4.1 Pyannote.audio — Optional Dependency Not Declared

**Status:** Used in code, not in `pyproject.toml` optional dependencies  
**Location:** `apps/api/pyproject.toml`  
**Impact:** Pyannote diarization may fail if not installed

**Details:**
- `pyannote.audio>=3.3.0` is in main dependencies ✅
- `torch`, `torchaudio` are in main dependencies ✅
- `pyannote/embedding` model requires HuggingFace token
- **No optional dependency group** for diarization engines
- Architecture plan specifies fallback to NVIDIA APIs if pyannote unavailable

**What needs to be done:**
1. Add optional dependency group `[project.optional-dependencies]`:
   ```toml
   diarization = ["pyannote.audio>=3.3.0", "torch>=2.4.0"]
   voiceprint = ["resemblyzer>=0.1.4"]  # Optional fallback engine
   ```
2. Add graceful fallback logic in diarization worker if pyannote fails to load

---

### 4.2 Resemblyzer — Not Declared in Dependencies

**Status:** Used in code, not in `pyproject.toml`  
**Location:** `apps/api/src/ai/voiceprint.py` (imports `resemblyzer`)  
**Impact:** Voiceprint fallback engine will fail

**Details:**
- `resemblyzer` imported in `voiceprint.py` but not in `pyproject.toml`
- Used as fallback if pyannote embedding extraction fails
- Will cause `ImportError` at runtime

**What needs to be done:**
1. Add `resemblyzer>=0.1.4` to optional dependencies
2. Add graceful handling if resemblyzer not installed (already has try/except for ImportError)

---

### 4.3 Frontend Missing Dependencies for Planned Features

**Status:** Some packages not installed  
**Location:** `apps/web/package.json`  
**Impact:** Cannot implement all planned UI features

**Details:**
- ✅ `recharts` — charts installed
- ✅ `wavesurfer.js` — waveform player installed
- ✅ `zustand` — state management installed
- ✅ `@tanstack/react-query` — server state caching installed
- ❌ **No PDF viewer library** (for viewing exported reports)
- ❌ **No audio recording library** (for voiceprint enrollment from browser)

**What needs to be done:**
1. Add `react-pdf` if PDF report viewing is needed
2. Add `react-media-recorder` if browser-based voiceprint enrollment is needed

---

### 4.4 Docker Compose — MinIO Not Configured

**Status:** Architecture plan specifies MinIO, docker-compose.yml doesn't include it  
**Location:** `docker-compose.yml`  
**Impact:** Cannot test S3-compatible storage locally

**Details:**
- Architecture plan (Section 10) specifies MinIO on port 9000 for local S3-compatible storage
- `docker-compose.yml` only has PostgreSQL and Redis
- `.env.example` has S3 configuration section but no local S3 endpoint to test against

**What needs to be done:**
1. Add MinIO service to `docker-compose.yml`:
   ```yaml
   minio:
     image: minio/minio:latest
     container_name: samaa-minio
     ports:
       - "9000:9000"
       - "9001:9001"
     environment:
       MINIO_ROOT_USER: samaa
       MINIO_ROOT_PASSWORD: samaa_dev_password
     volumes:
       - minio_data:/data
     command: server /data --console-address ":9001"
   ```
2. Add MinIO configuration to `.env.example`
3. Create bucket initialization script

---

## 5. Configuration Gaps

### 5.1 Missing Environment Variables in .env.example

**Status:** Some referenced variables not documented  
**Location:** `.env.example`  
**Impact:** New developers may miss required configuration

**Details:**
- ✅ Database, Redis, JWT, NVIDIA API, Pyannote, VAD, Chunking, Role Classification — all documented
- ❌ `NEXT_PUBLIC_API_URL` — **Not in .env.example** (needed by frontend)
- ❌ `APP_ENV` validation — no documentation of valid values (development, staging, production)

**What needs to be done:**
1. Add `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` to `.env.example`
2. Create `.env.local.example` for frontend-specific variables
3. Document valid values for `APP_ENV`

---

### 5.2 Frontend Environment Variables — Not Documented

**Status:** No frontend .env example file  
**Location:** `apps/web/`  
**Impact:** Frontend API URL configuration unclear

**Details:**
- `api-client.ts` uses `process.env.NEXT_PUBLIC_API_URL` with fallback to `http://localhost:8000/api/v1`
- No `.env.local` or `.env.example` in `apps/web/`
- `start_servers.sh` doesn't set frontend env vars

**What needs to be done:**
1. Create `apps/web/.env.local.example`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```
2. Update `start_servers.sh` to symlink or create frontend .env

---

### 5.3 CORS Configuration — Hardcoded Origins

**Status:** CORS origins loaded from config, but config may not match deployment  
**Location:** `apps/api/src/config.py`, `.env.example`  
**Impact:** Frontend may be blocked by CORS in production

**Details:**
- `.env.example` has `CORS_ORIGINS=http://localhost:3000`
- `config.py` parses this into a list
- **No documentation** of how to configure for production domains
- No wildcard or multiple origin support documented

**What needs to be done:**
1. Document CORS configuration for production in `.env.example`:
   ```
   CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
   ```
2. Add validation in `config.py` to ensure origins are valid URLs

---

### 5.4 Database Connection Pool — Not Configured

**Status:** Default SQLAlchemy pool settings, no explicit configuration  
**Location:** `apps/api/src/database.py`  
**Impact:** May cause connection exhaustion under load

**Details:**
- `database.py` creates engine with `async_session_factory`
- No explicit pool size, max overflow, or pool timeout configuration
- Celery workers share the same database engine
- Under concurrent pipeline processing, may exhaust connections

**What needs to be done:**
1. Add pool configuration to engine creation:
   ```python
   create_async_engine(
       settings.database_url,
       pool_size=20,
       max_overflow=10,
       pool_timeout=30,
       pool_recycle=1800,
   )
   ```
2. Document pool sizing in deployment guide

---

### 5.5 Celery Beat Scheduler — Not Configured

**Status:** No periodic task scheduler  
**Location:** `apps/api/src/workers/celery_app.py`  
**Impact:** Cannot run scheduled metrics aggregation or cleanup tasks

**Details:**
- Celery app configured with workers only
- No `beat_schedule` for periodic tasks
- Architecture plan implies automated metrics aggregation
- No scheduled cleanup of old logs, temporary files, or expired tokens

**What needs to be done:**
1. Add `beat_schedule` to `celery_app.conf.update()`:
   ```python
   beat_schedule={
       "aggregate-daily-metrics": {
           "task": "src.workers.aggregation.aggregate_daily_metrics",
           "schedule": crontab(hour=1, minute=0),  # Run at 1 AM UTC
       },
   }
   ```
2. Start Celery Beat in `start_servers.sh`:
   ```bash
   celery -A src.workers.celery_app beat --loglevel=info &
   ```

---

## 6. Route Gaps — Architecture vs Implementation

### 6.1 Missing API Routes

| Planned Route (Architecture) | Status | Notes |
|---|---|---|
| `POST /api/v1/auth/logout` | ❌ Missing | Auth router has login, refresh, but no logout |
| `GET /api/v1/stores/{id}/metrics` | ❌ Missing | Specified in architecture, endpoint not wired |
| `GET /api/v1/brands/{id}/metrics` | ❌ Missing | Brand-level metrics not exposed |
| `GET /api/v1/export/recordings.csv` | ❌ Missing | Export service exists, no route |
| `GET /api/v1/export/conversations.csv` | ❌ Missing | Export service exists, no route |
| `POST /api/v1/voiceprints/enroll` | ❌ Missing | Voiceprint engine exists, no route |
| `GET /api/v1/analytics/funnel` | ❌ Missing | Sales funnel chart exists, no backend |
| `GET /api/v1/coaching/insights` | ❌ Missing | Coaching dashboard exists, no backend |

### 6.2 Frontend Route Mismatches

| Planned Route (Architecture) | Actual Route | Notes |
|---|---|---|
| `/store` (Store Manager dashboard) | `/stores` | Route name differs |
| `/salesperson` (Salesperson dashboard) | `/salespeople` | Route name differs |
| `/coaching` | ✅ `/coaching` | Matches |
| `/search` | ✅ `/search` | Matches |
| `/operations` | ✅ `/operations` | Exists but not in original architecture |

---

## 7. Priority Recommendations

### High Priority (Block Full System Functionality)

1. **Implement metrics aggregation Celery task** — Pipeline completes but metrics tables remain empty
2. **Add TanStack Query integration** — Frontend not using installed caching library
3. **Create export API endpoints** — Export service code exists but not accessible
4. **Wire voiceprint API endpoints** — Advanced speaker tracking cannot be used
5. **Fix role correction cascade** — Corrections logged but don't update transcript data

### Medium Priority (Improve User Experience)

6. **Implement semantic search embeddings** — Search backend exists but embeddings not generated
7. **Add reprocessing button to frontend** — Backend endpoint exists, UI doesn't expose it
8. **Create Zustand filter/dashboard stores** — Client state management incomplete
9. **Add MinIO to docker-compose** — Cannot test S3 storage locally
10. **Implement conversation audio extraction** — Endpoint exists, service logic missing

### Low Priority (Nice to Have)

11. **Add PDF export** — Only CSV export implemented
12. **Implement coaching analytics service** — Dedicated coaching insights aggregation
13. **Add cross-conversation speaker analytics** — Advanced customer tracking
14. **Configure Celery Beat scheduler** — Automated periodic tasks
15. **Document production CORS configuration** — Deployment readiness

---

## 8. Summary Statistics

| Category | Count | Status |
|---|---|---|
| **Missing API Endpoints** | 8 | Not wired |
| **Missing Frontend Stores** | 2 | Not created |
| **Missing Frontend Integration** | 3 (TanStack Query, reprocessing, voiceprint UI) | Partial |
| **Missing Dependencies** | 2 (resemblyzer, optional groups) | Not declared |
| **Configuration Gaps** | 5 (env vars, pool, beat, CORS, MinIO) | Not documented |
| **Incomplete Pipeline Steps** | 1 (metrics aggregation) | Missing task |
| **Unused Implemented Modules** | 3 (voiceprint, cross-conversation tracker, word attribution) | Zero wiring |

**Total Action Items:** 24

---

## 9. Next Steps

1. **Review this report** with team to prioritize action items
2. **Create GitHub issues** for each high-priority item
3. **Update implementation plan** (`plan/01-implementation-plan.md`) to reflect current status
4. **Track wiring progress** in decision log (`plan/02-decision-log.md`)
5. **Re-run this analysis** after Sprint 6 completion to verify all gaps closed

---

**Report generated by analyzing:**
- 75 Python backend files in `apps/api/src/`
- 58 TypeScript/TSX frontend files in `apps/web/src/`
- Architecture design document (`plan/00-architecture-design.md`)
- Implementation plan (`plan/01-implementation-plan.md`)
- Decision log (`plan/02-decision-log.md`)
- Configuration files (`.env.example`, `docker-compose.yml`, `pyproject.toml`, `package.json`)
