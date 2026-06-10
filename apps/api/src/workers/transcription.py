"""Speech-to-text worker — transcribes audio using NVIDIA Parakeet STT."""
import io
import logging
import uuid

from pydub import AudioSegment

from src.ai.stt import transcribe_audio
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import TranscriptSegment
from src.storage.local import get_storage
from src.workers.celery_app import celery_app
from src.workers.preprocessing import (
    _download_audio_sync,
    _get_recording_sync,
    _update_recording_status_sync,
    _upload_audio_sync,
)

logger = logging.getLogger(__name__)


def _store_transcript_sync(recording_id: str, segments: list[dict], words: list[dict] = None):
    """Store transcript segments and word-level transcripts in the database using sync session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
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
        logger.info(f"[{recording_id}] Stored {len(segments)} transcript segments, {len(words or [])} words")
    engine.dispose()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, name="transcribe_audio")
def transcribe_audio_task(self, recording_id: str) -> str:
    """Transcribe preprocessed audio using NVIDIA Parakeet STT.

    Args:
        recording_id: The recording to transcribe

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info(f"[{recording_id}] Starting transcription")
    _update_recording_status_sync(recording_id, RecordingStatus.TRANSCRIBING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()

        # Download preprocessed audio
        preprocessed_key = f"preprocessed/{recording_id}/audio.wav"
        logger.info(f"[{recording_id}] Downloading preprocessed audio")
        audio_data = _download_audio_sync(storage, preprocessed_key)

        # For large files, chunk the audio (use 15-minute chunks with 30-second overlap)
        chunk_duration_ms = settings.audio_chunk_duration_minutes * 60 * 1000  # 15 minutes
        overlap_ms = settings.audio_chunk_overlap_seconds * 1000  # 30 seconds

        if len(audio_data) <= max_chunk_size and duration_ms <= chunk_duration_ms:
            result = transcribe_audio(audio_data)
            segments = result.get("segments", [])
            words = result.get("words", [])
        else:
            segments, words = _transcribe_in_chunks_with_overlap(
                audio_data, recording_id, chunk_duration_ms, overlap_ms
            )

        if not segments:
            logger.warning(f"[{recording_id}] No transcript segments produced")
            segments = []

        # Store transcript in database
        _store_transcript_sync(recording_id, segments, words)

        logger.info(f"[{recording_id}] Transcription complete: {len(segments)} segments")
        return recording_id

    except Exception as exc:
        logger.error(f"[{recording_id}] Transcription failed: {exc}")
        if self.request.retries >= self.max_retries:

            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)


def _transcribe_in_chunks(
    audio_data: bytes, recording_id: str, max_chunk_size: int
) -> tuple[list[dict], list[dict]]:
    """Split large audio into chunks and transcribe each.
    
    Returns:
        Tuple of (segments, words)
    """
    logger.info(f"[{recording_id}] Audio too large ({len(audio_data)} bytes), chunking")

    audio = AudioSegment.from_wav(io.BytesIO(audio_data))
    duration_ms = len(audio)

    # Calculate chunk size in ms based on byte ratio
    chunk_duration_ms = int(duration_ms * (max_chunk_size / len(audio_data)))
    chunk_duration_ms = int(chunk_duration_ms * 0.9)  # safety margin

    all_segments = []
    all_words = []
    offset_ms = 0

    while offset_ms < duration_ms:
        end_ms = min(offset_ms + chunk_duration_ms, duration_ms)
        chunk = audio[offset_ms:end_ms]

        chunk_buffer = io.BytesIO()
        chunk.export(chunk_buffer, format="wav")
        chunk_bytes = chunk_buffer.getvalue()

        logger.info(
            f"[{recording_id}] Transcribing chunk {offset_ms/1000:.0f}s-{end_ms/1000:.0f}s"
        )
        result = transcribe_audio(chunk_bytes)
        chunk_segments = result.get("segments", [])
        chunk_words = result.get("words", [])

        # Adjust timestamps by offset and clamp to chunk boundaries
        offset_seconds = offset_ms / 1000.0
        chunk_end_seconds = end_ms / 1000.0
        for seg in chunk_segments:
            seg["start"] = max(seg["start"] + offset_seconds, offset_seconds)
            seg["end"] = min(seg["end"] + offset_seconds, chunk_end_seconds)
            if seg["start"] < seg["end"]:  # skip degenerate segments
                all_segments.append(seg)

        # Adjust word timestamps
        for word in chunk_words:
            word["start"] = max(word["start"] + offset_seconds, offset_seconds)
            word["end"] = min(word["end"] + offset_seconds, chunk_end_seconds)
            if word["start"] < word["end"]:
                all_words.append(word)

        offset_ms = end_ms

    logger.info(f"[{recording_id}] Chunked transcription: {len(all_segments)} segments, {len(all_words)} words")
    return all_segments, all_words


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
        f"[{recording_id}] Audio requires chunking: "
        f"{chunk_duration_ms/1000:.0f}s chunks with {overlap_ms/1000:.0f}s overlap"
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
            f"[{recording_id}] Transcribing chunk {chunk_index + 1}: "
            f"{chunk_start_ms/1000:.0f}s-{chunk_end_ms/1000:.0f}s"
        )

        result = transcribe_audio(chunk_bytes)
        chunk_segments = result.get("segments", [])
        chunk_words = result.get("words", [])

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

    # Deduplicate words in overlap regions
    all_words = _deduplicate_words(all_words)

    logger.info(
        f"[{recording_id}] Chunked transcription complete: "
        f"{len(all_segments)} segments, {len(all_words)} words (after dedup)"
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
