"""Speech-to-text worker — transcribes audio using NVIDIA Parakeet STT."""
import io
import logging
import uuid

from celery import chord, group
from celery.exceptions import Ignore
from pydub import AudioSegment

from src.ai.stt import transcribe_audio
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import TranscriptSegment
from src.storage.local import get_storage
from src.workers.celery_app import celery_app
from src.workers.pipeline_control import PipelineHalted, fail_and_halt
from src.workers.preprocessing import (
    _get_recording_sync,
    _update_recording_status_sync,
    _upload_audio_from_file_sync as _upload_audio_sync,
    load_manifest,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VAD integration (lazy imports — torch/torchaudio may not be installed)
# ---------------------------------------------------------------------------

def _apply_vad_filter(audio_bytes: bytes) -> tuple[bytes, list[dict]]:
    """Apply VAD silence filtering to audio bytes.

    Wraps vad_filter_audio with lazy import and graceful fallback.
    Returns (filtered_audio, speech_segments) or (original_audio, []) on failure.
    """
    if not settings.vad_use_silero or not settings.vad_filter_before_stt:
        return audio_bytes, []

    try:
        from src.ai.vad import vad_filter_audio
        return vad_filter_audio(audio_bytes)
    except ImportError:
        logger.warning("VAD dependencies (torch/torchaudio) not available — skipping VAD filter")
        return audio_bytes, []
    except Exception as exc:
        logger.warning("VAD filter failed (%s) — using original audio", exc)
        return audio_bytes, []


def _remap_timestamps(
    segments: list[dict],
    words: list[dict],
    speech_segments: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Remap STT timestamps from VAD-filtered audio back to original timeline.

    After VAD strips silence, STT returns timestamps relative to the compressed
    (speech-only) audio. This function maps them back to the original chunk
    timeline using the speech segment boundaries.

    Algorithm:
        For each STT timestamp t, find the speech segment [s_i.start, s_i.end]
        where the cumulative filtered position contains t. Then:
            original_time = s_i.start + (t - cumulative_before_i)

    Args:
        segments: STT segment dicts with start/end keys
        words: STT word dicts with start/end keys
        speech_segments: VAD speech segments in original timeline (seconds)

    Returns:
        (remapped_segments, remapped_words)
    """
    if not speech_segments:
        return segments, words

    # Build cumulative mapping: filtered_position → original_position
    # cumulative[i] = total speech seconds before segment i
    cumulative = [0.0]
    for seg in speech_segments:
        cumulative.append(cumulative[-1] + (seg["end"] - seg["start"]))
    total_filtered_duration = cumulative[-1]

    def remap(t: float) -> float:
        """Map a single timestamp from filtered → original timeline."""
        if t <= 0:
            return speech_segments[0]["start"] if speech_segments else t
        if t >= total_filtered_duration:
            return speech_segments[-1]["end"] if speech_segments else t

        # Binary-style search: find which speech segment contains this filtered time
        for i, seg in enumerate(speech_segments):
            seg_duration = seg["end"] - seg["start"]
            if cumulative[i] + seg_duration > t:
                offset_in_seg = t - cumulative[i]
                return seg["start"] + offset_in_seg

        # Fallback: clamp to last segment end
        return speech_segments[-1]["end"]

    remapped_segments = []
    for seg in segments:
        new_seg = dict(seg)
        new_seg["start"] = remap(seg["start"])
        new_seg["end"] = remap(seg["end"])
        if new_seg["start"] < new_seg["end"]:
            remapped_segments.append(new_seg)

    remapped_words = []
    for word in words:
        new_word = dict(word)
        new_word["start"] = remap(word["start"])
        new_word["end"] = remap(word["end"])
        if new_word["start"] < new_word["end"]:
            remapped_words.append(new_word)

    return remapped_segments, remapped_words

# Module-level engine — reused across task invocations in the same worker process.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine)


def _store_transcript_sync(recording_id: str, segments: list[dict], words: list[dict] = None):
    """Store transcript segments and word-level transcripts in the database using sync session."""
    with _SessionLocal() as session:
        # Clear any existing segments for this recording
        session.query(TranscriptSegment).filter(
            TranscriptSegment.recording_id == uuid.UUID(recording_id)
        ).delete()

        # Insert new segments
        for seg in segments:
            transcript_seg = TranscriptSegment(
                recording_id=uuid.UUID(recording_id),
                speaker_label="UNKNOWN",  # Will be updated by diarization
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"],
            )
            session.add(transcript_seg)

        # Store word-level transcripts if provided
        if words:
            from src.models.transcript import WordTranscript
            session.query(WordTranscript).filter(
                WordTranscript.recording_id == uuid.UUID(recording_id)
            ).delete()

            for word_data in words:
                word_transcript = WordTranscript(
                    recording_id=uuid.UUID(recording_id),
                    word=word_data["word"],
                    start_time=word_data["start"],
                    end_time=word_data["end"],
                    confidence=word_data["confidence"],
                    speaker_label="UNKNOWN",  # Will be updated by diarization
                )
                session.add(word_transcript)

        session.commit()
        logger.info("[%s] Stored %d transcript segments, %d words", recording_id, len(segments), len(words or []))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, name="transcribe_audio")
def transcribe_audio_task(self, recording_id: str) -> str:
    """Transcribe preprocessed audio using configured STT provider (Groq Whisper or NVIDIA Riva).

    Args:
        recording_id: The recording to transcribe

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info("[%s] Starting transcription", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.TRANSCRIBING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()

        # Download preprocessed audio
        preprocessed_key = f"preprocessed/{recording_id}/audio.wav"
        logger.info("[%s] Downloading preprocessed audio", recording_id)
        audio_data = storage.download_sync(preprocessed_key)

        # For large files, chunk the audio (use 15-minute chunks with 30-second overlap)
        chunk_duration_ms = settings.audio_chunk_duration_minutes * 60 * 1000  # 15 minutes
        overlap_ms = settings.audio_chunk_overlap_seconds * 1000  # 30 seconds

        # Calculate audio duration and max chunk size
        audio = AudioSegment.from_wav(io.BytesIO(audio_data))
        duration_ms = len(audio)
        max_chunk_size = settings.max_audio_chunk_bytes  # from settings

        if len(audio_data) <= max_chunk_size and duration_ms <= chunk_duration_ms:
            # File is small enough and short enough — single-shot transcription
            # Apply VAD filter to strip silence before STT
            speech_segments = []
            if settings.vad_filter_before_stt:
                audio_data, speech_segments = _apply_vad_filter(audio_data)

            result = transcribe_audio(audio_data)
            segments = result.get("segments", [])
            words = result.get("words", [])

            # Remap timestamps if VAD was applied
            if speech_segments:
                segments, words = _remap_timestamps(segments, words, speech_segments)
        else:
            # File too large or too long — chunk for STT provider limits
            # (Groq Whisper has 25 MB file limit)
            logger.info(
                "[%s] Audio needs chunking: %.1f MB, %.1f min (limit: %d MB, %d min)",
                recording_id,
                len(audio_data) / (1024 * 1024),
                duration_ms / 60000,
                max_chunk_size // (1024 * 1024),
                chunk_duration_ms // 60000,
            )
            segments, words = _transcribe_in_chunks_with_overlap(
                audio_data, recording_id, chunk_duration_ms, overlap_ms
            )

        if not segments:
            fail_and_halt(recording_id, "No transcript segments produced by STT")

        # Store transcript in database
        _store_transcript_sync(recording_id, segments, words)

        logger.info("[%s] Transcription complete: %d segments", recording_id, len(segments))
        return recording_id

    except PipelineHalted:
        raise Ignore()
    except Exception as exc:
        logger.error("[%s] Transcription failed: %s", recording_id, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise


# ---------------------------------------------------------------------------
# Parallel chunk tasks (dispatched via chord)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="dispatch_transcription")
def dispatch_transcription(self, recording_id: str):
    """Dispatch parallel transcription chunk tasks or take fast path.

    Reads the chunk manifest produced by preprocessing. If the recording
    is short enough, delegates to the existing single-task fast path.
    Otherwise replaces itself with a chord of parallel chunk tasks.
    """
    logger.info("[%s] Dispatching transcription", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.TRANSCRIBING)

    manifest = load_manifest(recording_id)

    if not manifest["needs_chunking"]:
        # Fast path: short recording, use existing task directly
        try:
            return transcribe_audio_task(recording_id)
        except PipelineHalted:
            raise Ignore()

    # Build parallel chunk group
    header = group(
        transcribe_chunk.s(
            recording_id,
            chunk["index"],
            chunk["file"],
        )
        for chunk in manifest["chunks"]
    )

    logger.info(
        "[%s] Dispatching %d parallel transcription chunks",
        recording_id, len(manifest["chunks"]),
    )

    # Replace self with chord: header runs in parallel, callback merges
    raise self.replace(
        chord(header, merge_transcription_results.s(recording_id))
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60,
                 soft_time_limit=600, time_limit=900,
                 name="transcribe_chunk")
def transcribe_chunk(self, recording_id: str, chunk_index: int, chunk_file: str):
    """Transcribe a single audio chunk. Idempotent with acks_late.

    Downloads only its own chunk file (~28MB for 15-min WAV) from storage,
    not the full recording. Applies VAD filtering to strip silence before
    sending to the STT API, then remaps timestamps back to original timeline.

    Returns a dict (JSON-serializable) — never raises past max_retries,
    returns a failure sentinel instead to prevent chord errors.
    """
    logger.info(
        "[%s] Transcribing chunk %d (%s)", recording_id, chunk_index, chunk_file,
    )
    try:
        storage = get_storage()
        chunk_key = f"preprocessed/{recording_id}/chunks/{chunk_file}"
        chunk_data = storage.download_sync(chunk_key)

        # Apply VAD filter: strip silence before STT (saves 40-60% API cost)
        speech_segments = []
        if settings.vad_filter_before_stt:
            filtered_data, speech_segments = _apply_vad_filter(chunk_data)
            if speech_segments:
                logger.info(
                    "[%s] Chunk %d VAD: %.1fMB → %.1fMB (%d speech segments)",
                    recording_id, chunk_index,
                    len(chunk_data) / (1024 * 1024),
                    len(filtered_data) / (1024 * 1024),
                    len(speech_segments),
                )
                chunk_data = filtered_data

        result = transcribe_audio(chunk_data)
        segments = result.get("segments", [])
        words = result.get("words", [])

        # Remap STT timestamps from VAD-filtered → original chunk timeline
        if speech_segments:
            segments, words = _remap_timestamps(segments, words, speech_segments)

        logger.info(
            "[%s] Chunk %d: %d segments, %d words",
            recording_id, chunk_index, len(segments), len(words),
        )

        return {
            "chunk_index": chunk_index,
            "segments": segments,
            "words": words,
            "failed": False,
        }
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        # Return sentinel instead of raising — prevents chord error
        logger.error(
            "[%s] Chunk %d failed permanently: %s",
            recording_id, chunk_index, exc,
        )
        return {
            "chunk_index": chunk_index,
            "segments": [],
            "words": [],
            "failed": True,
            "error": str(exc),
        }


@celery_app.task(bind=True, name="merge_transcription_results")
def merge_transcription_results(self, chunk_results: list, recording_id: str):
    """Merge chunk transcription results, dedup overlaps, store to DB.

    Chord callback that receives a list of chunk result dicts.
    Adjusts timestamps by chunk offset, deduplicates overlap regions,
    and stores the final merged transcript to the database.

    Returns recording_id for the next pipeline stage.
    """
    logger.info("[%s] Merging %d transcription chunk results", recording_id, len(chunk_results))

    # Separate successful from failed chunks
    successful = [r for r in chunk_results if not r.get("failed")]
    failed = [r for r in chunk_results if r.get("failed")]
    if failed:
        logger.warning(
            "[%s] %d transcription chunks failed: %s",
            recording_id, len(failed),
            [r["chunk_index"] for r in failed],
        )

    if not successful:
        fail_and_halt(recording_id, "All transcription chunks failed")

    # Load manifest to get chunk offsets
    manifest = load_manifest(recording_id)
    chunk_offsets = {c["index"]: c["start_ms"] / 1000.0 for c in manifest["chunks"]}

    # Adjust timestamps by chunk offset and collect
    all_segments = []
    all_words = []
    for result in successful:
        offset = chunk_offsets.get(result["chunk_index"], 0.0)

        for seg in result["segments"]:
            seg["start"] = seg["start"] + offset
            seg["end"] = seg["end"] + offset
            if seg["start"] < seg["end"]:
                all_segments.append(seg)

        for word in result["words"]:
            word["start"] = word["start"] + offset
            word["end"] = word["end"] + offset
            if word["start"] < word["end"]:
                all_words.append(word)

    # Dedup overlap regions (reuse existing functions)
    all_words = _deduplicate_words(all_words)
    all_segments = _deduplicate_segments(all_segments)

    if not all_segments:
        fail_and_halt(recording_id, "No transcript segments produced after merging chunks")

    # Store to DB (clear-and-reinsert for idempotency)
    _store_transcript_sync(recording_id, all_segments, all_words)

    logger.info(
        "[%s] Transcription merge complete: %d segments, %d words (from %d/%d chunks)",
        recording_id, len(all_segments), len(all_words),
        len(successful), len(chunk_results),
    )

    return recording_id


def _transcribe_in_chunks_with_overlap(
    audio_data: bytes,
    recording_id: str,
    chunk_duration_ms: int,
    overlap_ms: int,
) -> tuple[list[dict], list[dict]]:
    """Split large audio into chunks with overlap and transcribe each.

    Uses 15-minute chunks with 30-second overlap to maintain context across boundaries.
    Deduplicates words in overlap regions by keeping higher-confidence versions.

    Args:
        audio_data: Raw audio bytes
        recording_id: Recording identifier
        chunk_duration_ms: Chunk duration in milliseconds
        overlap_ms: Overlap duration in milliseconds

    Returns:
        Tuple of (segments, words) with deduplicated results
    """
    logger.info(
        "[%s] Audio requires chunking: %ds chunks with %ds overlap",
        recording_id,
        chunk_duration_ms // 1000,
        overlap_ms // 1000,
    )

    audio = AudioSegment.from_wav(io.BytesIO(audio_data))
    duration_ms = len(audio)

    all_segments = []
    all_words = []
    step_ms = chunk_duration_ms - overlap_ms  # Effective step between chunks

    chunk_index = 0
    for chunk_start_ms in range(0, duration_ms, step_ms):
        chunk_end_ms = min(chunk_start_ms + chunk_duration_ms, duration_ms)
        chunk = audio[chunk_start_ms:chunk_end_ms]

        chunk_buffer = io.BytesIO()
        chunk.export(chunk_buffer, format="wav")
        chunk_bytes = chunk_buffer.getvalue()

        logger.info(
            "[%s] Transcribing chunk %d: %.0fs-%.0fs",
            recording_id,
            chunk_index + 1,
            chunk_start_ms / 1000,
            chunk_end_ms / 1000,
        )

        # Apply VAD filter per chunk to strip silence before STT
        speech_segments = []
        if settings.vad_filter_before_stt:
            chunk_bytes, speech_segments = _apply_vad_filter(chunk_bytes)

        result = transcribe_audio(chunk_bytes)
        chunk_segments = result.get("segments", [])
        chunk_words = result.get("words", [])

        # Remap timestamps from VAD-filtered → original chunk timeline
        if speech_segments:
            chunk_segments, chunk_words = _remap_timestamps(
                chunk_segments, chunk_words, speech_segments
            )

        # Adjust timestamps by chunk offset
        offset_seconds = chunk_start_ms / 1000.0
        chunk_end_seconds = chunk_end_ms / 1000.0

        for seg in chunk_segments:
            seg["start"] = max(seg["start"] + offset_seconds, offset_seconds)
            seg["end"] = min(seg["end"] + offset_seconds, chunk_end_seconds)
            if seg["start"] < seg["end"]:
                all_segments.append(seg)

        for word in chunk_words:
            word["start"] = max(word["start"] + offset_seconds, offset_seconds)
            word["end"] = min(word["end"] + offset_seconds, chunk_end_seconds)
            if word["start"] < word["end"]:
                all_words.append(word)

        chunk_index += 1

    # Deduplicate words and segments in overlap regions
    all_words = _deduplicate_words(all_words)
    all_segments = _deduplicate_segments(all_segments)

    logger.info(
        "[%s] Chunked transcription complete: %d segments, %d words (after dedup)",
        recording_id,
        len(all_segments),
        len(all_words),
    )
    return all_segments, all_words


def _deduplicate_words(words: list[dict], tolerance_ms: float = 50.0) -> list[dict]:
    """Remove duplicate words in overlap regions.

    If two words have overlapping timestamps (within tolerance), keep the one
    with higher confidence.

    Args:
        words: List of word dicts with start, end, confidence
        tolerance_ms: Timestamp overlap tolerance in milliseconds

    Returns:
        Deduplicated word list
    """
    if not words:
        return []

    # Sort by start time
    sorted_words = sorted(words, key=lambda w: w["start"])

    deduplicated = [sorted_words[0]]
    tolerance_s = tolerance_ms / 1000.0

    for word in sorted_words[1:]:
        last_word = deduplicated[-1]

        # Check if this word overlaps with the last one
        time_diff = word["start"] - last_word["start"]

        if time_diff < tolerance_s and word["word"].lower() == last_word["word"].lower():
            # Duplicate detected — keep higher confidence
            if word["confidence"] > last_word["confidence"]:
                deduplicated[-1] = word  # Replace with higher confidence version
        else:
            deduplicated.append(word)

    return deduplicated


def _deduplicate_segments(segments: list[dict], tolerance_s: float = 1.0) -> list[dict]:
    """Remove duplicate segments produced by overlap regions."""
    if not segments:
        return []
    sorted_segs = sorted(segments, key=lambda s: s["start"])
    result = [sorted_segs[0]]
    for seg in sorted_segs[1:]:
        last = result[-1]
        if (
            abs(seg["start"] - last["start"]) < tolerance_s
            and seg["text"].strip() == last["text"].strip()
        ):
            continue
        result.append(seg)
    return result
