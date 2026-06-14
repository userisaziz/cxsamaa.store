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

# Module-level engine — reused across task invocations in the same worker process.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine)


def _get_labeled_segments_sync(recording_id: str) -> list[dict]:
    """Load transcript segments with speaker labels from DB."""
    with _SessionLocal() as session:
        rows = (
            session.query(TranscriptSegment)
            .filter(TranscriptSegment.recording_id == uuid.UUID(recording_id))
            .order_by(TranscriptSegment.start_time)
            .all()
        )
        return [
            {
                "start": row.start_time,
                "end": row.end_time,
                "text": row.text,
                "speaker": row.speaker_label,
            }
            for row in rows
        ]


def _get_silence_gaps_sync(recording_id: str) -> list[tuple[float, float]]:
    """Load silence gaps from recording.silence_gaps JSONB field."""
    from src.models.recording import Recording

    with _SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording and recording.silence_gaps:
            # Convert from list of dicts back to list of tuples
            return [(g["start"], g["end"]) for g in recording.silence_gaps]
    return []


def _store_conversations_sync(recording_id: str, conversations: list[dict]):
    """Store conversation records in DB."""
    from src.models.conversation import ConversationAnalysis
    from src.models.recording import Recording

    with _SessionLocal() as session:
        # Look up the parent recording to copy denormalized fields
        recording = session.query(Recording).filter(
            Recording.id == uuid.UUID(recording_id)
        ).first()
        salesperson_id = recording.salesperson_id if recording else None
        recorded_at = recording.recorded_at if recording else None

        # Clear any existing conversations and their analysis (cascade manually)
        conv_ids = [c.id for c in session.query(Conversation.id).filter(
            Conversation.recording_id == uuid.UUID(recording_id)
        ).all()]
        if conv_ids:
            session.query(ConversationAnalysis).filter(
                ConversationAnalysis.conversation_id.in_(conv_ids)
            ).delete(synchronize_session=False)
        session.query(Conversation).filter(
            Conversation.recording_id == uuid.UUID(recording_id)
        ).delete(synchronize_session=False)

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
        logger.info("[%s] Stored %d conversations", recording_id, len(conversations))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="segment_conversations")
def segment_conversations(self, recording_id: str) -> str:
    """Segment recording into discrete customer conversations.

    Uses silence gaps, greeting detection, and farewell detection to identify
    conversation boundaries per PRD AI-05.

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info("[%s] Starting conversation segmentation", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.SEGMENTING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Load labeled transcript segments
        labeled_segments = _get_labeled_segments_sync(recording_id)
        if not labeled_segments:
            logger.warning("[%s] No transcript segments found — cannot segment", recording_id)
            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, "No transcript segments")
            return recording_id

        logger.info("[%s] Segmenting %d transcript segments", recording_id, len(labeled_segments))

        # Load silence gaps from preprocessing
        silence_gaps = _get_silence_gaps_sync(recording_id)
        if silence_gaps:
            logger.info("[%s] Using %d silence gaps from preprocessing", recording_id, len(silence_gaps))

        # Run segmentation
        conversations = segment_conversations_ai(labeled_segments, silence_gaps=silence_gaps if silence_gaps else None)

        if not conversations:
            logger.warning("[%s] No conversations detected after segmentation", recording_id)
            # Store empty — mark as completed with 0 conversations
            conversations = []

        # Store conversations in DB
        _store_conversations_sync(recording_id, conversations)

        logger.info(
            "[%s] Segmentation complete: %d conversations detected",
            recording_id,
            len(conversations),
        )

        return recording_id

    except Exception as exc:
        logger.error("[%s] Segmentation failed: %s", recording_id, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise
