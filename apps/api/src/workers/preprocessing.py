"""Audio preprocessing worker — converts raw audio to standardized format."""
import json
import logging
import os
import subprocess
import tempfile
import uuid

from pydub import AudioSegment
from pydub.silence import detect_silence

from src.config import settings
from src.models.recording import Recording, RecordingStatus
from src.storage.local import get_storage
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Module-level engine — reused across task invocations in the same worker process.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine)

# Preprocessing constants
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
SILENCE_THRESHOLD_DB = -40
SILENCE_GAP_MS = 30000  # 30 seconds in milliseconds
TARGET_FORMAT = "wav"


# ---------------------------------------------------------------------------
# Sync DB helpers (Celery workers run in sync context)
# ---------------------------------------------------------------------------

def _update_recording_status_sync(recording_id: str, status: RecordingStatus, error: str | None = None):
    """Update recording status using sync DB session."""
    with _SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording:
            recording.status = status
            if error:
                recording.error_message = error
        session.commit()


def _get_recording_sync(recording_id: str) -> dict | None:
    """Get recording data using sync DB session."""
    with _SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if not recording:
            return None
        return {
            "id": str(recording.id),
            "file_url": recording.file_url,
            "format": recording.format,
        }


def _update_recording_duration_sync(recording_id: str, duration_seconds: int):
    """Update recording duration using sync DB session."""
    with _SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording:
            recording.duration_seconds = duration_seconds
        session.commit()


def _store_silence_gaps_sync(recording_id: str, silence_gaps: list[tuple[float, float]]):
    """Store silence gaps in recording.silence_gaps JSONB field."""
    with _SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording:
            # Convert to list of dicts for JSONB storage
            recording.silence_gaps = [{"start": s / 1000.0, "end": e / 1000.0} for s, e in silence_gaps]
        session.commit()


def _store_chunk_manifest_sync(recording_id: str, manifest: dict):
    """Store chunk manifest in recording.chunk_manifest JSONB field."""
    with _SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording:
            recording.chunk_manifest = manifest
        session.commit()


# ---------------------------------------------------------------------------
# Storage helpers (sync)
# ---------------------------------------------------------------------------

def _download_audio_sync(storage, file_url: str) -> bytes:
    """Download audio from storage using sync method."""
    return storage.download_sync(file_url)


def _upload_audio_sync(storage, data: bytes, key: str) -> str:
    """Upload audio to storage using sync method."""
    return storage.upload_sync(data, key)


# ---------------------------------------------------------------------------
# Chunk manifest helpers
# ---------------------------------------------------------------------------

def _detect_silence_gaps(audio: AudioSegment) -> list[tuple[float, float]]:
    """Detect silence gaps in audio using pydub.

    Returns list of (start_ms, end_ms) tuples for gaps >= SILENCE_GAP_MS.
    """
    min_silence_len = SILENCE_GAP_MS  # 30s minimum to count as a gap
    silence_ranges = detect_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=SILENCE_THRESHOLD_DB,
    )
    logger.info("Detected %d silence gaps (>= %ds)", len(silence_ranges), SILENCE_GAP_MS // 1000)
    return silence_ranges


def _build_chunk_manifest(
    duration_ms: int,
    silence_gaps_ms: list[tuple[float, float]],
    recording_id: str,
) -> dict:
    """Build a chunk manifest using silence-gap-aware splitting.

    Strategy:
    1. Use silence gaps >= 30s as preferred split points.
    2. If a speech region between two silence gaps exceeds max_chunk_duration,
       fall back to fixed-window splitting within that region.
    3. Apply overlap at each boundary for transcription continuity.

    Returns manifest dict with chunk list and metadata.
    """
    chunk_duration_ms = settings.audio_chunk_duration_minutes * 60 * 1000
    overlap_ms = settings.audio_chunk_overlap_seconds * 1000

    needs_chunking = duration_ms > chunk_duration_ms

    if not needs_chunking:
        return {
            "recording_id": recording_id,
            "duration_ms": duration_ms,
            "needs_chunking": False,
            "chunks": [
                {"index": 0, "start_ms": 0, "end_ms": duration_ms, "file": "chunk_000.wav"},
            ],
        }

    # Use silence gap midpoints as preferred split points
    split_points = []
    for gap_start, gap_end in silence_gaps_ms:
        midpoint = (gap_start + gap_end) / 2.0
        split_points.append(midpoint)

    # Sort and deduplicate
    split_points = sorted(set(split_points))

    # Build raw chunk boundaries from split points, adding fixed-window
    # fallback for regions that exceed max chunk duration
    raw_boundaries = [0]  # start of first chunk
    last_point = 0.0

    for sp in split_points:
        if sp - last_point >= chunk_duration_ms * 0.5:  # at least half a chunk
            raw_boundaries.append(sp)
            last_point = sp
        elif sp - last_point >= 60000:  # at least 1 minute
            raw_boundaries.append(sp)
            last_point = sp

    # Always include the end
    if raw_boundaries[-1] < duration_ms:
        raw_boundaries.append(duration_ms)

    # Sub-split any segment that still exceeds max chunk duration
    final_boundaries = []
    for i in range(len(raw_boundaries) - 1):
        seg_start = raw_boundaries[i]
        seg_end = raw_boundaries[i + 1]
        final_boundaries.append(seg_start)

        if seg_end - seg_start > chunk_duration_ms:
            # Fixed-window sub-split within this region
            sub_pos = seg_start + chunk_duration_ms
            while sub_pos < seg_end:
                final_boundaries.append(sub_pos)
                sub_pos += chunk_duration_ms

    final_boundaries.append(duration_ms)

    # Build chunk list with overlap
    chunks = []
    for i in range(len(final_boundaries) - 1):
        chunk_start = max(0, final_boundaries[i] - (overlap_ms if i > 0 else 0))
        chunk_end = min(
            final_boundaries[i + 1] + (overlap_ms if i < len(final_boundaries) - 2 else 0),
            duration_ms,
        )
        chunks.append({
            "index": i,
            "start_ms": int(final_boundaries[i]),
            "end_ms": int(final_boundaries[i + 1]),
            "audio_start_ms": int(chunk_start),  # actual audio extraction start (with overlap)
            "audio_end_ms": int(chunk_end),       # actual audio extraction end (with overlap)
            "file": f"chunk_{i:03d}.wav",
        })

    logger.info(
        "[%s] Chunk manifest: %d chunks from %d silence gaps (duration=%ds)",
        recording_id, len(chunks), len(silence_gaps_ms), duration_ms // 1000,
    )

    return {
        "recording_id": recording_id,
        "duration_ms": duration_ms,
        "needs_chunking": True,
        "chunks": chunks,
    }


def _split_and_upload_chunks(
    audio: AudioSegment,
    manifest: dict,
    recording_id: str,
    storage,
    tmpdir: str,
):
    """Split audio according to manifest and upload each chunk to storage."""
    chunk_dir = os.path.join(tmpdir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)

    for chunk_info in manifest["chunks"]:
        # Extract chunk using audio_start_ms/audio_end_ms (includes overlap)
        audio_start = chunk_info.get("audio_start_ms", chunk_info["start_ms"])
        audio_end = chunk_info.get("audio_end_ms", chunk_info["end_ms"])
        chunk_audio = audio[audio_start:audio_end]

        chunk_path = os.path.join(chunk_dir, chunk_info["file"])
        chunk_audio.export(
            chunk_path, format=TARGET_FORMAT,
            parameters=["-ar", str(TARGET_SAMPLE_RATE)],
        )

        with open(chunk_path, "rb") as f:
            chunk_data = f.read()

        chunk_key = f"preprocessed/{recording_id}/chunks/{chunk_info['file']}"
        _upload_audio_sync(storage, chunk_data, chunk_key)

        logger.info(
            "[%s] Uploaded chunk %d: %s (%d bytes, %.0fs-%.0fs)",
            recording_id, chunk_info["index"], chunk_info["file"],
            len(chunk_data), audio_start / 1000, audio_end / 1000,
        )

    # Also upload manifest.json to storage for dispatcher tasks
    manifest_key = f"preprocessed/{recording_id}/manifest.json"
    _upload_audio_sync(storage, json.dumps(manifest).encode(), manifest_key)

    logger.info(
        "[%s] Uploaded %d chunk files + manifest to storage",
        recording_id, len(manifest["chunks"]),
    )


def load_manifest(recording_id: str) -> dict:
    """Load chunk manifest from storage.

    Used by dispatcher tasks (dispatch_transcription, dispatch_diarization)
    to determine chunk boundaries at runtime.
    """
    storage = get_storage()
    manifest_key = f"preprocessed/{recording_id}/manifest.json"
    manifest_data = storage.download_sync(manifest_key)
    return json.loads(manifest_data)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="preprocess_audio")
def preprocess_audio(self, recording_id: str) -> str:
    """Preprocess raw audio: convert to mono, normalize, resample to 16kHz.

    Returns the recording_id for the next pipeline stage.
    """
    logger.info("[%s] Starting audio preprocessing", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.PREPROCESSING)

    try:
        # Get recording info
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()

        # Download original audio
        file_url = recording["file_url"]
        logger.info("[%s] Downloading audio from %s", recording_id, file_url)
        audio_data = _download_audio_sync(storage, file_url)

        # Process audio in a temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Preserve original extension so ffmpeg can detect format
            ext = os.path.splitext(file_url)[1] or ".mp3"
            input_path = os.path.join(tmpdir, f"input{ext}")
            output_path = os.path.join(tmpdir, "preprocessed.wav")

            # Write downloaded audio to temp file
            with open(input_path, "wb") as f:
                f.write(audio_data)

            # Convert to WAV via ffmpeg subprocess (avoids pydub subprocess hang in Celery)
            logger.info("[%s] Converting audio to WAV via ffmpeg", recording_id)
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, "-ac", "1", "-ar", str(TARGET_SAMPLE_RATE), "-f", "wav", output_path],
                capture_output=True,
                timeout=600,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")

            # Load preprocessed WAV
            logger.info("[%s] Loading preprocessed WAV", recording_id)
            audio = AudioSegment.from_wav(output_path)

            # Convert to mono
            logger.info("[%s] Converting to mono (channels: %d)", recording_id, audio.channels)
            if audio.channels > 1:
                audio = audio.set_channels(TARGET_CHANNELS)

            # Resample to 16kHz
            if audio.frame_rate != TARGET_SAMPLE_RATE:
                logger.info("[%s] Resampling %dHz → %dHz", recording_id, audio.frame_rate, TARGET_SAMPLE_RATE)
                audio = audio.set_frame_rate(TARGET_SAMPLE_RATE)

            # Normalize volume (target -20 dBFS)
            logger.info("[%s] Normalizing volume (current: %.1f dBFS)", recording_id, audio.dBFS)
            change_in_dbfs = -20.0 - audio.dBFS
            audio = audio.apply_gain(change_in_dbfs)

            # Update duration
            duration_seconds = len(audio) // 1000
            duration_ms = len(audio)
            _update_recording_duration_sync(recording_id, duration_seconds)

            # Detect silence gaps for chunk boundary optimization
            logger.info("[%s] Detecting silence gaps", recording_id)
            silence_gaps = _detect_silence_gaps(audio)
            _store_silence_gaps_sync(recording_id, silence_gaps)

            # Build chunk manifest (silence-gap-aware)
            manifest = _build_chunk_manifest(duration_ms, silence_gaps, recording_id)

            # Split audio into chunks and upload each to storage
            logger.info(
                "[%s] Splitting audio into %d chunks (needs_chunking=%s)",
                recording_id, len(manifest["chunks"]), manifest["needs_chunking"],
            )
            _split_and_upload_chunks(audio, manifest, recording_id, storage, tmpdir)

            # Store manifest in DB
            _store_chunk_manifest_sync(recording_id, manifest)

            logger.info(
                "[%s] Preprocessing complete. Duration: %ds, Chunks: %d",
                recording_id,
                duration_seconds,
                len(manifest["chunks"]),
            )

        return recording_id

    except Exception as exc:
        logger.error("[%s] Preprocessing failed: %s", recording_id, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise
