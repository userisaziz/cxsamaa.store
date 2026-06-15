"""Speaker role classification worker — identifies Salesperson vs Customer."""
import logging
import uuid


from src.ai.role_classifier import classify_speaker_roles
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import ConversationTurn, SpeakerRole
from src.workers.pipeline_control import PipelineHalted, fail_and_halt
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


def _get_conversation_turns_sync(recording_id: str) -> list[dict]:
    """Load conversation turns from DB."""
    with _SessionLocal() as session:
        rows = (
            session.query(ConversationTurn)
            .filter(ConversationTurn.recording_id == uuid.UUID(recording_id))
            .order_by(ConversationTurn.start_time)
            .all()
        )
        return [
            {
                "speaker": row.speaker_label,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "text": row.text,
                "word_count": row.word_count,
            }
            for row in rows
        ]


def _store_role_classifications_sync(recording_id: str, classifications: dict):
    """Store role classification results in DB."""
    with _SessionLocal() as session:
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
        logger.info("[%s] Stored %d role classifications", recording_id, len(classifications))


from src.workers.retry import pipeline_retry


@pipeline_retry
def classify_speaker_roles(recording_id: str) -> str:
    """Classify speaker roles as Salesperson or Customer.

    Uses LLM-based classification (primary) with heuristic fallback.
    Stores results in speaker_roles table and updates conversation_turns.

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info("[%s] Starting speaker role classification", recording_id)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Load conversation turns
        conversation_turns = _get_conversation_turns_sync(recording_id)
        if not conversation_turns:
            logger.warning("[%s] No conversation turns found — cannot classify roles", recording_id)
            fail_and_halt(recording_id, "No conversation turns")

        logger.info("[%s] Classifying roles from %d turns", recording_id, len(conversation_turns))

        # Classify speaker roles
        classifications = classify_speaker_roles(conversation_turns, use_llm=True)

        if not classifications:
            logger.warning("[%s] No role classifications produced — leaving existing roles", recording_id)

        else:
            _store_role_classifications_sync(recording_id, classifications)

        # Log results
        for speaker, role_info in classifications.items():
            logger.info(
                "[%s] %s → %s (method=%s, confidence=%.2f)",
                recording_id,
                speaker,
                role_info["role"],
                role_info["method"],
                role_info["confidence"],
            )

        logger.info(
            "[%s] Role classification complete: %d speakers classified",
            recording_id,
            len(classifications),
        )
        
        # Mark stage complete in pipeline_state
        from src.services.pipeline_state import mark_stage_complete_sync
        mark_stage_complete_sync(recording_id, "roles")
        
        return recording_id

    except PipelineHalted:
        raise
    except Exception as exc:
        logger.error("[%s] Role classification failed: %s", recording_id, exc, exc_info=True)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        
        # Mark stage failed in pipeline_state
        from src.services.pipeline_state import mark_stage_failed_sync
        mark_stage_failed_sync(recording_id, "roles", str(exc))
        raise
