"""Speech-to-text worker — transcribes audio using NVIDIA Parakeet STT.

Chunking is driven by the manifest produced in preprocessing (VAD-aware,
silence-driven). Transcription uses per-chunk VAD segments from the manifest
for silence-stripping before STT — no redundant VAD detection at this stage.
"""
import logging
import time
import uuid

from src.ai.stt import transcribe_audio
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import TranscriptSegment
from src.storage.local import get_storage
from src.workers.pipeline_control import PipelineHalted, fail_and_halt
from src.workers.preprocessing import (
    _get_recording_sync,
    _update_recording_status_sync,
    _upload_audio_from_file_sync as _upload_audio_sync,
    load_manifest,
)

logger = logging.getLogger(__name__)


def _transcribe_with_retry(
    audio_data: bytes,
    recording_id: str,
    chunk_index: int,
    max_retries: int = 3,
    initial_wait: float = 2.0,
    max_wait: float = 60.0,
) -> dict:
    """Transcribe audio with exponential backoff retry for timeout errors.

    Implements chunk-level retry logic specifically for timeout errors
    (e.g., Deepgram "write operation timed out"). Retries with increasing
    wait times before giving up.

    After all retries are exhausted, attempts an alternative STT provider
    if primary == fallback (to avoid retry loops).

    Args:
        audio_data: Raw audio bytes
        recording_id: Recording UUID
        chunk_index: Chunk index for logging
        max_retries: Maximum retry attempts (default: 3)
        initial_wait: Initial wait time in seconds (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 60.0)

    Returns:
        Transcription result dict with "segments" and "words"

    Raises:
        Exception: If all retries fail
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(
                    "[%s] Chunk %d: Retry attempt %d/%d after timeout",
                    recording_id, chunk_index, attempt, max_retries,
                )

            result = transcribe_audio(audio_data)
            if attempt > 0:
                logger.info(
                    "[%s] Chunk %d: Retry %d succeeded",
                    recording_id, chunk_index, attempt,
                )
            return result

        except Exception as exc:
            last_error = exc
            error_msg = str(exc).lower()

            # Check if this is a timeout error (worth retrying)
            is_timeout = any(
                keyword in error_msg
                for keyword in ["timeout", "timed out", "deadline exceeded"]
            )

            if not is_timeout or attempt >= max_retries:
                # Not a timeout or out of retries — give up
                logger.error(
                    "[%s] Chunk %d: STT failed on attempt %d: %s",
                    recording_id, chunk_index, attempt, exc,
                )
                
                # ✅ FIX: After retries exhausted, try alternative provider if primary == fallback
                if attempt >= max_retries and settings.stt_fallback_provider == settings.stt_provider:
                    from src.ai.stt import PROVIDERS
                    available = [p for p in PROVIDERS if p != settings.stt_provider]
                    if available:
                        alternative = available[0]
                        logger.info(
                            "[%s] Chunk %d: All retries exhausted, trying alternative provider: %s",
                            recording_id, chunk_index, alternative,
                        )
                        try:
                            from src.ai.stt import _call_provider
                            result, alt_name = _call_provider(alternative, audio_data, "audio.wav")
                            logger.info(
                                "[%s] Chunk %d: Alternative provider %s succeeded",
                                recording_id, chunk_index, alt_name,
                            )
                            return result
                        except Exception as alt_error:
                            logger.error(
                                "[%s] Chunk %d: Alternative provider also failed: %s",
                                recording_id, chunk_index, alt_error,
                            )
                            # Fall through to raise the original error
                
                raise

            # Calculate exponential backoff with jitter
            wait_time = min(
                initial_wait * (2 ** attempt),
                max_wait,
            )
            # Add small jitter to prevent thundering herd
            import random
            jitter = random.uniform(0, 0.1 * wait_time)
            wait_time += jitter

            logger.warning(
                "[%s] Chunk %d: Timeout on attempt %d, retrying in %.1fs: %s",
                recording_id, chunk_index, attempt, wait_time, exc,
            )
            time.sleep(wait_time)


# ---------------------------------------------------------------------------
# VAD audio filtering using pre-computed segments (no detection at this stage)
# ---------------------------------------------------------------------------

def _filter_audio_with_vad_segments(
    audio_bytes: bytes,
    vad_segments: list[dict],
) -> tuple[bytes, list[dict]]:
    """Filter audio using pre-computed VAD segments from the manifest.

    Unlike _apply_vad_filter (which runs full VAD detection + extraction),
    this uses VAD segments already computed during preprocessing. Only
    the extraction step runs — silently skipping the expensive detection.

    Args:
        audio_bytes: Raw chunk audio data (16kHz mono WAV)
        vad_segments: VAD speech segments from manifest (relative to chunk start)

    Returns:
        (filtered_audio_bytes, speech_segments)
        If no segments provided, returns (original_audio, []).
    """
    if not vad_segments:
        return audio_bytes, []

    try:
        from src.ai.vad import extract_speech_regions
        filtered = extract_speech_regions(audio_bytes, vad_segments)
        size_before = len(audio_bytes)
        size_after = len(filtered)
        if size_before > 0:
            reduction = (1 - size_after / size_before) * 100
            logger.debug(
                "VAD pre-filter: %.1fMB → %.1fMB (%.0f%% reduction, %d segments)",
                size_before / (1024 * 1024),
                size_after / (1024 * 1024),
                reduction,
                len(vad_segments),
            )
        return filtered, vad_segments
    except ImportError:
        logger.warning("VAD deps unavailable — skipping audio filter")
        return audio_bytes, []
    except Exception as exc:
        logger.warning("VAD pre-filter failed (%s) — using original audio", exc)
        return audio_bytes, []


def _apply_vad_filter(audio_bytes: bytes) -> tuple[bytes, list[dict]]:
    """Apply VAD silence filtering to audio bytes (legacy — uses full VAD detection).

    Prefer _filter_audio_with_vad_segments() when pre-computed VAD segments
    are available from the manifest. This function is retained for backward
    compatibility with the short-recording fast path where no manifest VAD exists.

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
                speaker_label=seg.get("speaker", "UNKNOWN"),
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
                    speaker_label=word_data.get("speaker", "UNKNOWN"),
                )
                session.add(word_transcript)

        session.commit()
        logger.info("[%s] Stored %d transcript segments, %d words", recording_id, len(segments), len(words or []))


from concurrent.futures import ThreadPoolExecutor

from src.workers.retry import pipeline_retry


@pipeline_retry
def transcribe_audio_task(recording_id: str) -> str:
    """Transcribe a short recording (no chunking needed) in a single STT call.

    This is the fast path for recordings short enough to fit in one API call.
    Uses VAD segments from the manifest for silence-stripping before STT.

    For chunked recordings, dispatch_transcription() handles parallel
    chunk processing via transcribe_chunk() instead.

    Args:
        recording_id: The recording to transcribe

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info("[%s] Starting single-shot transcription", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.TRANSCRIBING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()
        manifest = load_manifest(recording_id)

        # Download preprocessed audio
        preprocessed_key = f"preprocessed/{recording_id}/audio.wav"
        logger.info("[%s] Downloading preprocessed audio", recording_id)
        audio_data = storage.download_sync(preprocessed_key)

        # Use VAD segments from manifest for silence-stripping before STT
        speech_segments: list[dict] = []
        chunk_vad = manifest.get("chunks", [{}])[0].get("vad_segments", [])
        if settings.vad_filter_before_stt and chunk_vad:
            audio_data, speech_segments = _filter_audio_with_vad_segments(
                audio_data, chunk_vad,
            )

        result = transcribe_audio(audio_data)
        segments = result.get("segments", [])
        words = result.get("words", [])

        # Remap timestamps if VAD filtering was applied
        if speech_segments:
            segments, words = _remap_timestamps(segments, words, speech_segments)

        if not segments:
            fail_and_halt(recording_id, "No transcript segments produced by STT")

        # Store transcript in database
        _store_transcript_sync(recording_id, segments, words)

        logger.info("[%s] Transcription complete: %d segments", recording_id, len(segments))

        # Mark stage complete in pipeline_state
        from src.services.pipeline_state import mark_stage_complete_sync
        mark_stage_complete_sync(recording_id, "stt")

        return recording_id

    except PipelineHalted:
        raise
    except Exception as exc:
        logger.error("[%s] Transcription failed: %s", recording_id, exc, exc_info=True)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))

        # Mark stage failed in pipeline_state
        from src.services.pipeline_state import mark_stage_failed_sync
        mark_stage_failed_sync(recording_id, "stt", str(exc))
        raise


# ---------------------------------------------------------------------------
# Parallel chunk dispatch (ThreadPoolExecutor replaces Celery chord)
# ---------------------------------------------------------------------------

def dispatch_transcription(recording_id: str):
    """Dispatch parallel transcription chunk tasks or take fast path.

    Reads the chunk manifest produced by preprocessing. If the recording
    is short enough, uses the fast path. Otherwise processes chunks in
    parallel via ThreadPoolExecutor, passing per-chunk VAD segments
    from the manifest to avoid redundant VAD detection.
    """
    logger.info("[%s] Dispatching transcription", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.TRANSCRIBING)

    manifest = load_manifest(recording_id)

    if not manifest["needs_chunking"]:
        # Fast path: short recording
        return transcribe_audio_task(recording_id)

    # Parallel chunk processing
    num_chunks = len(manifest["chunks"])
    logger.info(
        "[%s] Processing %d transcription chunks in parallel",
        recording_id, num_chunks,
    )

    with ThreadPoolExecutor(max_workers=min(num_chunks, 4)) as executor:
        futures = [
            executor.submit(
                _transcribe_chunk_fn,
                recording_id,
                chunk["index"],
                chunk["file"],
                chunk.get("vad_segments", []),
            )
            for chunk in manifest["chunks"]
        ]
        results = [f.result() for f in futures]

    return merge_transcription_results(results, recording_id)


def _transcribe_chunk_fn(
    recording_id: str,
    chunk_index: int,
    chunk_file: str,
    vad_segments: list[dict],
):
    """Wrapper for transcribe_chunk that can be submitted to ThreadPoolExecutor."""
    return transcribe_chunk(recording_id, chunk_index, chunk_file, vad_segments)


@pipeline_retry
def transcribe_chunk(
    recording_id: str,
    chunk_index: int,
    chunk_file: str,
    vad_segments: list[dict] | None = None,
):
    """Transcribe a single audio chunk. Idempotent with acks_late.

    Downloads only its own chunk file (~28MB for 15-min WAV) from storage,
    not the full recording. Uses pre-computed VAD segments from the manifest
    to strip silence before sending to the STT API (no redundant VAD detection),
    then remaps timestamps back to original timeline.

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

        # Apply VAD filter using pre-computed segments from preprocessing
        # (no VAD detection at this stage — segments are already computed)
        speech_segments: list[dict] = []
        if settings.vad_filter_before_stt and vad_segments:
            filtered_data, speech_segments = _filter_audio_with_vad_segments(
                chunk_data, vad_segments,
            )
            if speech_segments:
                logger.info(
                    "[%s] Chunk %d VAD pre-filter: %.1fMB → %.1fMB (%d segments)",
                    recording_id, chunk_index,
                    len(chunk_data) / (1024 * 1024),
                    len(filtered_data) / (1024 * 1024),
                    len(speech_segments),
                )
                chunk_data = filtered_data

        # Retry STT with exponential backoff for timeout errors
        result = _transcribe_with_retry(chunk_data, recording_id, chunk_index)
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
        # Return sentinel instead of raising — prevents chain error
        logger.error(
            "[%s] Chunk %d failed: %s",
            recording_id, chunk_index, exc,
        )
        return {
            "chunk_index": chunk_index,
            "segments": [],
            "words": [],
            "failed": True,
            "error": str(exc),
        }


def merge_transcription_results(chunk_results: list, recording_id: str):
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

    # Check if we have enough successful chunks to continue
    total_chunks = len(chunk_results)
    success_rate = len(successful) / total_chunks if total_chunks > 0 else 0
    
    if success_rate < 0.5:
        # Less than 50% success rate — halt the pipeline
        fail_and_halt(
            recording_id,
            f"Too many transcription chunks failed ({len(failed)}/{total_chunks}, success rate: {success_rate:.0%})"
        )
    
    if success_rate < 1.0:
        logger.warning(
            "[%s] Continuing with partial transcript: %d/%d chunks successful (%.0%% success rate)",
            recording_id, len(successful), total_chunks, success_rate * 100,
        )

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
