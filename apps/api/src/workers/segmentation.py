"""Conversation segmentation worker — splits recording into discrete conversations."""
import logging
import uuid

from src.ai.segmenter import segment_conversations as segment_conversations_ai
from src.config import settings
from src.models.conversation import Conversation
from src.models.recording import RecordingStatus
from src.models.transcript import TranscriptSegment
from src.workers.celery_app import celery_app
from src.workers.preprocessing import (
    _get_recording_sync,
    _update_recording_status_sync,
)

logger = logging.getLogger(__name__)


def _get_labeled_segments_sync(recording_id: str) -> list[dict]:
    """Load transcript segments with speaker labels from DB."""
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
            {
                "start": row.start_time,
                "end": row.end_time,
                "text": row.text,
                "speaker": row.speaker_label,
            }
            for row in rows
        ]
    engine.dispose()
    return segments


def _get_silence_gaps_sync(recording_id: str) -> list[tuple[float, float]]:
    """Load silence gaps from recording.silence_gaps JSONB field."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models.recording import Recording

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording and recording.silence_gaps:
            # Convert from list of dicts back to list of tuples
            gaps = [(g["start"], g["end"]) for g in recording.silence_gaps]
            engine.dispose()
            return gaps
    engine.dispose()
    return []


def _store_conversations_sync(recording_id: str, conversations: list[dict]):
    """Store conversation records in DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models.recording import Recording

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        # Look up the parent recording to copy denormalized fields
        recording = session.query(Recording).filter(
            Recording.id == uuid.UUID(recording_id)
        ).first()
        salesperson_id = recording.salesperson_id if recording else None
        recorded_at = recording.recorded_at if recording else None

        # Clear any existing conversations for this recording
        session.query(Conversation).filter(
            Conversation.recording_id == uuid.UUID(recording_id)
        ).delete()

        for conv in conversations:
            conversation = Conversation(
                recording_id=uuid.UUID(recording_id),
                salesperson_id=salesperson_id,
                start_time=conv["start_time"],
                end_time=conv["end_time"],
                duration_seconds=conv["end_time"] - conv["start_time"],
                segment_count=conv["segment_count"],
                recorded_at=recorded_at,
            )
            session.add(conversation)

        session.commit()
        logger.info(f"[{recording_id}] Stored {len(conversations)} conversations")
    engine.dispose()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="segment_conversations")
def segment_conversations(self, recording_id: str) -> str:
    """Segment recording into discrete customer conversations.

    Uses silence gaps, greeting detection, and farewell detection to identify
    conversation boundaries per PRD AI-05.

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info(f"[{recording_id}] Starting conversation segmentation")
    _update_recording_status_sync(recording_id, RecordingStatus.SEGMENTING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Load labeled transcript segments
        labeled_segments = _get_labeled_segments_sync(recording_id)
        if not labeled_segments:
            logger.warning(f"[{recording_id}] No transcript segments found — cannot segment")
            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, "No transcript segments")
            return recording_id

        logger.info(f"[{recording_id}] Segmenting {len(labeled_segments)} transcript segments")

        # Load silence gaps from preprocessing
        silence_gaps = _get_silence_gaps_sync(recording_id)
        if silence_gaps:
            logger.info(f"[{recording_id}] Using {len(silence_gaps)} silence gaps from preprocessing")

        # Run segmentation
        conversations = segment_conversations_ai(labeled_segments, silence_gaps=silence_gaps if silence_gaps else None)

        if not conversations:
            logger.warning(f"[{recording_id}] No conversations detected after segmentation")
            # Store empty — mark as completed with 0 conversations
            conversations = []

        # Store conversations in DB
        _store_conversations_sync(recording_id, conversations)

        logger.info(
            f"[{recording_id}] Segmentation complete: {len(conversations)} conversations detected"
        )
        return recording_id

    except Exception as exc:
        logger.error(f"[{recording_id}] Segmentation failed: {exc}")
        if self.request.retries >= self.max_retries:

            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)
