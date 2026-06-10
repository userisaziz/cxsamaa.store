"""Conversation turn builder worker — merges word-level transcripts into turns."""
import logging
import uuid

from src.ai.conversation_builder import build_conversation_turns
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import ConversationTurn, WordTranscript
from src.workers.celery_app import celery_app
from src.workers.preprocessing import (
    _get_recording_sync,
    _update_recording_status_sync,
)

logger = logging.getLogger(__name__)


def _get_word_transcripts_sync(recording_id: str) -> list[dict]:
    """Load word-level transcripts from DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        rows = (
            session.query(WordTranscript)
            .filter(WordTranscript.recording_id == uuid.UUID(recording_id))
            .order_by(WordTranscript.start_time)
            .all()
        )
        words = [
            {
                "word": row.word,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "confidence": row.confidence,
                "speaker_label": row.speaker_label,
            }
            for row in rows
        ]
    engine.dispose()
    return words


def _store_turns_sync(recording_id: str, turns: list[dict]):
    """Store conversation turn records in DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
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
        logger.info(f"[{recording_id}] Stored {len(turns)} conversation turns")
    engine.dispose()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="build_conversation_turns")
def build_conversation_turns_task(self, recording_id: str) -> str:
    """Build conversation turns from word-level transcripts.

    Merges word-level transcripts into speaker turns based on:
    - Speaker continuity (same speaker = same turn)
    - Gap detection (gap > 1s = new turn)

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info(f"[{recording_id}] Starting conversation turn building")
    _update_recording_status_sync(recording_id, RecordingStatus.TRANSCRIBING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Load word-level transcripts
        word_transcripts = _get_word_transcripts_sync(recording_id)
        if not word_transcripts:
            logger.warning(f"[{recording_id}] No word transcripts found — cannot build turns")
            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, "No word transcripts")
            return recording_id

        logger.info(f"[{recording_id}] Building turns from {len(word_transcripts)} words")

        # Build conversation turns
        turns = build_conversation_turns(word_transcripts)

        if not turns:
            logger.warning(f"[{recording_id}] No turns built")
            turns = []

        # Store turns in DB
        _store_turns_sync(recording_id, turns)

        logger.info(
            f"[{recording_id}] Turn building complete: {len(turns)} turns built"
        )
        return recording_id

    except Exception as exc:
        logger.error(f"[{recording_id}] Turn building failed: {exc}")
        if self.request.retries >= self.max_retries:
            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)
