# SAMAA AI Pipeline Architecture

> Complete end-to-end flow from audio upload to sales intelligence insights

---

## Pipeline Overview

The SAMAA AI pipeline processes retail sales recordings through **9 sequential stages**, orchestrated by Celery. The pipeline supports recordings up to **9+ hours** with memory-efficient streaming (peak RAM ~50MB) and parallel chunk processing for STT and diarization.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SAMAA AI PIPELINE                            │
│                                                                 │
│  Audio Upload → Preprocessing → STT → Diarization → Turns      │
│       ↓                                                         │
│  Role Classification → Segmentation → Audio Stitching           │
│       ↓                                                         │
│  LLM Analysis → Performance Scoring → Dashboard Insights        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Audio Preprocessing

**File:** `src/workers/preprocessing.py`  
**Celery Task:** `preprocess_audio`  
**Status:** `PREPROCESSING`

### Purpose
Convert raw audio uploads to standardized 16kHz mono WAV, detect silence gaps, and split into chunks for parallel processing.

### Key Operations

1. **Download** source audio from storage (R2/S3/local)
2. **Convert** to 16kHz mono WAV via ffmpeg (streaming, no RAM spike)
3. **Normalize** loudness using EBU R128 standard (-20 LUFS target)
4. **Detect Silence** gaps using ffmpeg `silencedetect` filter (-40dB threshold, 30s minimum)
5. **Split into Chunks** with 30-second overlap at boundaries
6. **Upload** preprocessed audio + chunk manifest to storage

### Memory Efficiency
- All audio manipulation delegated to ffmpeg subprocesses
- Peak RAM: **~50 MB** regardless of recording length
- pydub removed from hot path entirely

### Output
```
preprocessed/{recording_id}/
├── audio.wav              # Full 16kHz mono WAV
└── manifest.json          # Chunk boundaries + metadata
```

### Chunk Manifest Structure
```json
{
  "recording_id": "uuid",
  "duration_ms": 32400000,
  "needs_chunking": true,
  "chunks": [
    {
      "index": 0,
      "start_ms": 0,
      "end_ms": 900000,
      "audio_start_ms": 0,
      "audio_end_ms": 930000,
      "file": "chunk_000.wav"
    }
  ]
}
```

---

## Stage 2: Transcription (STT)

**File:** `src/workers/transcription.py`  
**Celery Task:** `dispatch_transcription` → `transcribe_chunk` (parallel)  
**Status:** `TRANSCRIBING`

### Purpose
Convert audio to text with word-level timestamps using NVIDIA Riva Parakeet STT.

### Architecture

```
dispatch_transcription
    ├─ Load manifest from storage
    ├─ Calculate chunk count from manifest["chunks"]
    │
    ├─ If single chunk (fast path):
    │   └─ transcribe_audio_task(recording_id)
    │       ├─ Download preprocessed audio.wav
    │       ├─ Apply VAD filter (optional, strips silence)
    │       ├─ Call transcribe_audio(audio_bytes)
    │       └─ Store segments + words to DB
    │
    └─ If multiple chunks (parallel path):
        └─ chord(
              [transcribe_chunk.s(recording_id, chunk_idx) for chunk_idx in range(n)],
              merge_transcription_results.s(recording_id)
           )
        │
        ├─ transcribe_chunk(recording_id, chunk_idx):
        │   ├─ Download chunk_{idx:03d}.wav from storage
        │   ├─ Apply VAD filter to chunk (if enabled)
        │   ├─ Call transcribe_audio(chunk_bytes)
        │   └─ Return (chunk_idx, segments, words, speech_segments)
        │
        └─ merge_transcription_results(results, recording_id):
            ├─ Sort results by chunk_idx
            ├─ Remap timestamps from chunk-local → global timeline
            ├─ Deduplicate overlap regions (30s boundary)
            ├─ Store all segments + words to DB
            └─ Return recording_id
```

### Chunking Strategy

**Why chunk?**
- NVIDIA Riva API has file size limits (25 MB for REST, unlimited for gRPC but timeouts apply)
- Parallel processing reduces wall-clock time for long recordings
- Memory efficiency: process 15-min chunks instead of loading 9-hour file

**Chunk Configuration:**
```python
# From settings
AUDIO_CHUNK_DURATION_MINUTES = 15    # 15-minute chunks
AUDIO_CHUNK_OVERLAP_SECONDS = 30     # 30-second overlap at boundaries

# Calculated at runtime
chunk_duration_ms = 15 * 60 * 1000   # 900,000 ms
overlap_ms = 30 * 1000               # 30,000 ms
```

**Chunk Manifest Example (9-hour recording):**
```json
{
  "recording_id": "abc-123",
  "duration_ms": 32400000,  // 9 hours
  "needs_chunking": true,
  "chunks": [
    {
      "index": 0,
      "start_ms": 0,
      "end_ms": 900000,           // 15 min
      "audio_start_ms": 0,
      "audio_end_ms": 930000,     // +30s overlap
      "file": "chunk_000.wav"
    },
    {
      "index": 1,
      "start_ms": 900000,
      "end_ms": 1800000,          // 30 min
      "audio_start_ms": 870000,   // -30s overlap (from prev chunk)
      "audio_end_ms": 1830000,    // +30s overlap
      "file": "chunk_001.wav"
    }
    // ... 34 more chunks ...
  ]
}
```

### VAD (Voice Activity Detection) Integration

**Purpose:** Strip silence before STT to reduce API costs by 30-50%

**Implementation:**
```python
def _apply_vad_filter(audio_bytes: bytes) -> tuple[bytes, list[dict]]:
    """Apply Silero VAD to detect speech segments.
    
    Returns:
        - filtered_audio: Audio with silence removed
        - speech_segments: [{"start": 0.0, "end": 5.2}, ...]
    """
    # Lazy import torch/torchaudio (may not be installed)
    import torch
    from src.ai.vad import vad_filter_audio
    
    return vad_filter_audio(audio_bytes)
```

**VAD Configuration:**
```python
VAD_USE_SILERO = True
VAD_FILTER_BEFORE_STT = True
VAD_THRESHOLD = 0.5              # Probability threshold for speech
VAD_MIN_SPEECH_DURATION_MS = 100 # Ignore blips < 100ms
VAD_MIN_SILENCE_DURATION_MS = 300 # Merge gaps < 300ms
```

### Timestamp Remapping

When VAD strips silence, timestamps become chunk-local. They must be remapped to the global timeline:

```python
def _remap_timestamps(
    segments: list[dict],
    words: list[dict],
    speech_segments: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Remap VAD-filtered timestamps back to original timeline.
    
    Example:
        Chunk starts at 15:00 (global)
        VAD strips first 2s of silence
        Word at 3.5s (chunk-local) → 15:03.5 (global)
    """
    # Build offset map from speech_segments
    offset_map = []
    for seg in speech_segments:
        offset_map.append({
            "chunk_start": seg["start"],
            "global_start": seg["original_start"]
        })
    
    # Remap each segment/word
    for item in segments + words:
        offset = find_offset_for_time(item["start_time"], offset_map)
        item["start_time"] += offset
        item["end_time"] += offset
    
    return segments, words
```

### Overlap Deduplication

Chunks have 30-second overlaps to prevent cutting mid-sentence. After parallel transcription, overlaps must be deduplicated:

```python
def merge_transcription_results(results, recording_id):
    """Merge chunk results, handling overlap regions.
    
    Strategy:
    1. Sort chunks by index
    2. For each adjacent pair (chunk_i, chunk_{i+1}):
       - Identify overlap region (last 30s of chunk_i, first 30s of chunk_{i+1})
       - Keep segments from chunk_i (preferred, as they have more left context)
       - Drop duplicate segments from chunk_{i+1} that fall in overlap
    3. Concatenate non-overlapping segments
    """
    all_segments = []
    all_words = []
    
    for chunk_idx, (segments, words, speech_segs) in enumerate(results):
        if chunk_idx > 0:
            # Drop segments that overlap with previous chunk
            prev_end = results[chunk_idx - 1]["end_time"]
            segments = [s for s in segments if s["start"] >= prev_end - 1.0]
            words = [w for w in words if w["start"] >= prev_end - 1.0]
        
        all_segments.extend(segments)
        all_words.extend(words)
    
    # Store to DB
    _store_transcripts_sync(recording_id, all_segments, all_words)
```

### STT Provider Abstraction

**File:** `src/ai/stt.py`

```python
def transcribe_audio(audio_bytes: bytes) -> dict:
    """Transcribe audio using configured provider.
    
    Returns:
        {
            "segments": [
                {"start": 0.0, "end": 5.2, "text": "Hello welcome", "confidence": 0.95}
            ],
            "words": [
                {"start": 0.0, "end": 0.5, "word": "Hello", "confidence": 0.98},
                {"start": 0.5, "end": 1.2, "word": "welcome", "confidence": 0.92}
            ]
        }
    """
    provider = settings.stt_provider  # "nvidia_riva" | "groq_whisper"
    
    if provider == "nvidia_riva":
        return _transcribe_nvidia_riva(audio_bytes)
    elif provider == "groq_whisper":
        return _transcribe_groq_whisper(audio_bytes)
    else:
        raise ValueError(f"Unknown STT provider: {provider}")
```

**NVIDIA Riva (gRPC):**
- Model: Parakeet 1.1B (multilingual: en, hi, ar)
- Protocol: gRPC (lower latency than REST)
- Streaming: Supports real-time streaming for live audio
- Returns: Word-level timestamps + confidence scores

**Groq Whisper (fallback, currently disabled):**
- Model: Whisper Large v3
- API: REST via Groq (ultra-fast inference)
- Limitation: 25 MB file size limit (requires chunking)

### Output Tables

**transcript_segments:**
```sql
CREATE TABLE transcript_segments (
    id UUID PRIMARY KEY,
    recording_id UUID NOT NULL REFERENCES recordings(id),
    start_time FLOAT NOT NULL,          -- Seconds from start of recording
    end_time FLOAT NOT NULL,
    text TEXT NOT NULL,                 -- Full segment text
    confidence FLOAT,                   -- STT confidence (0.0-1.0)
    speaker_label VARCHAR(20),          -- Updated by diarization (initially "UNKNOWN")
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for time-range queries
CREATE INDEX idx_segments_recording_time ON transcript_segments(recording_id, start_time);
```

**word_transcripts:**
```sql
CREATE TABLE word_transcripts (
    id UUID PRIMARY KEY,
    recording_id UUID NOT NULL REFERENCES recordings(id),
    start_time FLOAT NOT NULL,          -- Precise word start time
    end_time FLOAT NOT NULL,
    word VARCHAR(255) NOT NULL,         -- Individual word
    confidence FLOAT,                   -- Word-level confidence
    speaker_label VARCHAR(20),          -- Updated by diarization
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for word-level queries
CREATE INDEX idx_words_recording_time ON word_transcripts(recording_id, start_time);
```

---

## Stage 3: Speaker Diarization

**File:** `src/workers/diarization.py`  
**Celery Task:** `dispatch_diarization` → `diarize_chunk` (parallel)  
**Status:** `DIARIZING`

### Purpose
Identify "who spoke when" by assigning speaker labels (Speaker_A, Speaker_B, etc.) to transcript segments.

### Architecture

```
dispatch_diarization
    ├─ Load manifest from storage
    ├─ If single chunk:
    │   └─ diarize_audio(recording_id)
    │       ├─ Download preprocessed audio.wav
    │       ├─ Call diarize_audio_api(audio_bytes)
    │       │   ├─ Try pyannote.audio (primary)
    │       │   └─ Fallback to NVIDIA NIM (if pyannote fails/disabled)
    │       ├─ Load transcript segments from DB
    │       ├─ assign_speaker_labels(segments, diarization_result)
    │       ├─ Update speaker_label in transcript_segments
    │       └─ Update speaker_label in word_transcripts
    │
    └─ If multiple chunks:
        └─ chord(
              [diarize_chunk.s(recording_id, chunk_idx) for chunk_idx in range(n)],
              merge_diarization_results.s(recording_id)
           )
        │
        ├─ diarize_chunk(recording_id, chunk_idx):
        │   ├─ Download chunk_{idx:03d}.wav
        │   ├─ Call diarize_audio_api(chunk_bytes)
        │   └─ Return (chunk_idx, speaker_segments)
        │
        └─ merge_diarization_results(results, recording_id):
            ├─ Collect all speaker segments from chunks
            ├─ Run cross-chunk speaker reconciliation
            │   ├─ Analyze overlap regions (30s boundaries)
            │   ├─ Match speakers across chunks via cosine similarity
            │   └─ Build global speaker mapping
            ├─ Load transcript segments from DB
            ├─ Apply global speaker mapping
            ├─ Update transcript_segments.speaker_label
            └─ Update word_transcripts.speaker_label
```

### Diarization Engine Details

**Primary: pyannote.audio 3.x**

```python
def diarize_with_pyannote(audio_bytes: bytes) -> list[dict]:
    """Diarize using pyannote.audio 3.x (segmentation-based).
    
    Model: pyannote/speaker-diarization-3.1
    Requires: Hugging Face token with model access approval
    
    Returns:
        [
            {"start": 0.0, "end": 5.2, "speaker": "SPEAKER_00"},
            {"start": 5.5, "end": 12.3, "speaker": "SPEAKER_01"},
            ...
        ]
    """
    from pyannote.audio import Pipeline
    import torchaudio
    import io
    
    # Load pipeline (cached after first load)
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=settings.hugging_face_token
    )
    
    # Load audio
    waveform, sample_rate = torchaudio.load(io.BytesIO(audio_bytes))
    
    # Run diarization
    diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})
    
    # Convert to segments
    speaker_segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_segments.append({
            "start": turn.start,
            "end": turn.end,
            "speaker": speaker
        })
    
    return speaker_segments
```

**Advantages:**
- Superior accuracy for multilingual retail (Hindi/English/Arabic code-switching)
- Better handling of overlapping speech
- Improved robustness with background noise
- Handles accent diversity across Middle East and South Asia

**Fallback: NVIDIA NIM Diarization API**

```python
def diarize_with_nvidia(audio_bytes: bytes) -> list[dict]:
    """Diarize using NVIDIA NIM API (fallback).
    
    Lower accuracy but no external dependency (no HF token needed).
    """
    from src.ai.nvidia_client import nvidia_client
    
    # Upload audio to NVIDIA API
    # Returns diarization result
    return nvidia_client.diarize(audio_bytes)
```

### Cross-Chunk Speaker Reconciliation

**Problem:** Chunks are processed independently, so:
- Chunk 0: Speaker_A = Salesperson, Speaker_B = Customer
- Chunk 1: Speaker_A = Customer, Speaker_B = Salesperson (labels swapped!)

**Solution:** Use 30-second overlap regions to match speakers across chunks.

```python
def reconcile_cross_chunk_speakers(chunk_results: list[dict]) -> dict[str, str]:
    """Build global speaker mapping from chunk-local labels.
    
    Algorithm:
    1. For each adjacent chunk pair (chunk_i, chunk_{i+1}):
       a. Extract speaker segments from overlap region
          - Last 30s of chunk_i
          - First 30s of chunk_{i+1}
       
       b. For each speaker in chunk_i:
          - Extract audio features (MFCC embeddings) from overlap
          - Compare to each speaker in chunk_{i+1}
          - Calculate cosine similarity
          - Match if similarity > 0.85
       
       c. Build mapping: {"chunk_1_SPEAKER_00": "global_SPEAKER_A", ...}
    
    2. Apply transitive closure:
       - If chunk_1_SPEAKER_00 → global_A
       - And chunk_2_SPEAKER_01 → chunk_1_SPEAKER_00
       - Then chunk_2_SPEAKER_01 → global_A
    
    3. Return global mapping for all chunks
    
    Returns:
        {
            "chunk_0_SPEAKER_00": "Speaker_A",
            "chunk_0_SPEAKER_01": "Speaker_B",
            "chunk_1_SPEAKER_00": "Speaker_B",  # Mapped correctly
            "chunk_1_SPEAKER_01": "Speaker_A",
            ...
        }
    """
    global_mapping = {}
    speaker_counter = 0
    
    for chunk_idx in range(len(chunk_results) - 1):
        current_chunk = chunk_results[chunk_idx]
        next_chunk = chunk_results[chunk_idx + 1]
        
        # Extract overlap segments
        overlap_start = current_chunk["end_ms"] - 30000
        overlap_end = overlap_start + 60000  # 30s from each chunk
        
        # Get speakers in overlap region
        current_speakers = get_speakers_in_range(
            current_chunk["segments"],
            overlap_start,
            current_chunk["end_ms"]
        )
        next_speakers = get_speakers_in_range(
            next_chunk["segments"],
            next_chunk["start_ms"],
            next_chunk["start_ms"] + 30000
        )
        
        # Match speakers via cosine similarity
        for curr_spk in current_speakers:
            best_match = None
            best_similarity = -1.0
            
            for next_spk in next_speakers:
                # Extract audio embeddings for comparison
                curr_embedding = extract_speaker_embedding(
                    current_chunk["audio"],
                    curr_spk,
                    overlap_region="end"
                )
                next_embedding = extract_speaker_embedding(
                    next_chunk["audio"],
                    next_spk,
                    overlap_region="start"
                )
                
                # Cosine similarity
                similarity = cosine_similarity(curr_embedding, next_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = next_spk
            
            # Match if similarity high enough
            if best_similarity > 0.85:
                global_spk = global_mapping.get(
                    f"chunk_{chunk_idx}_{curr_spk}",
                    f"Speaker_{chr(65 + speaker_counter)}"
                )
                global_mapping[f"chunk_{chunk_idx}_{curr_spk}"] = global_spk
                global_mapping[f"chunk_{chunk_idx + 1}_{best_match}"] = global_spk
            else:
                # No match, assign new global speaker
                new_spk = f"Speaker_{chr(65 + speaker_counter)}"
                speaker_counter += 1
                global_mapping[f"chunk_{chunk_idx + 1}_{best_match}"] = new_spk
    
    return global_mapping
```

### Speaker Label Assignment

After diarization, map speaker labels to transcript segments:

```python
def assign_speaker_labels(
    transcript_segments: list[dict],
    speaker_segments: list[dict],
) -> list[dict]:
    """Assign speaker labels to transcript segments using temporal overlap.
    
    Algorithm:
    For each transcript segment:
    1. Find all speaker segments that overlap with this segment
    2. Calculate overlap duration for each speaker
    3. Assign speaker with longest overlap (majority vote)
    
    Example:
        Transcript: [5.0s - 10.0s] "Hello welcome to our store"
        Speaker_A:  [4.5s - 8.0s]  → 3.0s overlap
        Speaker_B:  [7.5s - 12.0s] → 2.5s overlap
        
        Result: Assign Speaker_A (longer overlap)
    """
    labeled_segments = []
    
    for seg in transcript_segments:
        # Find overlapping speaker segments
        overlaps = []
        for spk_seg in speaker_segments:
            overlap_start = max(seg["start"], spk_seg["start"])
            overlap_end = min(seg["end"], spk_seg["end"])
            overlap_duration = max(0, overlap_end - overlap_start)
            
            if overlap_duration > 0:
                overlaps.append((spk_seg["speaker"], overlap_duration))
        
        # Assign speaker with longest overlap
        if overlaps:
            dominant_speaker = max(overlaps, key=lambda x: x[1])[0]
            seg["speaker"] = dominant_speaker
        else:
            seg["speaker"] = "UNKNOWN"
        
        labeled_segments.append(seg)
    
    return labeled_segments
```

### Database Updates

```python
def _update_speaker_labels_sync(recording_id: str, labeled_segments: list[dict]):
    """Write speaker labels back to transcript_segments table."""
    with _SessionLocal() as session:
        for seg in labeled_segments:
            session.query(TranscriptSegment).filter(
                TranscriptSegment.recording_id == uuid.UUID(recording_id),
                TranscriptSegment.start_time == seg["start"],
                TranscriptSegment.end_time == seg[end"],
            ).update({"speaker_label": seg["speaker"]})
        session.commit()


def _update_word_speaker_labels_sync(recording_id: str, labeled_segments: list[dict]):
    """Propagate speaker labels to word-level transcripts.
    
    For each word transcript, find the parent segment and copy speaker_label.
    """
    with _SessionLocal() as session:
        # Build time-to-speaker map from segments
        speaker_map = []
        for seg in labeled_segments:
            speaker_map.append({
                "start": seg["start"],
                "end": seg["end"],
                "speaker": seg["speaker"]
            })
        
        # Update all word transcripts
        words = session.query(WordTranscript).filter(
            WordTranscript.recording_id == uuid.UUID(recording_id)
        ).all()
        
        for word in words:
            # Find matching segment
            for seg in speaker_map:
                if seg["start"] <= word.start_time < seg["end"]:
                    word.speaker_label = seg["speaker"]
                    break
        
        session.commit()
```

---

## Stage 4: Conversation Turn Builder

**File:** `src/workers/turn_builder.py`  
**AI Module:** `src/ai/conversation_builder.py`  
**Celery Task:** `build_conversation_turns_task`  
**Status:** `BUILDING_TURNS`

### Purpose
Merge word-level transcripts into speaker turns based on continuity and gap detection.

### Algorithm

```python
# Turn boundary rules:
# 1. Speaker change → new turn
# 2. Gap > 1.0s → new turn (even if same speaker)
# 3. Same speaker + gap < 1.0s → same turn
```

### Key Operations

1. Load `word_transcripts` ordered by `start_time`
2. Group consecutive words by speaker label
3. Split on gaps > 1.0s
4. Aggregate into turns with word counts

### Output Table
```sql
conversation_turns:
  - recording_id, speaker_label, start_time, end_time, text, word_count
```

### Example
```
Words: [Hello(0.0-0.5), welcome(0.5-1.0), to(1.0-1.2), our(1.2-1.4), store(1.4-1.8)]
Turn:  {speaker: "Speaker_A", start: 0.0, end: 1.8, text: "Hello welcome to our store", word_count: 5}
```

---

## Stage 5: Speaker Role Classification

**File:** `src/workers/role_classification.py`  
**AI Module:** `src/ai/role_classifier.py`  
**Celery Task:** `classify_speaker_roles_task`  
**Status:** `CLASSIFYING_ROLES`

### Purpose
Identify which speaker is the **Salesperson** vs **Customer** using hybrid LLM + heuristic approach.

### Classification Strategy

```
┌──────────────────────────────────────┐
│         LLM Classification           │
│   (Primary — NVIDIA Llama 3.3 70B)   │
│                                      │
│   • Analyzes first 20 + last 5 turns │
│   • Multilingual Gulf retail context │
│   • JSON response with confidence    │
└──────────────────┬───────────────────┘
                   │
          Success? │
          ┌───┴───┐
         Yes      No
          │        │
          │        ▼
          │   ┌────────────────────┐
          │   │  Heuristic Fallback│
          │   │                    │
          │   │ • Retail greeting  │
          │   │   detection (+5.0) │
          │   │ • Service phrases  │
          │   │   (+3.5)           │
          │   │ • Word count bias  │
          │   │ • Customer signals │
          │   │   (negative score) │
          │   └────────────────────┘
          │
          ▼
   Final Role Assignment
```

### Heuristic Scoring System

| Signal | Score | Priority |
|--------|-------|----------|
| First retail greeting ("Welcome", "هلا", "नमस्ते") | +5.0 | Highest |
| First service phrase ("How can I help") | +3.5 | High |
| First turn speaker | +1.5 | Medium |
| Highest word count | +1.0 | Medium |
| Service phrase mentions | +1.5 each (max 4.0) | Medium |
| Price/product mentions | +2.0 / +1.5 | Medium |
| Customer signals (objections, hesitation) | -1.0 each (max -3.0) | Negative |

### Key Features

- **Arabic Diacritic Stripping:** Removes Tashkeel before regex matching
- **Context Window Sampling:** First 20 turns (greetings) + last 5 turns (avoid LLM overflow)
- **Multilingual Patterns:** Arabic, Hindi, Urdu, English code-switching
- **Greeting Split:** Retail greetings (+5.0) vs general greetings (+1.0)

### Output
- Updates `speaker_role` in database (Salesperson/Customer/Unknown)
- Stored in `conversation_turns` table

---

## Stage 6: Conversation Segmentation

**File:** `src/workers/segmentation.py`  
**AI Module:** `src/ai/segmenter.py`  
**Celery Task:** `segment_conversations`  
**Status:** `SEGMENTING`

### Purpose
Split continuous recording into discrete customer conversations using silence gaps and linguistic cues.

### Segmentation Algorithm

```python
# Conversation boundary rules:
# 1. Silence gap > 60s → definite boundary
# 2. Silence gap > 20s + farewell detected → likely boundary
# 3. Silence gap > 20s + greeting in next segment → new conversation
# 4. Gap > 20s + direct question → potential new conversation
```

### Multilingual Pattern Detection

**Greetings:** English, Arabic (MSA + Gulf), Hindi, Urdu, transliterated  
**Farewells:** "Goodbye", "مع السلامة", "अलविदा", "خدا حافظ"  
**Direct Questions:** "How much?", "بكم", "कितना", "अपने पास"

### Validation Rules
- Minimum conversation duration: **10 seconds**
- Minimum segments per conversation: **2**
- Filters out noise/empty segments

### Output Table
```sql
conversations:
  - id, recording_id, start_time, end_time, duration, metadata
```

---

## Stage 6.5: Audio Stitching

**File:** `src/workers/audio_stitcher.py`  
**Celery Task:** `stitch_conversation_audio`  
**Status:** `STITCHING_AUDIO`

### Purpose
Extract per-conversation audio files for playback in the dashboard.

### Why Stitching?

After segmentation identifies conversation boundaries, we need standalone audio files for:
- Dashboard playback of individual conversations
- Sharing specific conversations with brands/salespeople
- Avoiding on-the-fly ffmpeg cuts at API request time (latency)

### Process

```python
@celery_app.task(bind=True, name="stitch_conversation_audio")
def stitch_conversation_audio(self, recording_id: str) -> str:
    """Extract audio for each conversation and upload to storage.
    
    Pipeline:
    1. Load conversations from DB (created by segmentation)
    2. Download preprocessed audio.wav (16kHz mono, full recording)
    3. For each conversation:
       a. Calculate start/end times in milliseconds
       b. Slice audio using ffmpeg (efficient, no pydub loading)
       c. Export as WAV
       d. Upload to storage: conversations/{conv_id}/audio.wav
       e. Update conversation.audio_url in DB
    4. Return recording_id
    """
    logger.info("[%s] Starting audio stitching", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.STITCHING_AUDIO)
    
    try:
        # Load conversations from DB
        conversations = _get_conversations_sync(recording_id)
        logger.info("[%s] Stitching audio for %d conversations", recording_id, len(conversations))
        
        storage = get_storage()
        
        # Try to download preprocessed WAV first
        preprocessed_key = f"preprocessed/{recording_id}/audio.wav"
        audio_source = "preprocessed"
        
        try:
            audio_data = storage.download_sync(preprocessed_key)
            logger.info("[%s] Using preprocessed WAV for stitching", recording_id)
        except Exception:
            # Fallback: download original file
            recording = _get_recording_sync(recording_id)
            audio_source = "original"
            logger.info("[%s] Preprocessed WAV not found, using original file", recording_id)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save audio to temp file
            if audio_source == "preprocessed":
                audio_path = os.path.join(tmpdir, "full.wav")
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
            else:
                # Download original and convert
                audio_path = os.path.join(tmpdir, "full.wav")
                _download_and_convert_original(recording["file_url"], audio_path)
            
            # Extract each conversation
            for conv in conversations:
                conv_id = str(conv["id"])
                start_ms = int(conv["start_time"] * 1000)
                end_ms = int(conv["end_time"] * 1000)
                duration_ms = end_ms - start_ms
                
                logger.info(
                    "[%s] Stitching conversation %s (%.1fs - %.1fs)",
                    recording_id,
                    conv_id,
                    conv["start_time"],
                    conv["end_time"]
                )
                
                # Slice audio using ffmpeg
                output_path = os.path.join(tmpdir, f"conv_{conv_id}.wav")
                _extract_audio_segment(
                    input_path=audio_path,
                    output_path=output_path,
                    start_ms=start_ms,
                    duration_ms=duration_ms
                )
                
                # Upload to storage
                storage_key = f"conversations/{conv_id}/audio.wav"
                with open(output_path, "rb") as f:
                    storage.upload_sync(storage_key, f.read())
                
                # Update DB
                _update_conversation_audio_url_sync(conv_id, storage_key)
                logger.info("[%s] Uploaded conversation audio: %s", recording_id, storage_key)
        
        logger.info("[%s] Audio stitching complete", recording_id)
        return recording_id
        
    except Exception as exc:
        logger.error("[%s] Audio stitching failed: %s", recording_id, exc, exc_info=True)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)
```

### ffmpeg Extraction

**Why ffmpeg instead of pydub?**
- Memory efficiency: pydub loads entire WAV into RAM (~500MB for 9-hour file)
- Speed: ffmpeg can seek directly to start time without decoding full file
- Streaming: ffmpeg outputs directly to disk, no intermediate Python objects

```python
def _extract_audio_segment(
    input_path: str,
    output_path: str,
    start_ms: int,
    duration_ms: int,
):
    """Extract audio segment using ffmpeg.
    
    Command:
        ffmpeg -i input.wav -ss {start}s -t {duration}s -ar 16000 -ac 1 output.wav
    
    Parameters:
        -ss: Seek to start time (seconds)
        -t: Extract duration (seconds)
        -ar 16000: Maintain 16kHz sample rate
        -ac 1: Maintain mono channel
    """
    start_sec = start_ms / 1000.0
    duration_sec = duration_ms / 1000.0
    
    cmd = [
        "ffmpeg",
        "-y",                  # Overwrite output
        "-i", input_path,      # Input file
        "-ss", str(start_sec), # Start time
        "-t", str(duration_sec), # Duration
        "-ar", "16000",        # Sample rate
        "-ac", "1",            # Mono
        "-c:a", "pcm_s16le",   # PCM 16-bit
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    
    logger.info("Extracted %.1fs segment from %s", duration_sec, input_path)
```

### Fallback: Original File Conversion

If preprocessed WAV was cleaned up (e.g., storage optimization), fall back to original:

```python
def _download_and_convert_original(file_url: str, output_path: str):
    """Download original audio and convert to 16kHz mono WAV.
    
    Used as fallback when preprocessed WAV is unavailable.
    """
    # Download from storage
    storage = get_storage()
    parsed = urlparse(file_url)
    file_key = parsed.path.lstrip("/")
    audio_data = storage.download_sync(file_key)
    
    # Save to temp file
    input_path = output_path.replace(".wav", ".original")
    with open(input_path, "wb") as f:
        f.write(audio_data)
    
    # Convert using ffmpeg
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path
    ]
    
    subprocess.run(cmd, check=True, timeout=3600)
    
    # Cleanup original
    os.remove(input_path)
```

### Database Update

```python
def _update_conversation_audio_url_sync(conversation_id: str, audio_url: str):
    """Update conversation.audio_url in database."""
    with _SessionLocal() as session:
        session.query(Conversation).filter(
            Conversation.id == uuid.UUID(conversation_id)
        ).update({"audio_url": audio_url})
        session.commit()
```

### Storage Layout

```
storage/
└── conversations/
    ├── {conv_id_1}/
    │   └── audio.wav          # 2-minute conversation (~2MB)
    ├── {conv_id_2}/
    │   └── audio.wav          # 5-minute conversation (~5MB)
    └── {conv_id_3}/
        └── audio.wav          # 1-minute conversation (~1MB)
```

### Performance

| Conversation Length | Extraction Time | File Size |
|---------------------|----------------|-----------|
| 30 seconds | ~0.5s | ~0.5 MB |
| 2 minutes | ~1s | ~2 MB |
| 5 minutes | ~2s | ~5 MB |
| 15 minutes | ~5s | ~15 MB |

---

## Stage 7: LLM Conversation Analysis

**File:** `src/workers/analysis.py`  
**AI Module:** `src/ai/analyzer.py`  
**Celery Task:** `analyze_conversations`  
**Status:** `ANALYZING`

### Purpose
Extract structured business intelligence from each conversation using Llama 3.3 70B.

### Architecture

```python
@celery_app.task(bind=True, name="analyze_conversations")
def analyze_conversations(self, recording_id: str) -> str:
    """Analyze all conversations for a recording.
    
    Process:
    1. Load conversations from DB
    2. For each conversation:
       a. Load transcript segments within conversation time range
       b. Format transcript for LLM prompt
       c. Call LLM analysis API
       d. Parse JSON response with retry logic
       e. Store analysis to DB
    3. Return recording_id
    """
    logger.info("[%s] Starting conversation analysis", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.ANALYZING)
    
    try:
        # Load conversations
        conversations = _get_conversations_sync(recording_id)
        logger.info("[%s] Analyzing %d conversations", recording_id, len(conversations))
        
        for conv in conversations:
            conv_id = str(conv["id"])
            
            # Load transcript segments for this conversation
            segments = _get_conversation_segments_sync(conv_id)
            
            if not segments:
                logger.warning("[%s] No segments for conversation %s", recording_id, conv_id)
                continue
            
            # Call LLM analysis
            logger.info("[%s] Analyzing conversation %s (%d segments)", recording_id, conv_id, len(segments))
            analysis = analyze_conversation_ai(segments, max_retries=2)
            
            if analysis is None:
                logger.warning("[%s] Analysis failed for conversation %s", recording_id, conv_id)
                continue
            
            # Check confidence threshold
            if analysis.get("confidence", 0) < MIN_CONFIDENCE_THRESHOLD:
                logger.info(
                    "[%s] Skipping low-confidence analysis (%d%%) for conversation %s",
                    recording_id,
                    analysis["confidence"],
                    conv_id
                )
                continue
            
            # Store analysis
            _store_analysis_sync(conv_id, analysis)
            logger.info("[%s] Stored analysis for conversation %s", recording_id, conv_id)
        
        logger.info("[%s] Conversation analysis complete", recording_id)
        return recording_id
        
    except Exception as exc:
        logger.error("[%s] Analysis failed: %s", recording_id, exc, exc_info=True)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)
```

### LLM Prompt Design

**System Prompt:**
```python
SYSTEM_PROMPT = """You are an expert retail sales analyst. You analyze customer-salesperson conversations and extract structured business intelligence.

You MUST respond with valid JSON matching this exact schema:
{
    "intent": "Primary customer purchase intent or inquiry (one concise sentence)",
    "customer_expectation": "What the customer expects or wants from the product/service (e.g. durability, warranty, features, style). One concise sentence or null if not clear",
    "products": {"type": "array", "items": {"type": "string"}, "description": "Specific products discussed or requested. If none, return []"},
    "budget": "Budget range if mentioned (e.g. '$200-$500'), or null if not mentioned",
    "objections": {
        "type": "array",
        "items": {
            "category": {"type": "string", "enum": ["Price", "Features", "Timing", "Trust", "Competitor", "Other"]},
            "issue": "The specific customer concern or objection",
            "response": "How the salesperson addressed or responded to this objection"
        }
    },
    "competitors": {"type": "array", "items": {"type": "string"}, "description": "Competitor brands mentioned. If none, return []"},
    "closing_attempt": true,
    "outcome": {"type": "string", "enum": ["SALE_MADE", "LOST", "FOLLOW_UP_NEEDED"]},
    "loss_reason": "If outcome is LOST, a concise explanation of why the sale was lost based on the conversation. null if outcome is not LOST",
    "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
    "summary": "One paragraph summary of the conversation",
    "coaching_notes": "Specific coaching feedback for the salesperson based on their performance. Reference actual conversation moments and suggest SOP-compliant alternatives where applicable."
}

Rules:
- "outcome" must be exactly one of: SALE_MADE, LOST, FOLLOW_UP_NEEDED
- "confidence" is your confidence as an integer from 0 to 100
- "products" should list specific products discussed or requested
- "objections" must be an array of objects with category, issue, and response. If no objections, use empty array []
- "category" must be one of: Price, Features, Timing, Trust, Competitor, Other
- "competitors" should list competitor brands mentioned
- "closing_attempt" is true if the salesperson attempted to close the sale
- "loss_reason" should only be filled when outcome is LOST, otherwise null
- "customer_expectation" captures what the customer is looking for or expects from the purchase
- "coaching_notes" should be constructive and specific, referencing actual conversation moments and suggesting best-practice SOP responses
- If the conversation is too short or unclear, set confidence below 85
- If there are no products, competitors, or objections, you MUST return an empty array [], never null
- Respond ONLY with valid JSON, no additional text"""
```

### Transcript Formatting

**File:** `src/ai/utils.py`

```python
def format_transcript(segments: list[dict]) -> str:
    """Format conversation segments into readable transcript for LLM.
    
    Input:
        [
            {"start": 0.0, "end": 5.2, "text": "Hello welcome", "speaker": "Speaker_A"},
            {"start": 5.5, "end": 12.3, "text": "Hi I'm looking for a phone", "speaker": "Speaker_B"}
        ]
    
    Output:
        [Speaker_A] (0.0s - 5.2s): Hello welcome
        [Speaker_B] (5.5s - 12.3s): Hi I'm looking for a phone
    """
    lines = []
    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]
        
        lines.append(f"[{speaker}] ({start:.1f}s - {end:.1f}s): {text}")
    
    return "\n".join(lines)
```

### LLM API Call with Retry Logic

```python
def analyze_conversation(
    conversation_segments: list[dict[str, Any]],
    max_retries: int = 2,
) -> dict[str, Any] | None:
    """Analyze a single conversation using Llama 3.3 70B.
    
    Retry strategy:
    - Attempt 0: temperature=0.1 (deterministic)
    - Attempt 1: temperature=0.3 (more creative, escape local minima)
    - Attempt 2: temperature=0.5 (even more creative)
    """
    if not conversation_segments:
        logger.warning("Empty conversation segments — skipping analysis")
        return None
    
    # Format conversation for the prompt
    transcript_text = format_transcript(conversation_segments)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze this retail conversation:\n\n{transcript_text}"},
    ]
    
    for attempt in range(max_retries + 1):
        try:
            # Slightly increase temperature on retries to escape local minima
            temp = 0.1 if attempt == 0 else 0.3
            
            response_text = nvidia_client.chat_completion(
                messages=messages,  # Use original prompt for stateless retries
                temperature=temp,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            
            analysis = _parse_analysis_response(response_text)
            if analysis is None:
                logger.warning("Failed to parse analysis response (attempt %d)", attempt + 1)
                continue
            
            return analysis
            
        except NVIDIAAPIError as e:
            logger.error("NVIDIA API error during analysis (attempt %d): %s", attempt + 1, e)
            if attempt == max_retries:
                return None
            continue
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to parse LLM response (attempt %d): %s", attempt + 1, e)
            if attempt == max_retries:
                return None
            continue
    
    return None
```

### Robust JSON Parsing

**Critical:** LLMs sometimes return JSON wrapped in markdown code blocks or with extra text.

```python
def _parse_analysis_response(response_text: str) -> dict[str, Any] | None:
    """Parse and validate LLM analysis response.
    
    Handles:
    - Direct JSON: {"intent": ...}
    - Markdown fenced: ```json\n{...}\n```
    - Extra text: "Here's the analysis:\n{...}"
    """
    try:
        # Clean up response: strip markdown code blocks if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            # Remove markdown code fence
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]  # Remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove closing fence
            cleaned = "\n".join(lines)
        
        # Find JSON object (handle cases where LLM adds extra text)
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}") + 1
        if start_idx == -1 or end_idx == 0:
            logger.warning("No JSON object found in response (first 200 chars): %s", response_text[:200])
            return None
        
        json_str = cleaned[start_idx:end_idx]
        data = json.loads(json_str)
        
        # Validate required fields
        required_fields = ["intent", "outcome", "confidence", "summary"]
        for field in required_fields:
            if field not in data:
                logger.warning("Missing required field in analysis: %s", field)
                return None
        
        # Validate outcome enum
        if data["outcome"] not in ["SALE_MADE", "LOST", "FOLLOW_UP_NEEDED"]:
            logger.warning("Invalid outcome: %s", data["outcome"])
            return None
        
        # Validate confidence range
        if not (0 <= data["confidence"] <= 100):
            logger.warning("Confidence out of range: %d", data["confidence"])
            return None
        
        return data
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Failed to parse analysis response: %s", e)
        return None
```

### NVIDIA Client Implementation

**File:** `src/ai/nvidia_client.py`

```python
class NVIDIAClient:
    """Client for NVIDIA NIM API (Llama 3.3 70B)."""
    
    def __init__(self):
        self.api_key = settings.nvidia_api_key
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model = "meta/llama-3.3-70b-instruct"
    
    def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> str:
        """Call NVIDIA NIM chat completion API.
        
        Args:
            messages: List of {role, content} dicts
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            response_format: {"type": "json_object"} for JSON mode
        
        Returns:
            Response text string
        """
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120.0,  # 2-minute timeout
        )
        
        if response.status_code != 200:
            raise NVIDIAAPIError(f"NVIDIA API error {response.status_code}: {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


nvidia_client = NVIDIAClient()
```

### Analysis Schema (Output)

```json
{
  "intent": "Customer looking for a durable smartphone under $500 with good camera",
  "customer_expectation": "Long battery life, water resistance, warranty coverage",
  "products": ["Samsung Galaxy A54", "iPhone 14"],
  "budget": "$400-$500",
  "objections": [
    {
      "category": "Price",
      "issue": "Customer thinks Samsung is too expensive",
      "response": "Salesperson offered 10% discount and installment plan"
    },
    {
      "category": "Features",
      "issue": "Customer unsure about camera quality",
      "response": "Salesperson showed sample photos and demo unit"
    }
  ],
  "competitors": ["OnePlus", "Xiaomi"],
  "closing_attempt": true,
  "outcome": "SALE_MADE",
  "loss_reason": null,
  "confidence": 92,
  "summary": "Customer visited store looking for a mid-range smartphone. Salesperson presented Samsung Galaxy A54 and iPhone 14 options. After addressing price concerns with discount offer and demonstrating camera capabilities, customer purchased Samsung with 12-month installment plan.",
  "coaching_notes": "Excellent product knowledge demonstration. Consider asking more discovery questions about customer's current phone pain points earlier in the conversation. Strong closing technique with installment plan offer."
}
```

### Database Schema

```sql
CREATE TABLE conversation_analyses (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    
    -- Core analysis fields
    intent TEXT,
    customer_expectation TEXT,
    products JSONB,                     -- Array of product names
    budget VARCHAR(255),
    objections JSONB,                   -- Array of {category, issue, response}
    competitors JSONB,                  -- Array of competitor names
    closing_attempt BOOLEAN,
    outcome VARCHAR(50),                -- SALE_MADE, LOST, FOLLOW_UP_NEEDED
    loss_reason TEXT,
    confidence INTEGER,                 -- 0-100
    summary TEXT,
    coaching_notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for filtering by outcome
CREATE INDEX idx_analyses_outcome ON conversation_analyses(outcome);

-- Index for confidence filtering
CREATE INDEX idx_analyses_confidence ON conversation_analyses(confidence);
```

---

## Stage 8: Performance Scoring

**File:** `src/workers/scoring.py`  
**AI Module:** `src/ai/scorer.py`  
**Celery Task:** `score_salesperson`  
**Status:** `SCORING`

### Purpose
Score salesperson performance across 5 dimensions for coaching insights.

### Scoring Dimensions

| Dimension | Criteria | Score Range |
|-----------|----------|-------------|
| **Greeting** | Warmth, professionalism, speed | 0-100 |
| **Discovery** | Quality of needs-finding questions | 0-100 |
| **Product Knowledge** | Accuracy and depth of product info | 0-100 |
| **Objection Handling** | Effectiveness at resolving concerns | 0-100 |
| **Closing** | Number and quality of closing attempts | 0-100 |

### Scoring Rubric Example (Greeting)

- **90-100:** Warm, professional, immediate acknowledgment
- **70-89:** Friendly but could be more personalized
- **50-69:** Basic greeting, lacks warmth
- **0-49:** No greeting or rude/abrupt start

### Output Tables
```sql
salesperson_scores:
  - salesperson_id, conversation_id, greeting_score,
    discovery_score, product_knowledge_score,
    objection_handling_score, closing_score

daily_metrics:
  - date, store_id, salesperson_id, avg_score,
    total_conversations, total_sales, conversion_rate
```

---

## Pipeline Orchestration

**File:** `src/workers/pipeline.py`

### Celery Chain

```python
processing_chain = chain(
    preprocess_audio.s(recording_id),              # Stage 1
    dispatch_transcription.s(),                     # Stage 2 (parallel chord)
    dispatch_diarization.s(),                       # Stage 3 (parallel chord)
    build_conversation_turns_task.s(),             # Stage 4
    classify_speaker_roles_task.s(),               # Stage 5
    segment_conversations.s(),                     # Stage 6
    stitch_conversation_audio.s(),                 # Stage 6.5
    analyze_conversations.s(),                     # Stage 7
    score_salesperson.s(),                         # Stage 8
)
return processing_chain.apply_async()
```

### Parallel Processing

**Transcription & Diarization** use Celery chords for parallel chunk processing:

```python
# dispatch_transcription example
chunks = load_manifest(recording_id)["chunks"]
if len(chunks) > 1:
    chord_result = chord(
        [transcribe_chunk.s(recording_id, i) for i in range(len(chunks))],
        merge_transcription_results.s(recording_id)
    )
    return self.replace(chord_result)
else:
    return transcribe_audio_task.delay(recording_id)
```

### Status Transitions

```
UPLOADED → PREPROCESSING → TRANSCRIBING → DIARIZING → 
BUILDING_TURNS → CLASSIFYING_ROLES → SEGMENTING → 
STITCHING_AUDIO → ANALYZING → SCORING → COMPLETED
                                          ↓
                                       FAILED (on error)
```

---

## AI Module Architecture

### `src/ai/` Directory Structure

```
src/ai/
├── analyzer.py           # LLM conversation analysis (Llama 3.3 70B)
├── conversation_builder.py  # Turn merging algorithm
├── diarizer.py           # pyannote.audio + NVIDIA fallback
├── nvidia_client.py      # NVIDIA NIM API client
├── role_classifier.py    # Hybrid LLM + heuristic role classification
├── scorer.py             # 5-dimension performance scoring
├── segmenter.py          # Conversation boundary detection
├── stt.py                # STT provider abstraction
├── vad.py                # Silero VAD silence filtering
└── utils.py              # Transcript formatting utilities
```

### NVIDIA Client

**File:** `src/ai/nvidia_client.py`

Centralized client for NVIDIA NIM API with:
- Chat completion (Llama 3.3 70B)
- STT (Riva Parakeet via gRPC)
- Diarization (fallback)
- Error handling + retry logic

### Utility Functions

**`format_transcript(segments)`**  
Formats conversation segments into readable transcript for LLM prompts:

```
[Speaker_A] (0.0s - 5.2s): Hello, welcome to our store!
[Speaker_B] (5.5s - 12.3s): Hi, I'm looking for a phone.
```

---

## Database Schema Overview

### Core Tables

```sql
recordings:
  - id, brand_id, store_id, file_url, format, duration_ms, status

transcript_segments:
  - id, recording_id, start_time, end_time, text, confidence, speaker_label

word_transcripts:
  - id, recording_id, start_time, end_time, word, confidence, speaker_label

conversation_turns:
  - id, recording_id, speaker_label, start_time, end_time, text, word_count, speaker_role

conversations:
  - id, recording_id, start_time, end_time, duration, audio_url

conversation_analyses:
  - id, conversation_id, intent, products, budget, objections, 
    competitors, closing_attempt, outcome, confidence, summary, coaching_notes

salesperson_scores:
  - id, salesperson_id, conversation_id, greeting_score, discovery_score,
    product_knowledge_score, objection_handling_score, closing_score
```

---

## Storage Layout

```
storage/
├── recordings/{recording_id}/
│   └── original_audio.mp3
│
├── preprocessed/{recording_id}/
│   ├── audio.wav                    # Full 16kHz mono WAV
│   ├── manifest.json                # Chunk boundaries
│   └── chunk_000.wav, chunk_001.wav  # Individual chunks
│
└── conversations/{conversation_id}/
    └── audio.wav                    # Per-conversation audio
```

---

## Error Handling & Retry Logic

### Celery Task Configuration

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def task_name(self, recording_id: str):
    try:
        # Task logic
        pass
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            fail_and_halt(recording_id, "Error message")
            raise Ignore()
        raise self.retry(exc=exc)
```

### Pipeline Halt on Critical Failure

If a task fails after max retries:
1. Recording status set to `FAILED`
2. Error message logged
3. Pipeline chain stops (no further tasks execute)
4. `Ignore()` exception prevents retry loop

### LLM-Specific Error Handling

- **Empty Response:** Retry with increased temperature
- **JSON Parse Error:** Retry up to 2 times
- **API Error:** Fall back to heuristic (role classifier) or skip (analyzer/scorer)

---

## Configuration

**File:** `src/config.py`

### Key Settings

```python
# Audio Processing
TARGET_SAMPLE_RATE = 16000
SILENCE_THRESHOLD_DB = -40
SILENCE_GAP_MS = 30000
AUDIO_CHUNK_DURATION_MINUTES = 15
AUDIO_CHUNK_OVERLAY_SECONDS = 30

# VAD
VAD_USE_SILERO = True
VAD_FILTER_BEFORE_STT = True

# LLM
NVIDIA_API_KEY = "nvapi-..."
LLM_CONFIDENCE_THRESHOLD = 0.7
MIN_CONFIDENCE_THRESHOLD = 50

# Diarization
PYANNOTE_ENABLED = True
HUGGING_FACE_TOKEN = "hf_..."
```

---

## Performance Characteristics

### Memory Usage

| Stage | Peak RAM | Notes |
|-------|----------|-------|
| Preprocessing | ~50 MB | ffmpeg streaming, no RAM spike |
| STT (per chunk) | ~200 MB | AudioSegment in memory |
| Diarization (per chunk) | ~1.5 GB | pyannote.audio model |
| Turn Builder | ~100 MB | DB query results |
| Role Classification | ~50 MB | LLM API call |
| Segmentation | ~50 MB | In-memory processing |
| Audio Stitching | ~500 MB | pydub AudioSegment |
| LLM Analysis | ~50 MB | API call per conversation |
| Scoring | ~50 MB | API call per conversation |

### Processing Time Estimates

| Recording Length | Preprocessing | STT (parallel) | Diarization | Total Pipeline |
|------------------|---------------|----------------|-------------|----------------|
| 5 minutes | ~30s | ~15s | ~45s | ~3-5 min |
| 1 hour | ~2 min | ~5 min (4 chunks) | ~8 min | ~15-20 min |
| 9 hours | ~10 min | ~45 min (36 chunks) | ~60 min | ~2-3 hours |

---

## Monitoring & Observability

### Celery Flower

Real-time task monitoring at `http://localhost:5555`:
- Task status (PENDING, STARTED, SUCCESS, FAILED)
- Execution time per task
- Worker utilization

### Logging

Each task logs with recording ID prefix:
```
[recording_id] Starting audio preprocessing
[recording_id] Manifest: 12 chunks from 8 silence gaps
[recording_id] Transcription successful: 245 segments
```

### Status Tracking

Recording status updates at each stage, queryable via API:
```python
GET /api/v1/recordings/{id}
→ { "status": "ANALYZING", "progress": 78 }
```

---

## Future Enhancements

1. **Real-time Streaming:** Process audio as it's recorded (WebSocket)
2. **Voiceprint Enrollment:** Persistent speaker identification across recordings
3. **Cross-Conversation Tracking:** Link customers across multiple visits
4. **Sentiment Analysis:** Emotional tone tracking per conversation
5. **Custom LLM Fine-tuning:** Domain-specific model for retail sales
6. **GPU Acceleration:** pyannote.audio on GPU for 5x speedup
7. **Batch Processing:** Process multiple recordings in parallel

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **ffmpeg over pydub** | Memory efficiency for 9+ hour recordings |
| **Celery chords** | Parallel chunk processing for STT/diarization |
| **pyannote.audio primary** | Superior multilingual accuracy |
| **LLM + heuristic hybrid** | Reliability when LLM unavailable |
| **Context window sampling** | Prevent LLM overflow on long conversations |
| **Arabic diacritic stripping** | Regex robustness with ASR output |
| **Word count over turn count** | Better salesperson signal (customers take more short turns) |

---

## File Dependencies

```
pipeline.py
├── preprocessing.py
│   └── config.py, storage/local.py, models/recording.py
├── transcription.py
│   ├── ai/stt.py, ai/nvidia_client.py
│   └── ai/vad.py (optional)
├── diarization.py
│   └── ai/diarizer.py (pyannote + NVIDIA fallback)
├── turn_builder.py
│   └── ai/conversation_builder.py
├── role_classification.py
│   └── ai/role_classifier.py (LLM + heuristic)
├── segmentation.py
│   └── ai/segmenter.py (silence + greeting detection)
├── audio_stitcher.py
│   └── pydub, ffmpeg
├── analysis.py
│   └── ai/analyzer.py (Llama 3.3 70B)
└── scoring.py
    └── ai/scorer.py (5-dimension scoring)
```

---

*Last updated: June 14, 2026*
