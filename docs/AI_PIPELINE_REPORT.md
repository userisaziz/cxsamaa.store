# SAMAA AI Pipeline — Complete Technical Report

**Generated:** June 13, 2026  
**Version:** 1.0  
**Scope:** End-to-end audio processing pipeline from upload to scoring

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Pipeline Stages (Detailed)](#3-pipeline-stages-detailed)
4. [Parallel Chunk Processing Architecture](#4-parallel-chunk-processing-architecture)
5. [AI Model Integration](#5-ai-model-integration)
6. [Data Models & Storage](#6-data-models--storage)
7. [Error Handling & Retry Strategy](#7-error-handling--retry-strategy)
8. [Configuration & Environment](#8-configuration--environment)
9. [Performance Characteristics](#9-performance-characteristics)
10. [Known Limitations & Future Enhancements](#10-known-limitations--future-enhancements)

---

## 1. Executive Summary

SAMAA (Sales Audio Management & AI Analysis) is a multi-stage AI pipeline that converts raw retail audio recordings (up to 12 hours) into structured business intelligence. The pipeline processes audio through 8 sequential stages, leveraging NVIDIA Riva gRPC for speech-to-text, pyannote.audio for speaker diarization, and Llama 3.3 70B via NVIDIA NIM for conversation analysis and salesperson scoring.

**Key Capabilities:**
- Multilingual support: Hindi/English/Arabic code-switching
- Parallel chunk processing for long recordings (>15 min)
- Silence-gap-aware chunking to preserve conversation boundaries
- Word-level timestamps for speaker attribution
- 5-dimensional salesperson performance scoring
- Cross-conversation tracking and voiceprint identity

**Tech Stack:**
- **Backend:** FastAPI + Celery + Redis (broker/backend)
- **Database:** PostgreSQL + pgvector
- **AI Models:** NVIDIA Riva Parakeet (STT), pyannote.audio 3.1 (diarization), Llama 3.3 70B (analysis/scoring)
- **Storage:** Local filesystem (pluggable abstraction)

---

## 2. Architecture Overview

### 2.1 High-Level Flow

```
Client Upload → API Endpoint → Celery Pipeline Chain → 8 Sequential Stages → DB Persistence
```

### 2.2 Pipeline Stage Sequence

| Stage | Task Name | Input | Output | Duration (est.) |
|-------|-----------|-------|--------|-----------------|
| 1 | `preprocess_audio` | Raw audio (MP3/WAV/M4A) | Normalized 16kHz mono WAV + chunk manifest | 10-60s |
| 2 | `dispatch_transcription` | Preprocessed audio | Chunk manifest → parallel STT tasks | Variable |
| 3 | `dispatch_diarization` | Preprocessed audio + transcripts | Speaker-labeled segments | Variable |
| 4 | `build_conversation_turns` | Word-level transcripts | Speaker turns (merged by continuity) | 5-30s |
| 5 | `classify_speaker_roles` | Conversation turns | Salesperson vs Customer labels | 5-20s |
| 6 | `segment_conversations` | Labeled turns + silence gaps | Discrete conversation objects | 5-15s |
| 7 | `analyze_conversations` | Conversation transcripts | LLM analysis (intent, products, objections, outcome) | 30-120s per conversation |
| 8 | `score_salesperson` | Conversation transcripts + analysis | 5-dimension performance scores | 15-60s per conversation |

### 2.3 Recording Status State Machine

```
UPLOADED → PREPROCESSING → TRANSCRIBING → DIARIZING → SEGMENTING → ANALYZING → SCORING → COMPLETED
                                                                                      ↓
                                                                                  FAILED (any stage)
```

### 2.4 Orchestration Architecture

**File:** `src/workers/pipeline.py`

```python
processing_chain = chain(
    preprocess_audio.s(recording_id),          # Stage 1
    dispatch_transcription.s(),                # Stage 2 (dispatcher)
    dispatch_diarization.s(),                  # Stage 3 (dispatcher)
    build_conversation_turns_task.s(),         # Stage 4
    classify_speaker_roles_task.s(),           # Stage 5
    segment_conversations.s(),                 # Stage 6
    analyze_conversations.s(),                 # Stage 7
    score_salesperson.s(),                     # Stage 8
)
```

**Key Design Pattern:** Dispatcher tasks (`dispatch_transcription`, `dispatch_diarization`) use `self.replace(chord(...))` to dynamically substitute themselves with parallel chunk processing when recordings exceed the chunking threshold.

---

## 3. Pipeline Stages (Detailed)

### 3.1 Stage 1: Audio Preprocessing

**File:** `src/workers/preprocessing.py` (387 lines)  
**Task:** `preprocess_audio`  
**Max Retries:** 3 | **Retry Delay:** 60s

#### 3.1.1 Input/Output

| Aspect | Detail |
|--------|--------|
| **Input** | Raw audio file (MP3/WAV/M4A) from storage |
| **Output** | Normalized 16kHz mono WAV + chunk manifest JSON |
| **Storage Keys** | `preprocessed/{recording_id}/audio.wav`, `preprocessed/{recording_id}/chunks/chunk_XXX.wav`, `preprocessed/{recording_id}/manifest.json` |

#### 3.1.2 Processing Steps

1. **Download:** Fetch raw audio from storage via `storage.download_sync(file_url)`
2. **Format Conversion:** Use ffmpeg subprocess to convert to WAV (avoids pydub subprocess hang in Celery)
   ```bash
   ffmpeg -y -i input.{ext} -ac 1 -ar 16000 -f wav preprocessed.wav
   ```
3. **Mono Conversion:** `audio.set_channels(1)` if stereo
4. **Resampling:** `audio.set_frame_rate(16000)` if not already 16kHz
5. **Volume Normalization:** Target -20 dBFS
   ```python
   change_in_dbfs = -20.0 - audio.dBFS
   audio = audio.apply_gain(change_in_dbfs)
   ```
6. **Silence Detection:** Detect gaps ≥ 30 seconds at -40 dBFS threshold
   ```python
   silence_ranges = detect_silence(audio, min_silence_len=30000, silence_thresh=-40)
   ```
7. **Chunk Manifest Building:** Silence-gap-aware splitting strategy (see §4)
8. **Chunk Splitting & Upload:** Export each chunk as WAV and upload to storage
9. **Database Updates:**
   - `recording.duration_seconds`
   - `recording.silence_gaps` (JSONB: `[{start, end}]`)
   - `recording.chunk_manifest` (JSONB)

#### 3.1.3 Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `TARGET_SAMPLE_RATE` | 16000 Hz | Standard for NVIDIA Riva STT |
| `TARGET_CHANNELS` | 1 | Mono audio |
| `SILENCE_THRESHOLD_DB` | -40 dB | Silence detection sensitivity |
| `SILENCE_GAP_MS` | 30000 ms (30s) | Minimum gap for conversation boundary |
| `TARGET_FORMAT` | "wav" | Output format |

---

### 3.2 Stage 2: Transcription (Speech-to-Text)

**File:** `src/workers/transcription.py` (440 lines)  
**Dispatcher Task:** `dispatch_transcription`  
**Chunk Task:** `transcribe_chunk`  
**Merge Task:** `merge_transcription_results`  
**Max Retries:** 3 | **Retry Delay:** 60s (chunk), 120s (legacy)

#### 3.2.1 Dispatch Logic

```python
manifest = load_manifest(recording_id)

if not manifest["needs_chunking"]:
    # Fast path: single task for short recordings
    return transcribe_audio_task(recording_id)
else:
    # Parallel path: chord of chunk tasks
    header = group(transcribe_chunk.s(recording_id, chunk["index"], chunk["file"])
                   for chunk in manifest["chunks"])
    raise self.replace(chord(header, merge_transcription_results.s(recording_id)))
```

#### 3.2.2 Chunk Task Details

**Task:** `transcribe_chunk`  
**Timeouts:** `soft_time_limit=600s` (10 min), `time_limit=900s` (15 min)  
**Idempotency:** `acks_late=True` + clear-and-reinsert DB pattern

**Processing:**
1. Download only its chunk file (~28MB for 15-min WAV) from `preprocessed/{recording_id}/chunks/chunk_XXX.wav`
2. Call `transcribe_audio(chunk_data)` → NVIDIA Riva gRPC STT
3. Return dict:
   ```python
   {
       "chunk_index": int,
       "segments": [{start, end, text}],
       "words": [{word, start, end, confidence}],
       "failed": bool,
       "error": str (if failed)
   }
   ```

**Failure Handling:** Returns failure sentinel instead of raising past `max_retries` to prevent chord errors.

#### 3.2.3 Merge Logic

**Task:** `merge_transcription_results`

1. Separate successful from failed chunks
2. Load manifest for chunk offsets: `chunk_offsets = {c["index"]: c["start_ms"] / 1000.0}`
3. Adjust timestamps: `seg["start"] += offset`, `seg["end"] += offset`
4. Deduplicate overlaps:
   - **Words:** `_deduplicate_words()` — keep higher-confidence version if overlap < 50ms
   - **Segments:** `_deduplicate_segments()` — remove duplicates if overlap < 1s and text matches
5. Store to `TranscriptSegment` and `WordTranscript` tables (clear-and-reinsert)

#### 3.2.4 Legacy Chunking (In-Process)

**Function:** `_transcribe_in_chunks_with_overlap()`

Used when `dispatch_transcription` fast path is taken but audio exceeds `max_audio_chunk_bytes`. Splits audio in-memory using 15-minute chunks with 30-second overlap, transcribes each, deduplicates, and returns merged results.

**Note:** This is a fallback; the preferred path is via manifest-driven parallel chunks.

---

### 3.3 Stage 3: Speaker Diarization

**File:** `src/workers/diarization.py` (316 lines)  
**Dispatcher Task:** `dispatch_diarization`  
**Chunk Task:** `diarize_chunk`  
**Merge Task:** `merge_diarization_results`  
**Max Retries:** 3 | **Retry Delay:** 120s

#### 3.3.1 Architecture

Identical dispatcher pattern to transcription:
- Fast path: `diarize_audio(recording_id)` for short recordings
- Parallel path: `chord(header, merge_diarization_results.s(recording_id))` for long recordings

#### 3.3.2 Diarization Engine

**File:** `src/ai/diarizer.py` (262 lines)

**Primary:** pyannote.audio 3.1 (`pyannote/speaker-diarization-3.1`)  
**Fallback:** NVIDIA NeMo Speaker Diarization (NIM API)

**Pyannote Configuration:**
- Device: Auto-detect (CUDA → MPS → CPU)
- HuggingFace token: Required (gated model)
- Hyperparameters optimized for retail multilingual audio

**Lazy Loading:** Thread-safe singleton pattern with double-checked locking:
```python
with _pyannote_lock:
    if _pyannote_diarizer is None:
        _pyannote_diarizer = PyannoteDiarizer(...)
```

#### 3.3.3 Speaker Label Assignment

**Function:** `assign_speaker_labels(transcript_segments, speaker_segments)`

Maps speaker diarization segments to transcript segments using time overlap containment. Each transcript segment gets assigned the speaker label of the diarization segment that contains its midpoint.

**Word-Level Propagation:** `_update_word_speaker_labels_sync()` uses O(W + S) sweep to assign speaker labels to words based on segment containment of word midpoints.

#### 3.3.4 Chunk Task Details

**Task:** `diarize_chunk`  
**Timeouts:** `soft_time_limit=1800s` (30 min), `time_limit=2400s` (40 min)

Returns:
```python
{
    "chunk_index": int,
    "speaker_segments": [{start, end, speaker}],
    "failed": bool,
    "error": str (if failed)
}
```

**No Cross-Chunk Speaker Reconciliation:** Chunks split at silence-gap boundaries, so each chunk contains complete conversations with independently valid speaker labels.

---

### 3.4 Stage 4: Conversation Turn Builder

**File:** `src/workers/turn_builder.py` (123 lines)  
**Task:** `build_conversation_turns_task`  
**Max Retries:** 3 | **Retry Delay:** 60s

#### 3.4.1 Purpose

Merges word-level transcripts into speaker turns based on:
1. **Speaker continuity:** Same speaker = same turn
2. **Gap detection:** Gap > 1s = new turn

#### 3.4.2 Processing

1. Load `WordTranscript` records ordered by `start_time`
2. Call `build_conversation_turns(word_transcripts)` from `src/ai/conversation_builder.py`
3. Store `ConversationTurn` records (clear-and-reinsert)

**Output:**
```python
{
    "speaker": str,
    "start_time": float,
    "end_time": float,
    "text": str,
    "word_count": int
}
```

---

### 3.5 Stage 5: Speaker Role Classification

**File:** `src/workers/role_classification.py` (138 lines)  
**Task:** `classify_speaker_roles_task`  
**Max Retries:** 3 | **Retry Delay:** 60s

#### 3.5.1 Purpose

Classify each speaker as **Salesperson** or **Customer** using LLM-based classification with heuristic fallback.

#### 3.5.2 Processing

1. Load `ConversationTurn` records
2. Call `classify_speaker_roles(conversation_turns, use_llm=True)` from `src/ai/role_classifier.py` (510 lines)
3. Store `SpeakerRole` records and update `ConversationTurn.role_label`

**Classification Output:**
```python
{
    "Speaker_0": {
        "role": "SALESPERSON" | "CUSTOMER",
        "method": "llm" | "heuristic",
        "confidence": float (0.0-1.0)
    },
    ...
}
```

#### 3.5.3 Role Classifier Architecture

**File:** `src/ai/role_classifier.py` (510 lines)

**Primary:** LLM classification via NVIDIA NIM (Llama 3.3 70B)  
**Fallback:** Heuristic-based classification using:
- Speaking time ratio (salesperson typically talks more)
- Greeting detection (first speaker often salesperson)
- Turn-taking patterns
- Keyword analysis (sales-specific vocabulary)

---

### 3.6 Stage 6: Conversation Segmentation

**File:** `src/workers/segmentation.py` (148 lines)  
**Task:** `segment_conversations`  
**Max Retries:** 3 | **Retry Delay:** 60s

#### 3.6.1 Purpose

Split continuous recording into discrete customer conversations per PRD AI-05.

#### 3.6.2 Segmentation Signals

| Signal | Rule | Priority |
|--------|------|----------|
| Silence gap | Gap ≥ 30 seconds → conversation boundary | High |
| Greeting detection | Salesperson greeting phrase → new conversation start | Medium |
| Departure detection | Farewell phrases → conversation end | Medium |
| New speaker entry | New speaker after silence → new conversation | Low |

#### 3.6.3 Processing

1. Load labeled transcript segments with speaker roles
2. Load silence gaps from `recording.silence_gaps` (JSONB)
3. Call `segment_conversations_ai(labeled_segments, silence_gaps)` from `src/ai/segmenter.py` (321 lines)
4. Store `Conversation` records (clear-and-reinsert)

**Output:**
```python
{
    "start_time": float,
    "end_time": float,
    "segment_count": int
}
```

---

### 3.7 Stage 7: Conversation Analysis

**File:** `src/workers/analysis.py` (236 lines)  
**Task:** `analyze_conversations`  
**Max Retries:** 3 | **Retry Delay:** 120s

#### 3.7.1 Purpose

Analyze each conversation using Llama 3.3 70B to extract structured business intelligence.

#### 3.7.2 Analysis Schema

```json
{
    "intent": "string",
    "customer_expectation": "string | null",
    "products": ["string"],
    "budget": "string | null",
    "objections": [
        {
            "category": "Price|Features|Timing|Trust|Competitor|Other",
            "issue": "string",
            "response": "string"
        }
    ],
    "competitors": ["string"],
    "closing_attempt": boolean,
    "outcome": "SALE_MADE | LOST | FOLLOW_UP_NEEDED",
    "loss_reason": "string | null",
    "confidence": 0-100,
    "summary": "string",
    "coaching_notes": "string"
}
```

#### 3.7.3 Processing

For each conversation:
1. Load transcript segments within conversation time range
   ```python
   TranscriptSegment.start_time >= conv.start_time
   TranscriptSegment.end_time <= conv.end_time + 1.0
   ```
2. Call `analyze_conversation_ai(segments)` from `src/ai/analyzer.py` (228 lines)
3. Check confidence threshold: `analysis["confidence"] >= MIN_CONFIDENCE_THRESHOLD (50)`
4. Store `ConversationAnalysis` record (upsert)
5. Update `Conversation.summary`

**LLM Configuration:**
- Model: Llama 3.3 70B via NVIDIA NIM
- Temperature: 0.1
- Max tokens: 2048
- Response format: `json_object`
- Retries: 2 (for malformed JSON)

**Confidence Threshold Enforcement:** Analysis discarded if confidence < 50% (configurable via `MIN_CONFIDENCE_THRESHOLD`)

**Retry Logic:** If LLM returns malformed JSON, appends correction prompt and retries up to 2 times.

---

### 3.8 Stage 8: Salesperson Scoring

**File:** `src/workers/scoring.py` (295 lines)  
**Task:** `score_salesperson`  
**Max Retries:** 3 | **Retry Delay:** 120s

#### 3.8.1 Purpose

Score salesperson performance across 5 dimensions per PRD AI-07.

#### 3.8.2 Scoring Dimensions

| Dimension | Criteria | Weight |
|-----------|----------|--------|
| **Greeting Score** | Warmth, professionalism, speed of initial greeting | 20% |
| **Discovery Score** | Quality and depth of needs-finding questions | 20% |
| **Product Knowledge** | Accuracy and depth of product explanations | 20% |
| **Objection Handling** | Effectiveness at addressing and resolving objections | 20% |
| **Closing Score** | Number and quality of closing attempts | 20% |

#### 3.8.3 Scoring Schema

```json
{
    "greeting_score": 0-100,
    "discovery_score": 0-100,
    "product_knowledge_score": 0-100,
    "objection_handling_score": 0-100,
    "closing_score": 0-100
}
```

**Scoring Rubric (per dimension):**
- **90-100:** Excellent performance
- **70-89:** Good with room for improvement
- **50-69:** Basic/needs development
- **0-49:** Poor/absent

#### 3.8.4 Processing

For each conversation:
1. Load transcript segments within conversation time range
2. Call `score_salesperson_performance(segments)` from `src/ai/scorer.py` (204 lines)
3. Store scores in `ConversationAnalysis.scores` (JSONB, upsert)
4. Mark recording as `COMPLETED` with `processed_at` timestamp
5. Update daily metrics for salesperson and store

**LLM Configuration:**
- Model: Llama 3.3 70B via NVIDIA NIM
- Temperature: 0.1
- Max tokens: 512
- Response format: `json_object`
- Retries: 2 (for malformed JSON)

#### 3.8.5 Daily Metrics Aggregation

**Function:** `_update_daily_metrics_sync(recording_id)`

Computes and upserts `DailyMetrics` for:
- Salesperson level (`entity_type="SALESPERSON"`)
- Store level (`entity_type="STORE"`)

**Metrics Computed:**
- `conversation_count`: Total conversations for entity on date
- `avg_score`: Average of all dimension scores across conversations
- `conversion_rate`: `(sale_count / conv_count) * 100`

---

## 4. Parallel Chunk Processing Architecture

### 4.1 Chunk Manifest Structure

**Generated by:** `preprocess_audio` stage  
**Storage:** `preprocessed/{recording_id}/manifest.json` (JSONB in DB + file in storage)

```json
{
    "recording_id": "uuid-string",
    "duration_ms": 3600000,
    "needs_chunking": true,
    "chunks": [
        {
            "index": 0,
            "start_ms": 0,
            "end_ms": 900000,
            "audio_start_ms": 0,
            "audio_end_ms": 930000,
            "file": "chunk_000.wav"
        },
        {
            "index": 1,
            "start_ms": 900000,
            "end_ms": 1800000,
            "audio_start_ms": 870000,
            "audio_end_ms": 1830000,
            "file": "chunk_001.wav"
        }
    ]
}
```

**Key Fields:**
- `start_ms` / `end_ms`: Logical content boundaries (used for timestamp adjustment)
- `audio_start_ms` / `audio_end_ms`: Actual audio extraction boundaries (includes overlap)
- `file`: Filename for chunk in storage

### 4.2 Silence-Gap-Aware Chunking Strategy

**File:** `src/workers/preprocessing.py`, function `_build_chunk_manifest()`

**Algorithm:**
1. Detect silence gaps ≥ 30 seconds at -40 dBFS
2. Use silence gap midpoints as preferred split points
3. Filter split points:
   - Must be ≥ 30s from previous split (half chunk minimum)
   - OR ≥ 60s from previous split (fallback)
4. Sub-split any region exceeding `audio_chunk_duration_minutes` using fixed windows
5. Apply 30-second overlap at each chunk boundary

**Example:**
```
Recording: 8 hours (28,800 seconds)
Silence gaps detected: 45 gaps ≥ 30s
Chunks generated: ~38 chunks (average 12.6 min each)
Overlap: 30 seconds per boundary
```

### 4.3 Celery Chord Execution Model

**Dispatcher Pattern:**
```python
@celery_app.task(bind=True, name="dispatch_transcription")
def dispatch_transcription(self, recording_id: str):
    manifest = load_manifest(recording_id)
    
    if not manifest["needs_chunking"]:
        return transcribe_audio_task(recording_id)  # Fast path
    
    # Parallel path
    header = group(
        transcribe_chunk.s(recording_id, chunk["index"], chunk["file"])
        for chunk in manifest["chunks"]
    )
    raise self.replace(chord(header, merge_transcription_results.s(recording_id)))
```

**Execution Flow:**
```
1. dispatch_transcription task starts
2. Loads manifest from storage
3. Creates group of N transcribe_chunk tasks
4. Replaces itself with chord(header, callback)
5. Celery executes all chunks in parallel (limited by worker concurrency)
6. When ALL chunks complete, callback (merge_transcription_results) runs
7. Callback receives list of chunk results, merges, stores to DB
8. Returns recording_id to next pipeline stage
```

**Worker Concurrency Impact:**
- Default: `worker_prefetch_multiplier=1` (fair scheduling)
- Actual parallelism limited by number of Celery workers
- Recommended: 4-8 workers for optimal throughput

### 4.4 Chunk Task Idempotency

All chunk tasks follow **clear-and-reinsert** pattern:
```python
# Merge callback clears existing data before reinsert
session.query(TranscriptSegment).filter(
    TranscriptSegment.recording_id == uuid.UUID(recording_id)
).delete()
# Then inserts merged results
```

**Benefits:**
- Safe to retry on failure
- No duplicate data on reprocessing
- Deterministic results

### 4.5 Failure Sentinel Pattern

Chunk tasks return failure dicts instead of raising past `max_retries`:
```python
return {
    "chunk_index": chunk_index,
    "segments": [],
    "words": [],
    "failed": True,
    "error": str(exc),
}
```

**Why:** Prevents Celery chord error propagation (single chunk failure would cancel all other chunks and skip callback).

**Callback Handling:**
```python
successful = [r for r in chunk_results if not r.get("failed")]
failed = [r for r in chunk_results if r.get("failed")]

if not successful:
    fail_and_halt(recording_id, "All transcription chunks failed")
# Proceed with partial results if some chunks succeeded
```

---

## 5. AI Model Integration

### 5.1 NVIDIA Riva gRPC STT (Speech-to-Text)

**File:** `src/ai/stt.py` (252 lines)  
**Class:** `RivaSTTClient`

**Model:** Parakeet 1.1B RNNT  
**Endpoint:** `grpc.nvcf.nvidia.com:443`  
**Function ID:** `71203149-d3b7-4460-8231-1be2543a1fca`

**Configuration:**
```python
encoding=raudio.AudioEncoding.LINEAR_PCM  # 16-bit PCM
sample_rate_hertz=16000
audio_channel_count=1
language_code="en-US"
profanity_filter=False
enable_automatic_punctuation=True
enable_word_time_offsets=True  # Critical for speaker attribution
```

**Response Parsing:**
- Extracts word-level timestamps from gRPC response
- Groups words into segments based on pause gaps
- Converts Riva time values (milliseconds) to seconds
- Returns both segment-level and word-level transcripts

**Time Conversion Logic:**
```python
def _to_seconds(t) -> float:
    if hasattr(t, 'seconds'):  # google.protobuf.Duration
        return t.seconds + getattr(t, 'nanos', 0) / 1e9
    if isinstance(t, int):  # Milliseconds
        return t / 1000.0
    return float(t)  # Already seconds
```

**Migration Note:** Migrated from NVIDIA REST API to gRPC Riva client. Requires `riva-client` package.

---

### 5.2 pyannote.audio (Speaker Diarization)

**File:** `src/ai/pyannote_diarizer.py` (226 lines)  
**Class:** `PyannoteDiarizer`

**Model:** `pyannote/speaker-diarization-3.1`  
**Requirements:** HuggingFace token (gated model)

**Device Auto-Detection:**
```python
if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"
```

**Hyperparameter Tuning (Retail Audio):**
```python
self.pipeline.instantiate({
    "segmentation": {
        "min_duration_off": 0.5,  # Minimum non-speech duration
        "min_duration_on": 0.3,   # Minimum speech duration
    },
    "clustering": {
        "method": "centroid",
        "threshold": 0.5,  # Optimized for multilingual code-switching
    }
})
```

**Fallback Chain:**
```
1. Try pyannote.audio 3.1 (primary)
2. If disabled or fails → Try pyannote community models
3. If all fail → Fall back to NVIDIA NeMo NIM API
```

**Performance:**
- 8-hour recording: ~15-25 min on CPU, ~3-5 min on GPU
- Accuracy: Significantly better than cloud APIs for overlapping speech and code-switching

---

### 5.3 Llama 3.3 70B (Analysis & Scoring)

**File:** `src/ai/nvidia_client.py` (273 lines)  
**Class:** `nvidia_client` (singleton)

**Model:** `meta/llama-3.3-70b-instruct`  
**Endpoint:** NVIDIA NIM API (REST)

**Common Configuration:**
```python
temperature=0.1          # Low temperature for deterministic outputs
max_tokens=2048          # Analysis, 512 for scoring
response_format={"type": "json_object"}  # Enforce JSON output
```

**JSON Parsing Robustness:**
```python
# Attempt 1: Direct JSON parse
try:
    return json.loads(response_text)
except json.JSONDecodeError:
    pass

# Attempt 2: Extract from markdown code block
json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
if json_match:
    return json.loads(json_match.group(1))
```

**Retry Strategy:**
- Max 2 retries for malformed JSON
- Appends correction prompt to message history
- Returns `None` if all retries exhausted

---

## 6. Data Models & Storage

### 6.1 Core Database Models

**Tables:**

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| **Recording** | `id`, `file_url`, `format`, `duration_seconds`, `status`, `silence_gaps` (JSONB), `chunk_manifest` (JSONB), `processed_at` | → Salesperson, ← TranscriptSegment, ← Conversation |
| **TranscriptSegment** | `id`, `recording_id`, `speaker_label`, `start_time`, `end_time`, `text` | ← Recording |
| **WordTranscript** | `id`, `recording_id`, `word`, `start_time`, `end_time`, `confidence`, `speaker_label` | ← Recording |
| **ConversationTurn** | `id`, `recording_id`, `speaker_label`, `role_label`, `start_time`, `end_time`, `text`, `word_count` | ← Recording |
| **SpeakerRole** | `id`, `recording_id`, `speaker_label`, `role_label`, `classification_method`, `confidence` | ← Recording |
| **Conversation** | `id`, `recording_id`, `salesperson_id`, `start_time`, `end_time`, `duration_seconds`, `segment_count`, `summary` | ← Recording, ← ConversationAnalysis |
| **ConversationAnalysis** | `id`, `conversation_id`, `intent`, `products` (JSONB), `objections` (JSONB), `outcome`, `confidence`, `scores` (JSONB), `summary`, `coaching_notes` | ← Conversation |
| **DailyMetrics** | `id`, `entity_id`, `entity_type`, `date`, `conversation_count`, `avg_score`, `conversion_rate` | Computed aggregate |

### 6.2 Storage Layout

**Local Storage Structure:**
```
uploads/
├── {recording_id}.{ext}              # Original uploaded audio
└── preprocessed/
    └── {recording_id}/
        ├── audio.wav                  # Full preprocessed audio
        ├── manifest.json              # Chunk manifest
        └── chunks/
            ├── chunk_000.wav          # Chunk files
            ├── chunk_001.wav
            └── ...
```

**Storage Abstraction:**
- Interface: `src/storage/local.py`
- Methods: `download_sync()`, `upload_sync()`
- Pluggable: Can swap for S3/GCS implementation

### 6.3 JSONB Fields

**`Recording.silence_gaps`:**
```json
[
    {"start": 120.5, "end": 155.2},
    {"start": 360.0, "end": 395.8}
]
```

**`Recording.chunk_manifest`:**
```json
{
    "recording_id": "uuid",
    "duration_ms": 3600000,
    "needs_chunking": true,
    "chunks": [...]
}
```

**`ConversationAnalysis.scores`:**
```json
{
    "greeting_score": 85,
    "discovery_score": 72,
    "product_knowledge_score": 90,
    "objection_handling_score": 68,
    "closing_score": 75
}
```

---

## 7. Error Handling & Retry Strategy

### 7.1 Task Retry Configuration

| Task | Max Retries | Retry Delay | Soft Timeout | Hard Timeout |
|------|-------------|-------------|--------------|--------------|
| `preprocess_audio` | 3 | 60s | - | - |
| `transcribe_chunk` | 3 | 60s | 600s (10 min) | 900s (15 min) |
| `diarize_chunk` | 3 | 120s | 1800s (30 min) | 2400s (40 min) |
| `build_conversation_turns_task` | 3 | 60s | - | - |
| `classify_speaker_roles_task` | 3 | 60s | - | - |
| `segment_conversations` | 3 | 60s | - | - |
| `analyze_conversations` | 3 | 120s | - | - |
| `score_salesperson` | 3 | 120s | - | - |

**Global Limits (Celery config):**
- `task_soft_time_limit`: 3600s (1 hour)
- `task_time_limit`: 7200s (2 hours)

### 7.2 PipelineHalted Pattern

**File:** `src/workers/pipeline_control.py`

```python
class PipelineHalted(Exception):
    """Recording failed a validation step — do not retry, do not continue chain."""

def fail_and_halt(recording_id: str, reason: str) -> None:
    """Mark recording FAILED and halt the chain without retries."""
    _update_recording_status_sync(recording_id, RecordingStatus.FAILED, reason)
    raise PipelineHalted(reason)
```

**Usage:**
```python
try:
    if not transcript_segments:
        fail_and_halt(recording_id, "No transcript segments found")
except PipelineHalted:
    raise Ignore()  # Celery marks task as ignored, chain stops
```

**When to Use:**
- Missing prerequisites (no transcripts, no words)
- Validation failures (empty results)
- Business logic violations

### 7.3 Retry vs Halt Decision Tree

```
Task fails
├─ Is it a transient error? (network timeout, API rate limit)
│  ├─ YES → Retry (up to max_retries with exponential backoff)
│  └─ NO → Is it a validation failure?
│     ├─ YES → fail_and_halt() + raise Ignore()
│     └─ NO → Update status to FAILED + re-raise exception
```

### 7.4 Chord Failure Handling

**Problem:** If one chunk task raises exception past `max_retries`, Celery cancels chord callback.

**Solution:** Return failure sentinel instead of raising:
```python
except Exception as exc:
    if self.request.retries < self.max_retries:
        raise self.retry(exc=exc)
    # Return sentinel instead of raising
    return {
        "chunk_index": chunk_index,
        "segments": [],
        "failed": True,
        "error": str(exc),
    }
```

**Callback Logic:**
```python
successful = [r for r in chunk_results if not r.get("failed")]
if not successful:
    fail_and_halt(recording_id, "All chunks failed")
# Proceed with partial results
```

### 7.5 Status Update Timing

Each task updates `Recording.status` at **task start**:
```python
@celery_app.task(bind=True)
def preprocess_audio(self, recording_id: str):
    _update_recording_status_sync(recording_id, RecordingStatus.PREPROCESSING)
    # ... processing ...
```

**Final Status:**
- **Success:** `RecordingStatus.COMPLETED` set by `score_salesperson` stage
- **Failure:** `RecordingStatus.FAILED` with `error_message` populated

---

## 8. Configuration & Environment

### 8.1 Environment Variables

**File:** `src/config.py` (via `pydantic-settings`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | str | - | Async PostgreSQL URL |
| `DATABASE_URL_SYNC` | str | - | Sync PostgreSQL URL (Celery) |
| `REDIS_URL` | str | `redis://localhost:6379/0` | Redis broker/backend |
| `NVIDIA_API_KEY` | str | - | NVIDIA NIM API key |
| `PYANNOTE_HF_TOKEN` | str | - | HuggingFace token for pyannote |
| `DIARIZATION_USE_PYANNOTE` | bool | `True` | Enable pyannote diarization |
| `PYANNOTE_MODEL_NAME` | str | `pyannote/speaker-diarization-3.1` | Pyannote model |
| `PYANNOTE_DEVICE` | str | `auto` | Device: cpu/cuda/mps |
| `AUDIO_CHUNK_DURATION_MINUTES` | int | `15` | Max chunk duration |
| `AUDIO_CHUNK_OVERLAY_SECONDS` | int | `30` | Overlap between chunks |
| `MAX_AUDIO_CHUNK_BYTES` | int | `50_000_000` | ~50MB threshold for chunking |

### 8.2 Celery Configuration

**File:** `src/workers/celery_app.py`

```python
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,              # Redelivery on worker crash
    worker_prefetch_multiplier=1,     # Fair scheduling
    task_soft_time_limit=3600,        # 1 hour
    task_time_limit=7200,             # 2 hours
)
```

**Key Settings:**
- `task_acks_late=True`: Ensures chunk tasks redelivered on worker crash
- `worker_prefetch_multiplier=1`: Prevents one worker hogging all chunk tasks
- `task_track_started=True`: Enables progress monitoring

### 8.3 Worker Launch Commands

**macOS (avoid fork crash):**
```bash
celery -A src.workers.celery_app worker --loglevel=info --pool=solo
```

**Production (multi-worker):**
```bash
celery -A src.workers.celery_app worker --loglevel=info --concurrency=4
```

**Flower (monitoring):**
```bash
celery -A src.workers.celery_app flower --port=5555
```

---

## 9. Performance Characteristics

### 9.1 Processing Time Estimates

**8-Hour Recording (typical retail day):**

| Stage | CPU Time | Wall Clock (4 workers) | Notes |
|-------|----------|------------------------|-------|
| Preprocessing | 2-5 min | 2-5 min | Sequential, ffmpeg dominates |
| Chunking | N/A | N/A | Part of preprocessing |
| Transcription (15 min chunks) | ~4 min/chunk | 15-20 min | 32 chunks × 4 workers = 8 batches |
| Diarization (15 min chunks) | ~3 min/chunk | 12-25 min | 32 chunks × 4 workers; GPU vs CPU variance |
| Turn Building | 30-60s | 30-60s | Sequential |
| Role Classification | 10-30s | 10-30s | Sequential, LLM call |
| Segmentation | 10-20s | 10-20s | Sequential |
| Analysis (per conversation) | 15-60s | 5-10 min | Depends on conversation count (typically 30-50) |
| Scoring (per conversation) | 10-30s | 3-8 min | Depends on conversation count |
| **TOTAL** | **~4-6 hours** | **~40-70 min** | Wall clock with parallelism |

**Short Recording (< 15 min):**
- Total: 3-8 minutes (no chunking overhead)

### 9.2 Memory Usage

| Process | Peak Memory | Notes |
|---------|-------------|-------|
| ffmpeg conversion | ~200MB | Scales with audio file size |
| pyannote diarization (CPU) | ~2GB | Model loading + inference |
| pyannote diarization (GPU) | ~4GB VRAM | Model + intermediate activations |
| LLM API calls | ~50MB | HTTP requests only, no local model |
| Celery worker (base) | ~100MB | Per worker process |

### 9.3 Storage Requirements

**Per 8-Hour Recording:**

| Component | Size | Notes |
|-----------|------|-------|
| Original audio (MP3 128kbps) | ~450MB | Upload |
| Preprocessed WAV (16kHz mono) | ~1.1GB | 16-bit PCM |
| Chunks (32 × ~28MB) | ~900MB | With overlap |
| **Total Storage** | **~2.5GB** | Per recording |

### 9.4 Bottleneck Analysis

**Primary Bottlenecks:**
1. **Transcription:** NVIDIA Riva API latency (~4 min per 15-min chunk)
2. **Diarization:** pyannote inference time (CPU: 3 min/chunk, GPU: 1 min/chunk)
3. **LLM Analysis:** Per-conversation sequential calls (30-50 conversations × 15-60s)

**Optimization Opportunities:**
- Parallel analysis/scoring (currently sequential loop)
- GPU acceleration for pyannote (10x speedup)
- Cache LLM responses for identical transcripts

---

## 10. Known Limitations & Future Enhancements

### 10.1 Current Limitations

1. **Sequential LLM Calls:** Analysis and scoring loop processes conversations one-by-one. Could parallelize with chord.

2. **No Cross-Chunk Speaker Reconciliation:** Speaker labels (Speaker_0, Speaker_1) are chunk-local. Same speaker in different chunks may get different labels.

3. **No Streaming Support:** Pipeline assumes complete file upload. No real-time processing.

4. **Single Language Code:** STT uses `en-US` only. No multilingual STT (relies on code-switching robustness of Parakeet model).

5. **Local Storage Only:** No S3/GCS backend implemented (abstraction exists but not wired).

6. **No Progress Reporting:** Status updates only at stage transitions. No granular progress (% complete).

7. **Fixed Confidence Threshold:** `MIN_CONFIDENCE_THRESHOLD = 50` is hardcoded. Should be configurable per brand/store.

8. **No Voiceprint Persistence:** Voiceprint embeddings computed but not stored for cross-recording speaker matching.

### 10.2 Planned Enhancements

**Phase A: Parallel Analysis & Scoring**
- Convert `analyze_conversations` loop to chord
- Parallel LLM calls for independent conversations
- Estimated speedup: 3-5x for analysis stage

**Phase B: Cross-Recording Speaker Identity**
- Store voiceprint embeddings in pgvector
- Match speakers across recordings
- Resolve "Speaker_0" to consistent identity (e.g., "John - Salesperson")

**Phase C: Streaming Pipeline**
- WebSocket-based real-time transcription
- Incremental diarization on streaming chunks
- Live conversation detection

**Phase D: Multilingual STT**
- Language detection preprocessing
- Per-chunk language code routing
- Mixed-language transcript handling

**Phase E: Cloud Storage Integration**
- S3/GCS backend implementation
- Presigned URL upload flow
- CDN integration for playback

### 10.3 Monitoring & Observability Gaps

**Current:**
- Celery logs (info/error)
- Recording status in DB
- Manual `reprocess_all.py` script for monitoring

**Needed:**
- Flower dashboard integration
- Prometheus metrics export
- Stage timing histograms
- Error rate alerting
- Cost tracking (API calls × token usage)

---

## Appendix A: File Inventory

| File | Lines | Responsibility |
|------|-------|----------------|
| `src/workers/pipeline.py` | 44 | Pipeline orchestration |
| `src/workers/pipeline_control.py` | 24 | Halt/Ignore helpers |
| `src/workers/celery_app.py` | 43 | Celery configuration |
| `src/workers/preprocessing.py` | 387 | Audio normalization, chunking |
| `src/workers/transcription.py` | 440 | STT dispatch, chunking, merging |
| `src/workers/diarization.py` | 316 | Speaker diarization dispatch |
| `src/workers/turn_builder.py` | 122 | Word-to-turn merging |
| `src/workers/role_classification.py` | 137 | LLM/heuristic role classification |
| `src/workers/segmentation.py` | 147 | Conversation boundary detection |
| `src/workers/analysis.py` | 235 | LLM conversation analysis |
| `src/workers/scoring.py` | 294 | 5-dimension performance scoring |
| `src/ai/stt.py` | 252 | NVIDIA Riva gRPC client |
| `src/ai/diarizer.py` | 262 | pyannote/NVIDIA fallback |
| `src/ai/pyannote_diarizer.py` | 226 | pyannote.audio wrapper |
| `src/ai/analyzer.py` | 228 | Llama 3.3 analysis prompt |
| `src/ai/scorer.py` | 204 | Llama 3.3 scoring prompt |
| `src/ai/role_classifier.py` | 510 | Role classification logic |
| `src/ai/segmenter.py` | 321 | Conversation segmentation |
| `src/ai/conversation_builder.py` | 152 | Turn building algorithm |
| `src/ai/nvidia_client.py` | 273 | NVIDIA NIM REST client |
| **TOTAL** | **~4,500** | Pipeline implementation |

---

## Appendix B: Testing Strategy

**Test Files:**
- `tests/test_workers.py`: Unit tests for pipeline chain structure
- `tests/test_pipeline_integration.py`: Integration tests for stage ordering
- `tests/test_diarization.py`: Diarization accuracy tests

**Coverage Gaps:**
- No end-to-end pipeline tests with real audio
- No chunk merging edge case tests
- No LLM response parsing tests
- No failure scenario tests (network errors, API failures)

---

## Appendix C: Reprocessing Workflow

**Script:** `reprocess_all.py`

**Usage:**
```bash
python reprocess_all.py --token <jwt-token>
```

**Monitors:**
- Stage-by-stage status polling
- Real-time emoji-based progress indicators
- Automatic retry on FAILED status

**Stage Emojis:**
```
📤 UPLOADED → 🔧 PREPROCESSING → 📝 TRANSCRIBING → 🎯 DIARIZING → ✂️ SEGMENTING → 🧠 ANALYZING → 📊 SCORING → ✅ COMPLETED / ❌ FAILED
```

---

**End of Report**

*For questions or clarifications, review the corresponding source files listed in Appendix A or consult the repository wiki at `.qoder/repowiki/`.*