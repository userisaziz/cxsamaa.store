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


def _store_transcript_sync(recording_id: str, segments: list[dict]):
    """Store transcript segments in the database using sync session."""
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

        session.commit()
        logger.info(f"[{recording_id}] Stored {len(segments)} transcript segments")
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

        # For large files, chunk the audio (NVIDIA NIM has file size limits)
        max_chunk_size = 25 * 1024 * 1024  # 25MB

        if len(audio_data) <= max_chunk_size:
            segments = transcribe_audio(audio_data)
        else:
            segments = _transcribe_in_chunks(audio_data, recording_id, max_chunk_size)

        if not segments:
            logger.warning(f"[{recording_id}] No transcript segments produced")
            segments = []

        # Store transcript in database
        _store_transcript_sync(recording_id, segments)

        logger.info(f"[{recording_id}] Transcription complete: {len(segments)} segments")
        return recording_id

    except Exception as exc:
        logger.error(f"[{recording_id}] Transcription failed: {exc}")
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)


def _transcribe_in_chunks(
    audio_data: bytes, recording_id: str, max_chunk_size: int
) -> list[dict]:
    """Split large audio into chunks and transcribe each."""
    logger.info(f"[{recording_id}] Audio too large ({len(audio_data)} bytes), chunking")

    audio = AudioSegment.from_wav(io.BytesIO(audio_data))
    duration_ms = len(audio)

    # Calculate chunk size in ms based on byte ratio
    chunk_duration_ms = int(duration_ms * (max_chunk_size / len(audio_data)))
    chunk_duration_ms = int(chunk_duration_ms * 0.9)  # safety margin

    all_segments = []
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
        chunk_segments = transcribe_audio(chunk_bytes)

        # Adjust timestamps by offset
        offset_seconds = offset_ms / 1000.0
        for seg in chunk_segments:
            seg["start"] += offset_seconds
            seg["end"] += offset_seconds
            all_segments.append(seg)

        offset_ms = end_ms

    logger.info(f"[{recording_id}] Chunked transcription: {len(all_segments)} total segments")
    return all_segments
