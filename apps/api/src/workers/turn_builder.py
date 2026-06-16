"""Conversation turn builder worker — merges word-level transcripts into turns."""
import logging
import uuid


from src.ai.conversation_builder import build_conversation_turns as _build_turns_ai
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import ConversationTurn, WordTranscript
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


def _get_word_transcripts_sync(recording_id: str) -> list[dict]:
    """Load word-level transcripts from DB."""
    with _SessionLocal() as session:
        rows = (
            session.query(WordTranscript)
            .filter(WordTranscript.recording_id == uuid.UUID(recording_id))
            .order_by(WordTranscript.start_time)
            .all()
        )
        return [
            {
                "word": row.word,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "confidence": row.confidence,
                "speaker_label": row.speaker_label,
            }
            for row in rows
        ]


def _store_turns_sync(recording_id: str, turns: list[dict]):
    """Store conversation turn records in DB."""
    with _SessionLocal() as session:
        # Clear any existing turns for this recording
        session.query(ConversationTurn).filter(
            ConversationTurn.recording_id == uuid.UUID(recording_id)
        ).delete()

        for turn in turns:
            conversation_turn = ConversationTurn(
                recording_id=uuid.UUID(recording_id),
                speaker_label=turn["speaker"],
                start_time=turn["start_time"],
                end_time=turn["end_time"],
                text=turn["text"],
                word_count=turn["word_count"],
            )
            session.add(conversation_turn)

        session.commit()
        logger.info("[%s] Stored %d conversation turns", recording_id, len(turns))


from src.workers.retry import pipeline_retry


@pipeline_retry
def build_conversation_turns(recording_id: str) -> str:
    """Build conversation turns from word-level transcripts.

    Merges word-level transcripts into speaker turns based on:
    - Speaker continuity (same speaker = same turn)
    - Gap detection (gap > 1s = new turn)
    
    Speaker labels come from STT diarization (Deepgram built-in diarizer
    provides \"SPEAKER_0\", \"SPEAKER_1\", etc.) or fall back to \"UNKNOWN\"
    if no diarization was performed.

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info("[%s] Starting conversation turn building", recording_id)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Load word-level transcripts
        word_transcripts = _get_word_transcripts_sync(recording_id)
        if not word_transcripts:
            logger.warning("[%s] No word transcripts found — cannot build turns", recording_id)
            fail_and_halt(recording_id, "No word transcripts")

        logger.info("[%s] Building turns from %d words", recording_id, len(word_transcripts))
        
        # Log if diarization was skipped (all speakers will be UNKNOWN)
        from src.config import settings
        if not settings.enable_diarization:
            logger.info(
                "[%s] Pyannote diarization disabled — using STT-level speaker labels "
                "from Deepgram built-in diarizer",
                recording_id,
            )

        # Build conversation turns
        turns = _build_turns_ai(word_transcripts)

        if not turns:
            logger.warning("[%s] No turns built from word transcripts", recording_id)
            fail_and_halt(recording_id, "No turns built from word transcripts")

        # Store turns in DB
        _store_turns_sync(recording_id, turns)

        logger.info(
            "[%s] Turn building complete: %d turns built",
            recording_id,
            len(turns),
        )
        
        # Mark stage complete in pipeline_state
        from src.services.pipeline_state import mark_stage_complete_sync
        mark_stage_complete_sync(recording_id, "turns")
        
        return recording_id

    except PipelineHalted:
        raise
    except Exception as exc:
        logger.error("[%s] Turn building failed: %s", recording_id, exc, exc_info=True)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        
        # Mark stage failed in pipeline_state
        from src.services.pipeline_state import mark_stage_failed_sync
        mark_stage_failed_sync(recording_id, "turns", str(exc))
        raise
