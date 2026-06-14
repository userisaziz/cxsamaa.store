"""Audio preprocessing worker — converts raw audio to standardized format.

Memory-efficient pipeline for long recordings (tested up to 9+ hours):
- All audio manipulation delegated to ffmpeg subprocesses (never loads WAV into Python RAM)
- Silence detection via ffmpeg silencedetect filter (streaming, O(1) memory)
- Chunk splitting via ffmpeg seek+cut (disk-based, no pydub slicing)
- Network I/O streamed to disk (no full-file-in-RAM spikes)
- pydub removed entirely from hot path
- Peak RAM: ~50 MB regardless of recording length
"""
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from urllib.parse import urlparse

from src.config import settings
from src.models.recording import Recording, RecordingStatus
from src.storage.local import get_storage
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level DB engine — reused across task invocations in the same worker
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine)

# ---------------------------------------------------------------------------
# Preprocessing constants
# ---------------------------------------------------------------------------
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
SILENCE_THRESHOLD_DB = -40
SILENCE_GAP_MS = 30000          # 30 s minimum gap to count as silence
TARGET_FORMAT = "wav"

# loudnorm target levels (EBU R128)
LOUDNORM_I = -20                # integrated loudness (LUFS)
LOUDNORM_TP = -1.5              # true peak (dBTP)
LOUDNORM_LRA = 11               # loudness range (LU)

# ffmpeg subprocess timeouts (seconds)
TIMEOUT_CONVERT = 7200          # 2 hr — covers 9-hr file + loudnorm at slow CPU
TIMEOUT_SILENCE = 1800          # 30 min — silence scan for 9-hr file
TIMEOUT_CHUNK = 300             # 5 min per chunk cut


# ---------------------------------------------------------------------------
# Sync DB helpers (Celery workers run in sync context)
# ---------------------------------------------------------------------------

def _get_recording_id_uuid(recording_id: str) -> uuid.UUID:
    """Safely convert recording_id to UUID (handles str or already-UUID)."""
    if isinstance(recording_id, uuid.UUID):
        return recording_id
    return uuid.UUID(str(recording_id))


def _update_recording_status_sync(
    recording_id: str,
    status: RecordingStatus,
    error: str | None = None,
) -> None:
    rec_uuid = _get_recording_id_uuid(recording_id)
    with _SessionLocal() as session:
        rec = session.query(Recording).filter(Recording.id == rec_uuid).first()
        if rec:
            rec.status = status
            if error:
                rec.error_message = error
        session.commit()


def _get_recording_sync(recording_id: str) -> dict | None:
    rec_uuid = _get_recording_id_uuid(recording_id)
    with _SessionLocal() as session:
        rec = session.query(Recording).filter(Recording.id == rec_uuid).first()
        if not rec:
            return None
        return {
            "id": str(rec.id),
            "file_url": rec.file_url,
            "format": rec.format,
        }


def _update_recording_duration_sync(recording_id: str, duration_seconds: int) -> None:
    rec_uuid = _get_recording_id_uuid(recording_id)
    with _SessionLocal() as session:
        rec = session.query(Recording).filter(Recording.id == rec_uuid).first()
        if rec:
            rec.duration_seconds = duration_seconds
        session.commit()


def _store_silence_gaps_sync(
    recording_id: str,
    silence_gaps: list[tuple[float, float]],
) -> None:
    """Store silence gaps as JSONB [{start, end}] in seconds."""
    rec_uuid = _get_recording_id_uuid(recording_id)
    with _SessionLocal() as session:
        rec = session.query(Recording).filter(Recording.id == rec_uuid).first()
        if rec:
            rec.silence_gaps = [
                {"start": s / 1000.0, "end": e / 1000.0}
                for s, e in silence_gaps
            ]
        session.commit()


def _store_chunk_manifest_sync(recording_id: str, manifest: dict) -> None:
    rec_uuid = _get_recording_id_uuid(recording_id)
    with _SessionLocal() as session:
        rec = session.query(Recording).filter(Recording.id == rec_uuid).first()
        if rec:
            rec.chunk_manifest = manifest
        session.commit()


# ---------------------------------------------------------------------------
# Storage helpers (sync)
# ---------------------------------------------------------------------------

def _download_audio_sync_streaming(file_url: str, dest_path: str) -> None:
    """Stream download directly to disk — avoids loading entire file into RAM.

    Works for both local file:// URLs and HTTP(S) pre-signed URLs.
    For local paths the storage backend already handles this via read_bytes,
    but for remote URLs this uses streaming to keep RAM at ~0 MB overhead.
    """
    parsed = urlparse(file_url)

    # Local file path — copy directly
    if parsed.scheme in ("", "file"):
        src = parsed.path if parsed.path else file_url
        with open(src, "rb") as src_f, open(dest_path, "wb") as dst_f:
            shutil.copyfileobj(src_f, dst_f, length=8 * 1024 * 1024)  # 8 MB chunks
        return

    # HTTP(S) — stream via requests
    import requests
    with requests.get(file_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)


def _upload_audio_from_file_sync(storage, file_path: str, key: str) -> str:
    """Upload a file from disk path — avoids loading entire chunk into RAM.

    Uses boto3's upload_file for R2 (multipart streaming from disk).
    Falls back to LocalStorage's write-bytes path.
    """
    # R2/boto3: use upload_file which streams from disk via multipart upload
    if hasattr(storage, "client") and hasattr(storage.client, "upload_file"):
        storage.client.upload_file(file_path, storage.bucket, key)
        logger.debug("Uploaded %s to R2: %s", file_path, key)
        return key

    # LocalStorage fallback: read in 8 MB blocks and write directly
    if hasattr(storage, "base_dir"):
        dest = storage.base_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "rb") as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)
        logger.debug("Copied %s → %s", file_path, dest)
        return key

    # Ultimate fallback: read full file (should not happen in production)
    with open(file_path, "rb") as f:
        data = f.read()
    return storage.upload_sync(data, key)


# ---------------------------------------------------------------------------
# ffmpeg helpers — all audio work stays out of Python RAM
# ---------------------------------------------------------------------------

def _run_ffmpeg(args: list[str], timeout: int, label: str) -> subprocess.CompletedProcess:
    """Run an ffmpeg command, raising RuntimeError on non-zero exit."""
    result = subprocess.run(
        args,
        capture_output=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg {label} failed (exit {result.returncode}):\n"
            f"{result.stderr.decode(errors='replace')}"
        )
    return result


def _convert_and_normalize(input_path: str, output_path: str) -> None:
    """Convert any audio format → 16kHz mono WAV with loudnorm in one ffmpeg pass.

    Uses a two-pass loudnorm approach for accurate normalization on long files:
    Pass 1 — measure integrated loudness / true peak / LRA.
    Pass 2 — apply correction with measured values.

    Falls back to single-pass if the two-pass parse fails (should never happen
    with a valid audio file, but guards against corrupt/short recordings).
    """
    logger.info("Converting + normalizing (two-pass loudnorm): %s → %s", input_path, output_path)

    # --- Pass 1: measure (with format conversion to match Pass 2 exactly) ---
    p1 = subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-ac", str(TARGET_CHANNELS),
            "-ar", str(TARGET_SAMPLE_RATE),
            "-af", f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}:print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True,
        timeout=TIMEOUT_CONVERT,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    # loudnorm JSON appears in stderr
    loudnorm_json = _parse_loudnorm_json(p1.stderr.decode(errors="replace"))

    if loudnorm_json:
        # --- Pass 2: apply measured values ---
        af = (
            f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}"
            f":measured_I={loudnorm_json['input_i']}"
            f":measured_TP={loudnorm_json['input_tp']}"
            f":measured_LRA={loudnorm_json['input_lra']}"
            f":measured_thresh={loudnorm_json['input_thresh']}"
            f":offset={loudnorm_json['target_offset']}"
            f":linear=true:print_format=none"
        )
        _run_ffmpeg(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-ac", str(TARGET_CHANNELS),
                "-ar", str(TARGET_SAMPLE_RATE),
                "-af", af,
                "-f", TARGET_FORMAT, output_path,
            ],
            timeout=TIMEOUT_CONVERT,
            label="pass-2 loudnorm",
        )
    else:
        # Fallback: single-pass (less accurate but safe)
        logger.warning("loudnorm pass-1 parse failed — using single-pass fallback")
        _run_ffmpeg(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-ac", str(TARGET_CHANNELS),
                "-ar", str(TARGET_SAMPLE_RATE),
                "-af", f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}",
                "-f", TARGET_FORMAT, output_path,
            ],
            timeout=TIMEOUT_CONVERT,
            label="single-pass loudnorm",
        )


def _parse_loudnorm_json(stderr_text: str) -> dict | None:
    """Extract the JSON block that ffmpeg loudnorm prints to stderr.

    Uses regex to specifically target the loudnorm JSON (must contain "input_i")
    rather than blindly grabbing the last { } block.
    """
    try:
        match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', stderr_text, re.DOTALL)
        if not match:
            return None
        return json.loads(match.group(0))
    except (json.JSONDecodeError, ValueError):
        return None


def _get_duration_ms(path: str) -> int:
    """Return audio duration in milliseconds using ffprobe (no RAM cost)."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams", path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    info = json.loads(result.stdout)
    try:
        return int(float(info["format"]["duration"]) * 1000)
    except (KeyError, ValueError, TypeError):
        # Fallback: check audio streams for duration
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "audio" and "duration" in stream:
                return int(float(stream["duration"]) * 1000)
        raise RuntimeError(f"Could not determine duration from ffprobe")


def _detect_silence_gaps_ffmpeg(path: str) -> list[tuple[float, float]]:
    """Detect silence gaps using ffmpeg silencedetect filter.

    Streams the audio entirely inside ffmpeg — Python never touches PCM data.
    Returns list of (start_ms, end_ms) tuples for gaps >= SILENCE_GAP_MS.
    """
    result = subprocess.run(
        [
            "ffmpeg", "-i", path,
            "-af", (
                f"silencedetect=noise={SILENCE_THRESHOLD_DB}dB"
                f":d={SILENCE_GAP_MS / 1000}"
            ),
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SILENCE,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    # silencedetect writes to stderr regardless of exit code
    gaps = _parse_silencedetect_output(result.stderr)
    logger.info(
        "Detected %d silence gaps (>= %ds)",
        len(gaps), SILENCE_GAP_MS // 1000,
    )
    return gaps


def _parse_silencedetect_output(stderr: str) -> list[tuple[float, float]]:
    """Parse ffmpeg silencedetect stderr into (start_ms, end_ms) tuples.

    Uses regex for robustness across FFmpeg versions.  zip() naturally handles
    the edge case where audio ends in silence (unclosed start with no end).
    """
    starts = re.findall(r"silence_start:\s*([0-9.]+)", stderr)
    ends = re.findall(r"silence_end:\s*([0-9.]+)", stderr)

    gaps = []
    for s, e in zip(starts, ends):
        try:
            gaps.append((float(s) * 1000.0, float(e) * 1000.0))
        except ValueError:
            continue
    return gaps


def _split_and_upload_chunks_ffmpeg(
    source_path: str,
    manifest: dict,
    recording_id: str,
    storage,
    tmpdir: str,
) -> None:
    """Cut each chunk from source WAV via ffmpeg and upload immediately.

    Uses `-ss` before `-i` (input seek) so ffmpeg jumps directly to the
    timestamp without decoding from the start — critical for 9-hour files.
    Each chunk file is deleted from disk right after upload to keep disk
    usage bounded to roughly 2× the largest single chunk.
    """
    chunk_dir = os.path.join(tmpdir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)

    for chunk_info in manifest["chunks"]:
        audio_start_ms = chunk_info.get("audio_start_ms", chunk_info["start_ms"])
        audio_end_ms = chunk_info.get("audio_end_ms", chunk_info["end_ms"])
        audio_start_s = audio_start_ms / 1000.0
        duration_s = (audio_end_ms - audio_start_ms) / 1000.0

        chunk_path = os.path.join(chunk_dir, chunk_info["file"])

        _run_ffmpeg(
            [
                "ffmpeg", "-y",
                "-ss", f"{audio_start_s:.3f}",   # seek BEFORE -i = O(1) for WAV
                "-i", source_path,
                "-t", f"{duration_s:.3f}",
                "-ar", str(TARGET_SAMPLE_RATE),
                "-ac", str(TARGET_CHANNELS),
                "-f", TARGET_FORMAT, chunk_path,
            ],
            timeout=TIMEOUT_CHUNK,
            label=f"chunk {chunk_info['index']}",
        )

        chunk_key = f"preprocessed/{recording_id}/chunks/{chunk_info['file']}"
        _upload_audio_from_file_sync(storage, chunk_path, chunk_key)

        # Free disk space immediately — don't accumulate all chunks at once
        os.unlink(chunk_path)


# ---------------------------------------------------------------------------
# Chunk manifest helpers
# ---------------------------------------------------------------------------

def _build_chunk_manifest(
    duration_ms: int,
    silence_gaps_ms: list[tuple[float, float]],
    recording_id: str,
) -> dict:
    """Build a chunk manifest using silence-gap-aware splitting.

    Strategy:
    1. Use silence gaps >= 30s as preferred split points (split at midpoint).
    2. If a speech region between two silence gaps exceeds max_chunk_duration,
       fall back to fixed-window splitting within that region.
    3. Apply overlap at each boundary for transcription continuity.

    Returns manifest dict consumed by dispatch_transcription and
    dispatch_diarization.
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
                {
                    "index": 0,
                    "start_ms": 0,
                    "end_ms": duration_ms,
                    "audio_start_ms": 0,
                    "audio_end_ms": duration_ms,
                    "file": "chunk_000.wav",
                },
            ],
        }

    # Derive preferred split points from silence gap midpoints
    split_points = sorted({
        (gap_start + gap_end) / 2.0
        for gap_start, gap_end in silence_gaps_ms
    })

    # Build raw boundaries: accept a split point if it's at least 1 min from
    # the previous one (or half a chunk, whichever is larger)
    min_gap = max(chunk_duration_ms * 0.5, 60_000)
    raw_boundaries: list[float] = [0.0]
    last = 0.0
    for sp in split_points:
        if sp - last >= min_gap:
            raw_boundaries.append(sp)
            last = sp

    if raw_boundaries[-1] < duration_ms:
        raw_boundaries.append(float(duration_ms))

    # Sub-split any segment that still exceeds max chunk duration
    final_boundaries: list[float] = []
    for i in range(len(raw_boundaries) - 1):
        seg_start = raw_boundaries[i]
        seg_end = raw_boundaries[i + 1]
        final_boundaries.append(seg_start)
        if seg_end - seg_start > chunk_duration_ms:
            sub = seg_start + chunk_duration_ms
            while sub < seg_end:
                final_boundaries.append(sub)
                sub += chunk_duration_ms
    final_boundaries.append(float(duration_ms))

    # Build chunk list with overlap
    n = len(final_boundaries) - 1
    chunks = []
    for i in range(n):
        chunk_start = max(0.0, final_boundaries[i] - (overlap_ms if i > 0 else 0))
        chunk_end = min(
            final_boundaries[i + 1] + (overlap_ms if i < n - 1 else 0),
            float(duration_ms),
        )
        chunks.append({
            "index": i,
            "start_ms": int(final_boundaries[i]),
            "end_ms": int(final_boundaries[i + 1]),
            "audio_start_ms": int(chunk_start),
            "audio_end_ms": int(chunk_end),
            "file": f"chunk_{i:03d}.wav",
        })

    logger.info(
        "[%s] Manifest: %d chunks from %d silence gaps (duration=%ds, chunk_max=%ds)",
        recording_id,
        len(chunks),
        len(silence_gaps_ms),
        duration_ms // 1000,
        chunk_duration_ms // 1000,
    )

    return {
        "recording_id": recording_id,
        "duration_ms": duration_ms,
        "needs_chunking": True,
        "chunks": chunks,
    }


def load_manifest(recording_id: str) -> dict:
    """Load chunk manifest from storage.

    Used by dispatch_transcription and dispatch_diarization to determine
    chunk boundaries at runtime without hitting the database.
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
    """Preprocess raw audio: convert to 16kHz mono WAV, normalize loudness,
    detect silence gaps, split into chunks, upload to storage.

    All audio manipulation happens inside ffmpeg subprocesses.  Python RAM
    usage stays ~50 MB regardless of recording length.

    Returns recording_id for the next pipeline stage (dispatch_transcription).
    """
    logger.info("[%s] Starting audio preprocessing", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.PREPROCESSING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()
        file_url = recording["file_url"]

        with tempfile.TemporaryDirectory() as tmpdir:

            # ------------------------------------------------------------------
            # 1. Download source audio to disk (streaming — no RAM spike)
            # ------------------------------------------------------------------
            # Use DB format instead of parsing URL (avoids pre-signed URL query params)
            ext = f".{recording.get('format', 'mp3').lower()}"
            input_path = os.path.join(tmpdir, f"input{ext}")
            logger.info("[%s] Downloading %s → %s", recording_id, file_url, input_path)
            _download_audio_sync_streaming(file_url, input_path)

            # ------------------------------------------------------------------
            # 2. Convert + normalize (two-pass loudnorm, all in ffmpeg)
            # ------------------------------------------------------------------
            output_path = os.path.join(tmpdir, "preprocessed.wav")
            _convert_and_normalize(input_path, output_path)

            # ------------------------------------------------------------------
            # 3. Get duration via ffprobe (no AudioSegment needed)
            # ------------------------------------------------------------------
            duration_ms = _get_duration_ms(output_path)
            duration_seconds = duration_ms // 1000
            logger.info("[%s] Duration: %ds (%d chunks expected)", recording_id, duration_seconds,
                        max(1, duration_ms // (settings.audio_chunk_duration_minutes * 60 * 1000)))
            _update_recording_duration_sync(recording_id, duration_seconds)

            # ------------------------------------------------------------------
            # 4. Detect silence gaps (ffmpeg silencedetect, streaming)
            # ------------------------------------------------------------------
            logger.info("[%s] Detecting silence gaps", recording_id)
            silence_gaps = _detect_silence_gaps_ffmpeg(output_path)
            _store_silence_gaps_sync(recording_id, silence_gaps)

            # ------------------------------------------------------------------
            # 5. Build chunk manifest (pure Python, no audio in RAM)
            # ------------------------------------------------------------------
            manifest = _build_chunk_manifest(duration_ms, silence_gaps, recording_id)

            # ------------------------------------------------------------------
            # 6. Split chunks on disk + upload immediately (ffmpeg seek+cut)
            # ------------------------------------------------------------------
            logger.info(
                "[%s] Splitting into %d chunks (needs_chunking=%s)",
                recording_id, len(manifest["chunks"]), manifest["needs_chunking"],
            )
            _split_and_upload_chunks_ffmpeg(output_path, manifest, recording_id, storage, tmpdir)

            # ------------------------------------------------------------------
            # 7. Persist manifest to DB + storage
            # ------------------------------------------------------------------
            _store_chunk_manifest_sync(recording_id, manifest)
            manifest_key = f"preprocessed/{recording_id}/manifest.json"
            storage.upload_sync(json.dumps(manifest).encode("utf-8"), manifest_key)

            logger.info(
                "[%s] Preprocessing complete — duration: %ds, chunks: %d",
                recording_id, duration_seconds, len(manifest["chunks"]),
            )

        return recording_id

    except Exception as exc:
        logger.error("[%s] Preprocessing failed: %s", recording_id, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise