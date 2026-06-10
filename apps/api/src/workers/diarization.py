"""Speaker diarization worker — assigns speaker labels to transcript segments."""
import logging
import uuid

from src.ai.diarizer import assign_speaker_labels, diarize_audio as diarize_audio_api
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import TranscriptSegment
from src.storage.local import get_storage
from src.workers.celery_app import celery_app
from src.workers.preprocessing import (
    _download_audio_sync,
    _get_recording_sync,
    _update_recording_status_sync,
)

logger = logging.getLogger(__name__)


def _get_transcript_segments_sync(recording_id: str) -> list[dict]:
    """Load transcript segments from DB using sync session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        rows = (
            session.query(TranscriptSegment)
            .filter(TranscriptSegment.recording_id == uuid.UUID(recording_id))
            .order_by(TranscriptSegment.start_time)
            .all()
        )
        segments = [
            {"start": row.start_time, "end": row.end_time, "text": row.text}
            for row in rows
        ]
    engine.dispose()
    return segments


def _update_speaker_labels_sync(recording_id: str, labeled_segments: list[dict]):
    """Write speaker labels back to transcript_segments table."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        for seg in labeled_segments:
            (
                session.query(TranscriptSegment)
                .filter(
                    TranscriptSegment.recording_id == uuid.UUID(recording_id),
                    TranscriptSegment.start_time == seg["start"],
                    TranscriptSegment.end_time == seg["end"],
                )
                .update({"speaker_label": seg["speaker"]})
            )
        session.commit()
        logger.info(f"[{recording_id}] Updated speaker labels for {len(labeled_segments)} segments")
    engine.dispose()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, name="diarize_audio")
def diarize_audio(self, recording_id: str) -> str:
    """Diarize speakers using pyannote.audio (primary) or NVIDIA NeMo (fallback) and assign labels.

    Pyannote.audio provides superior accuracy for multilingual retail sales audio:
    - Better handling of overlapping speech
    - Improved robustness with background noise  
    - Optimized for Hindi/English/Arabic code-switching scenarios
    - Handles accent diversity across Middle East and South Asia

    Falls back to NVIDIA NIM if pyannote is disabled or fails.

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info(f"[{recording_id}] Starting speaker diarization")
    _update_recording_status_sync(recording_id, RecordingStatus.DIARIZING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()

        # Download preprocessed audio
        preprocessed_key = f"preprocessed/{recording_id}/audio.wav"
        logger.info(f"[{recording_id}] Downloading preprocessed audio for diarization")
        audio_data = _download_audio_sync(storage, preprocessed_key)

        # Call diarization (pyannote primary, NVIDIA fallback)
        logger.info(f"[{recording_id}] Running diarization (pyannote.audio primary)")
        speaker_segments = diarize_audio_api(audio_data)
        logger.info(f"[{recording_id}] Diarization produced {len(speaker_segments)} speaker segments")

        # Load transcript segments from DB
        transcript_segments = _get_transcript_segments_sync(recording_id)
        if not transcript_segments:
            logger.warning(f"[{recording_id}] No transcript segments found — skipping speaker assignment")
            return recording_id

        # Merge speaker labels into transcript segments
        labeled_segments = assign_speaker_labels(transcript_segments, speaker_segments)

        # Write speaker labels back to DB
        _update_speaker_labels_sync(recording_id, labeled_segments)

        # Log speaker distribution
        speaker_counts: dict[str, int] = {}
        for seg in labeled_segments:
            speaker = seg["speaker"]
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        logger.info(f"[{recording_id}] Speaker distribution: {speaker_counts}")

        return recording_id

    except Exception as exc:
        logger.error(f"[{recording_id}] Diarization failed: {exc}")
        if self.request.retries >= self.max_retries:

            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)
