"""Speaker role classification worker — identifies Salesperson vs Customer."""
import logging
import uuid

from src.ai.role_classifier import classify_speaker_roles
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import ConversationTurn, SpeakerRole
from src.workers.celery_app import celery_app
from src.workers.preprocessing import (
    _get_recording_sync,
    _update_recording_status_sync,
)

logger = logging.getLogger(__name__)


def _get_conversation_turns_sync(recording_id: str) -> list[dict]:
    """Load conversation turns from DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        rows = (
            session.query(ConversationTurn)
            .filter(ConversationTurn.recording_id == uuid.UUID(recording_id))
            .order_by(ConversationTurn.start_time)
            .all()
        )
        turns = [
            {
                "speaker": row.speaker_label,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "text": row.text,
                "word_count": row.word_count,
            }
            for row in rows
        ]
    engine.dispose()
    return turns


def _store_role_classifications_sync(recording_id: str, classifications: dict):
    """Store role classification results in DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        # Clear any existing classifications for this recording
        session.query(SpeakerRole).filter(
            SpeakerRole.recording_id == uuid.UUID(recording_id)
        ).delete()

        # Insert new classifications
        for speaker_label, role_info in classifications.items():
            speaker_role = SpeakerRole(
                recording_id=uuid.UUID(recording_id),
                speaker_label=speaker_label,
                role_label=role_info["role"],
                classification_method=role_info["method"],
                confidence=role_info["confidence"],
            )
            session.add(speaker_role)

            # Also update conversation_turns with role_label
            session.query(ConversationTurn).filter(
                ConversationTurn.recording_id == uuid.UUID(recording_id),
                ConversationTurn.speaker_label == speaker_label,
            ).update({"role_label": role_info["role"]})

        session.commit()
        logger.info(f"[{recording_id}] Stored {len(classifications)} role classifications")
    engine.dispose()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="classify_speaker_roles")
def classify_speaker_roles_task(self, recording_id: str) -> str:
    """Classify speaker roles as Salesperson or Customer.

    Uses LLM-based classification (primary) with heuristic fallback.
    Stores results in speaker_roles table and updates conversation_turns.

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info(f"[{recording_id}] Starting speaker role classification")
    _update_recording_status_sync(recording_id, RecordingStatus.TRANSCRIBING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Load conversation turns
        conversation_turns = _get_conversation_turns_sync(recording_id)
        if not conversation_turns:
            logger.warning(f"[{recording_id}] No conversation turns found — cannot classify roles")
            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, "No conversation turns")
            return recording_id

        logger.info(f"[{recording_id}] Classifying roles from {len(conversation_turns)} turns")

        # Classify speaker roles
        classifications = classify_speaker_roles(conversation_turns, use_llm=True)

        if not classifications:
            logger.warning(f"[{recording_id}] No role classifications produced")
            classifications = {}

        # Store classifications in DB
        _store_role_classifications_sync(recording_id, classifications)

        # Log results
        for speaker, role_info in classifications.items():
            logger.info(
                f"[{recording_id}] {speaker} → {role_info['role']} "
                f"(method={role_info['method']}, confidence={role_info['confidence']:.2f})"
            )

        logger.info(
            f"[{recording_id}] Role classification complete: {len(classifications)} speakers classified"
        )
        return recording_id

    except Exception as exc:
        logger.error(f"[{recording_id}] Role classification failed: {exc}")
        if self.request.retries >= self.max_retries:
            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)
