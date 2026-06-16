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
import socket
import subprocess
import tempfile
import uuid
from urllib.parse import urlparse

from botocore.exceptions import ConnectionClosedError, EndpointConnectionError
from boto3.s3.transfer import TransferConfig
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from urllib3.exceptions import ProtocolError

from src.config import settings
from src.models.recording import Recording, RecordingStatus
from src.storage.local import get_storage

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
            "status": rec.status.value if rec.status else None,
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

    Works for both local file:// URLs, HTTP(S) pre-signed URLs, and R2 storage keys.
    For R2, uses boto3's native download_file for O(1) memory streaming.
    For local paths, uses shutil.copyfileobj with 8 MB chunks.
    For HTTP(S), uses requests with stream=True.
    """
    parsed = urlparse(file_url)

    # R2 storage key (starts with "recordings/" or contains path separator without scheme)
    if file_url.startswith("recordings/") or (parsed.scheme == "" and "/" in file_url):
        storage = get_storage()
        logger.info("Downloading from storage backend: %s", file_url)

        # Use streaming download if available (R2/boto3), else fallback to bytes (Local)
        if hasattr(storage, "download_file_sync"):
            storage.download_file_sync(file_url, dest_path)
        else:
            # Fallback for backends that don't support streaming (e.g., LocalStorage)
            audio_data = storage.download_sync(file_url)
            with open(dest_path, "wb") as dst_f:
                dst_f.write(audio_data)
        return

    # Local file path — copy directly
    if parsed.scheme in ("", "file"):
        src = parsed.path if parsed.path else file_url
        with open(src, "rb") as src_f, open(dest_path, "wb") as dst_f:
            shutil.copyfileobj(src_f, dst_f, length=8 * 1024 * 1024)  # 8 MB chunks
        return

    # HTTP(S) — stream via requests
    import requests
    with requests.get(file_url, stream=True, timeout=900) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):
                f.write(chunk)


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type((
        ConnectionClosedError,
        EndpointConnectionError,
        ProtocolError,
        TimeoutError,
        socket.timeout,
    )),
    reraise=True,
)
def _upload_audio_from_file_sync(storage, file_path: str, key: str) -> str:
    """Upload a file from disk path — avoids loading entire chunk into RAM.

    Uses boto3's upload_file for R2 (multipart streaming from disk).
    Falls back to LocalStorage's write-bytes path.
    
    Retry strategy: Retries up to 4 times with exponential backoff (5s, 10s, 20s, 40s)
    for transient network failures (timeout, connection closed, protocol errors).
    """
    # R2/boto3: use upload_file which streams from disk via multipart upload
    if hasattr(storage, "client") and hasattr(storage.client, "upload_file"):
        # Force smaller multipart chunks to reduce retry cost on network drop
        transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,  # Use multipart for files > 8MB
            multipart_chunksize=8 * 1024 * 1024,  # Split into 8MB chunks
            max_concurrency=4,                    # Upload 4 chunks in parallel
            use_threads=True,
        )
        
        logger.info("Uploading %s to R2: %s", file_path, key)
        storage.client.upload_file(file_path, storage.bucket, key, Config=transfer_config)
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
    vad_segments: list[dict],
    recording_id: str,
) -> dict:
    """Build a chunk manifest using VAD-aware, silence-driven splitting.

    Strategy (VAD-driven, with ffmpeg silence gaps as fallback):
    1. Collect natural boundary candidates from VAD silence gaps (>= 2s between
       speech segments) and ffmpeg silence gaps (>= 30s). VAD boundaries are
       preferred because they operate at finer granularity.
    2. Walk the timeline: at each step, look ahead up to max_chunk_duration for
       the farthest natural split point. If found, split there (no overlap).
    3. If no natural split within max_chunk_duration, force-split at the time
       limit and apply overlap for ASR continuity across the boundary.
    4. Per-chunk VAD segments are clipped from the full-recording VAD output
       and stored with timestamps relative to chunk start for direct use by
       the transcription stage.

    Returns manifest dict consumed by dispatch_transcription and
    dispatch_diarization.
    """
    chunk_duration_ms = settings.audio_chunk_duration_minutes * 60 * 1000
    overlap_ms = settings.audio_chunk_overlap_seconds * 1000
    min_vad_silence_s = settings.vad_chunk_min_silence_for_boundary

    needs_chunking = duration_ms > chunk_duration_ms

    if not needs_chunking:
        # Short recording — single chunk with full VAD segments
        return {
            "recording_id": recording_id,
            "duration_ms": duration_ms,
            "needs_chunking": False,
            "vad_speech_segments": vad_segments,
            "chunks": [
                {
                    "index": 0,
                    "start_ms": 0,
                    "end_ms": duration_ms,
                    "audio_start_ms": 0,
                    "audio_end_ms": duration_ms,
                    "file": "chunk_000.wav",
                    "boundary_type_before": None,
                    "boundary_type_after": None,
                    "vad_segments": vad_segments,
                },
            ],
        }

    # ── Step 1: Collect natural boundary candidates ──────────────────────

    natural_boundaries_ms: list[float] = []

    # Type A: VAD silence gaps (gaps between speech segments >= min_silence)
    if vad_segments and settings.vad_driven_chunking:
        for i in range(len(vad_segments) - 1):
            gap_start_s = vad_segments[i]["end"]
            gap_end_s = vad_segments[i + 1]["start"]
            gap_duration_s = gap_end_s - gap_start_s
            if gap_duration_s >= min_vad_silence_s:
                midpoint_ms = ((gap_start_s + gap_end_s) / 2.0) * 1000.0
                natural_boundaries_ms.append(midpoint_ms)

    # Track VAD-derived boundary count before ffmpeg merge
    vad_boundary_count = len(natural_boundaries_ms)

    # Type B: ffmpeg silence gaps (30s+ gaps from silencedetect)
    for gap_start, gap_end in silence_gaps_ms:
        midpoint_ms = (gap_start + gap_end) / 2.0
        natural_boundaries_ms.append(midpoint_ms)

    # Deduplicate: merge boundaries within min_gap of each other
    natural_boundaries_ms.sort()
    min_gap_ms = max(chunk_duration_ms * 0.25, 60_000)  # at least 60s apart
    deduped: list[float] = []
    for pos in natural_boundaries_ms:
        if not deduped or pos - deduped[-1] >= min_gap_ms:
            deduped.append(pos)

    logger.info(
        "[%s] Natural boundary candidates: %d (from VAD=%d + ffmpeg=%d)",
        recording_id,
        len(deduped),
        vad_boundary_count,
        len(silence_gaps_ms),
    )

    # ── Step 2: Walk timeline, split at natural boundaries where possible ─

    boundaries_ms: list[float] = [0.0]
    is_natural: list[bool] = []  # is_natural[i] = True if boundary i→i+1 is natural

    current_pos = 0.0
    boundary_idx = 0

    while current_pos < duration_ms:
        look_ahead = min(current_pos + chunk_duration_ms, duration_ms)

        # Find the farthest natural boundary within [current_pos, look_ahead]
        best_natural = None
        while boundary_idx < len(deduped) and deduped[boundary_idx] <= look_ahead:
            candidate = deduped[boundary_idx]
            # Must be at least 60s from current position (avoid splitting too close)
            if candidate > current_pos + 60_000:
                best_natural = candidate
            boundary_idx += 1

        if best_natural is not None:
            # Split at natural boundary — no overlap needed
            boundaries_ms.append(best_natural)
            is_natural.append(True)
            current_pos = best_natural
        else:
            # No natural boundary found — force split at time limit
            if look_ahead >= duration_ms:
                boundaries_ms.append(float(duration_ms))
                is_natural.append(True)  # end of recording = natural
            else:
                boundaries_ms.append(look_ahead)
                is_natural.append(False)  # forced split
            current_pos = look_ahead

    # ── Step 3: Build chunks with smart overlap ──────────────────────────

    n = len(boundaries_ms) - 1
    chunks = []

    for i in range(n):
        chunk_start_ms = boundaries_ms[i]
        chunk_end_ms = boundaries_ms[i + 1]

        # Determine overlap: only at forced boundaries
        need_overlap_before = (i > 0 and not is_natural[i - 1])
        need_overlap_after = (i < n - 1 and not is_natural[i])

        audio_start_ms = (
            max(0.0, chunk_start_ms - overlap_ms) if need_overlap_before
            else chunk_start_ms
        )
        audio_end_ms = (
            min(chunk_end_ms + overlap_ms, float(duration_ms)) if need_overlap_after
            else chunk_end_ms
        )

        boundary_type_before = (
            "natural" if is_natural[i - 1] else "forced"
        ) if i > 0 else None
        boundary_type_after = (
            "natural" if is_natural[i] else "forced"
        ) if i < n - 1 else None

        # Per-chunk VAD segments: clip from full recording, make relative to
        # audio_start_ms so transcription can use them directly
        chunk_vad: list[dict] = []
        if vad_segments:
            chunk_start_s = audio_start_ms / 1000.0
            chunk_end_s = audio_end_ms / 1000.0
            for seg in vad_segments:
                if seg["end"] > chunk_start_s and seg["start"] < chunk_end_s:
                    clipped_start = max(seg["start"], chunk_start_s) - chunk_start_s
                    clipped_end = min(seg["end"], chunk_end_s) - chunk_start_s
                    if clipped_end > clipped_start:
                        chunk_vad.append({
                            "start": round(clipped_start, 3),
                            "end": round(clipped_end, 3),
                        })

        chunks.append({
            "index": i,
            "start_ms": int(chunk_start_ms),
            "end_ms": int(chunk_end_ms),
            "audio_start_ms": int(audio_start_ms),
            "audio_end_ms": int(audio_end_ms),
            "file": f"chunk_{i:03d}.wav",
            "boundary_type_before": boundary_type_before,
            "boundary_type_after": boundary_type_after,
            "vad_segments": chunk_vad,
        })

    logger.info(
        "[%s] Manifest: %d chunks (%d natural, %d forced), duration=%ds, max_chunk=%ds",
        recording_id,
        len(chunks),
        sum(1 for n in is_natural if n),
        sum(1 for n in is_natural if not n),
        duration_ms // 1000,
        chunk_duration_ms // 1000,
    )

    return {
        "recording_id": recording_id,
        "duration_ms": duration_ms,
        "needs_chunking": True,
        "vad_speech_segments": vad_segments,
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

from src.workers.retry import pipeline_retry


# ---------------------------------------------------------------------------

@pipeline_retry
def preprocess_audio(recording_id: str) -> str:
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
            # Extract file extension from MIME type (e.g., "audio/mpeg" -> "mp3")
            format_value = (recording.get('format') or 'mp3').lower()
            # Map MIME types to file extensions
            mime_to_ext = {
                'audio/mpeg': 'mp3',
                'audio/wav': 'wav',
                'audio/x-wav': 'wav',
                'audio/wave': 'wav',
                'audio/mp4': 'm4a',
                'audio/aac': 'aac',
                'audio/ogg': 'ogg',
                'audio/flac': 'flac',
            }
            ext = f".{mime_to_ext.get(format_value, format_value.split('/')[-1] if '/' in format_value else format_value)}"
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
            # 4. Detect VAD speech segments (Silero VAD on preprocessed WAV)
            #    Run BEFORE silence detection — VAD gives finer boundaries
            #    for chunk splitting. Falls back gracefully if torch unavailable.
            # ------------------------------------------------------------------
            vad_segments: list[dict] = []
            if settings.vad_use_silero and settings.vad_driven_chunking:
                logger.info("[%s] Detecting speech segments via Silero VAD", recording_id)
                try:
                    from src.ai.vad import detect_speech_segments_from_file
                    vad_segments = detect_speech_segments_from_file(output_path)
                    logger.info(
                        "[%s] VAD: %d speech segments detected (%.1fs total speech)",
                        recording_id,
                        len(vad_segments),
                        sum(s["end"] - s["start"] for s in vad_segments),
                    )
                except ImportError:
                    logger.warning(
                        "[%s] VAD deps (torch/torchaudio) unavailable — "
                        "falling back to ffmpeg silence detection only",
                        recording_id,
                    )
                except Exception as exc:
                    logger.warning("[%s] VAD failed (%s) — falling back to ffmpeg only", recording_id, exc)

            # ------------------------------------------------------------------
            # 5. Detect silence gaps (ffmpeg silencedetect, streaming)
            # ------------------------------------------------------------------
            logger.info("[%s] Detecting silence gaps", recording_id)
            silence_gaps = _detect_silence_gaps_ffmpeg(output_path)
            _store_silence_gaps_sync(recording_id, silence_gaps)

            # ------------------------------------------------------------------
            # 6. Build chunk manifest — VAD-driven with silence-gap fallback
            # ------------------------------------------------------------------
            manifest = _build_chunk_manifest(
                duration_ms, silence_gaps, vad_segments, recording_id,
            )

            # ------------------------------------------------------------------
            # 7. Split chunks on disk + upload immediately (ffmpeg seek+cut)
            #    For short recordings (needs_chunking=False), also upload the
            #    full preprocessed audio for the transcription fast path.
            # ------------------------------------------------------------------
            logger.info(
                "[%s] Splitting into %d chunks (needs_chunking=%s)",
                recording_id, len(manifest["chunks"]), manifest["needs_chunking"],
            )
            _split_and_upload_chunks_ffmpeg(output_path, manifest, recording_id, storage, tmpdir)
            
            # Upload full preprocessed audio for transcription fast path
            if not manifest["needs_chunking"]:
                audio_key = f"preprocessed/{recording_id}/audio.wav"
                _upload_audio_from_file_sync(storage, output_path, audio_key)
                logger.info("[%s] Uploaded full preprocessed audio: %s", recording_id, audio_key)

            # ------------------------------------------------------------------
            # 8. Persist manifest to DB + storage
            # ------------------------------------------------------------------
            _store_chunk_manifest_sync(recording_id, manifest)
            manifest_key = f"preprocessed/{recording_id}/manifest.json"
            storage.upload_sync(json.dumps(manifest).encode("utf-8"), manifest_key)

            logger.info(
                "[%s] Preprocessing complete — duration: %ds, chunks: %d",
                recording_id, duration_seconds, len(manifest["chunks"]),
            )
            
            # Mark stage complete in pipeline_state
            from src.services.pipeline_state import mark_stage_complete_sync
            mark_stage_complete_sync(recording_id, "preprocess")

        return recording_id

    except Exception as exc:
        logger.error("[%s] Preprocessing failed: %s", recording_id, exc, exc_info=True)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        
        # Mark stage failed in pipeline_state
        from src.services.pipeline_state import mark_stage_failed_sync
        mark_stage_failed_sync(recording_id, "preprocess", str(exc))
        raise