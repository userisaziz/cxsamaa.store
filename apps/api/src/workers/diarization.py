"""Speaker diarization worker — assigns speaker labels to transcript segments."""
import logging
import uuid
from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

# Module-level engine — reused across task invocations in the same worker process.
# Celery workers are long-lived processes, so creating an engine per DB call
# wastes connections and adds latency.
_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine)


def _get_transcript_segments_sync(recording_id: str) -> list[dict]:
    """Load transcript segments from DB using sync session."""
    with _SessionLocal() as session:
        rows = (
            session.query(TranscriptSegment)
            .filter(TranscriptSegment.recording_id == uuid.UUID(recording_id))
            .order_by(TranscriptSegment.start_time)
            .all()
        )
        return [
            {"start": row.start_time, "end": row.end_time, "text": row.text}
            for row in rows
        ]


def _update_speaker_labels_sync(recording_id: str, labeled_segments: list[dict]) -> None:
    """Write speaker labels back to transcript_segments table."""
    with _SessionLocal() as session:
        for seg in labeled_segments:
            session.query(TranscriptSegment).filter(
                TranscriptSegment.recording_id == uuid.UUID(recording_id),
                TranscriptSegment.start_time == seg["start"],
                TranscriptSegment.end_time == seg["end"],
            ).update({"speaker_label": seg["speaker"]})
        session.commit()
    logger.info(
        "[%s] Updated speaker labels for %d segments",
        recording_id,
        len(labeled_segments),
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, name="diarize_audio")
def diarize_audio(self, recording_id: str) -> str:
    """Diarize speakers using pyannote.audio (primary) or NVIDIA NeMo (fallback).

    Pyannote.audio provides superior accuracy for multilingual retail sales audio:
    - Better handling of overlapping speech
    - Improved robustness with background noise
    - Optimized for Hindi/English/Arabic code-switching scenarios
    - Handles accent diversity across Middle East and South Asia

    Falls back to NVIDIA NIM if pyannote is disabled or fails.

    Returns:
        recording_id for the next pipeline stage.
    """
    logger.info("[%s] Starting speaker diarization", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.DIARIZING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()

        preprocessed_key = f"preprocessed/{recording_id}/audio.wav"
        logger.info("[%s] Downloading preprocessed audio for diarization", recording_id)
        audio_data = _download_audio_sync(storage, preprocessed_key)

        logger.info("[%s] Running diarization (pyannote.audio primary)", recording_id)
        speaker_segments = diarize_audio_api(audio_data)
        logger.info(
            "[%s] Diarization produced %d speaker segments",
            recording_id,
            len(speaker_segments),
        )

        transcript_segments = _get_transcript_segments_sync(recording_id)
        if not transcript_segments:
            # FIX 2: status update on early-return path so recording isn't
            # left stuck in DIARIZING indefinitely.
            logger.warning(
                "[%s] No transcript segments found — skipping speaker assignment",
                recording_id,
            )
            _update_recording_status_sync(recording_id, RecordingStatus.DIARIZED)
            return recording_id

        labeled_segments = assign_speaker_labels(transcript_segments, speaker_segments)
        _update_speaker_labels_sync(recording_id, labeled_segments)

        speaker_counts = Counter(seg["speaker"] for seg in labeled_segments)
        logger.info("[%s] Speaker distribution: %s", recording_id, dict(speaker_counts))

        # FIX 1: mark as DIARIZED so downstream stages can proceed.
        _update_recording_status_sync(recording_id, RecordingStatus.DIARIZED)
        return recording_id

    except Exception as exc:
        logger.error("[%s] Diarization failed: %s", recording_id, exc, exc_info=True)

        # FIX 3: only retry while attempts remain; on the final failure
        # update status to FAILED and re-raise the original exception so
        # callers see the real error, not MaxRetriesExceededError.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise