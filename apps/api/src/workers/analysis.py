"""Conversation analysis worker — analyzes conversations using Llama 3.3 70B."""
import logging
import uuid

from src.ai.analyzer import analyze_conversation as analyze_conversation_ai
from src.ai.analyzer import MIN_CONFIDENCE_THRESHOLD
from src.config import settings
from src.models.conversation import Conversation, ConversationAnalysis
from src.models.recording import RecordingStatus
from src.models.transcript import TranscriptSegment
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


def _get_conversations_sync(recording_id: str) -> list[dict]:
    """Load conversations from DB."""
    with _SessionLocal() as session:
        rows = (
            session.query(Conversation)
            .filter(Conversation.recording_id == uuid.UUID(recording_id))
            .order_by(Conversation.start_time)
            .all()
        )
        return [
            {
                "id": str(row.id),
                "start_time": row.start_time,
                "end_time": row.end_time,
            }
            for row in rows
        ]


def _get_conversation_segments_sync(conversation_id: str) -> list[dict]:
    """Load transcript segments for a conversation's time range."""
    # First get the conversation's recording_id and time range
    with _SessionLocal() as session:
        conv = session.query(Conversation).filter(
            Conversation.id == uuid.UUID(conversation_id)
        ).first()
        if not conv:
            return []

        recording_id = conv.recording_id
        start_time = conv.start_time
        end_time = conv.end_time

        # Get transcript segments within this time range
        rows = (
            session.query(TranscriptSegment)
            .filter(
                TranscriptSegment.recording_id == recording_id,
                TranscriptSegment.start_time >= start_time,  # no lower buffer to avoid overlap
                TranscriptSegment.end_time <= end_time + 1.0,
            )
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


def _store_analysis_sync(conversation_id: str, analysis: dict):
    """Store analysis result in the database."""
    with _SessionLocal() as session:
        # Check if analysis already exists
        existing = session.query(ConversationAnalysis).filter(
            ConversationAnalysis.conversation_id == uuid.UUID(conversation_id)
        ).first()

        if existing:
            # Update existing
            existing.intent = analysis.get("intent")
            existing.customer_expectation = analysis.get("customer_expectation")
            existing.products = analysis.get("products", [])
            existing.budget = analysis.get("budget")
            existing.objections = analysis.get("objections", [])
            existing.competitors = analysis.get("competitors", [])
            existing.closing_attempt = analysis.get("closing_attempt", False)
            existing.outcome = analysis.get("outcome")
            existing.loss_reason = analysis.get("loss_reason")
            existing.confidence = analysis.get("confidence")
            existing.summary = analysis.get("summary")
            existing.coaching_notes = analysis.get("coaching_notes")
        else:
            # Create new
            ca = ConversationAnalysis(
                conversation_id=uuid.UUID(conversation_id),
                intent=analysis.get("intent"),
                customer_expectation=analysis.get("customer_expectation"),
                products=analysis.get("products", []),
                budget=analysis.get("budget"),
                objections=analysis.get("objections", []),
                competitors=analysis.get("competitors", []),
                closing_attempt=analysis.get("closing_attempt", False),
                outcome=analysis.get("outcome"),
                loss_reason=analysis.get("loss_reason"),
                confidence=analysis.get("confidence"),
                summary=analysis.get("summary"),
                coaching_notes=analysis.get("coaching_notes"),
            )
            session.add(ca)

        session.commit()
        logger.info("[%s] Stored conversation analysis", conversation_id)


def _update_conversation_summary_sync(conversation_id: str, summary: str):
    """Update the conversation's summary field."""
    with _SessionLocal() as session:
        session.query(Conversation).filter(
            Conversation.id == uuid.UUID(conversation_id)
        ).update({"summary": summary})
        session.commit()


from src.workers.retry import pipeline_retry


@pipeline_retry
def analyze_conversations(recording_id: str) -> str:
    """Analyze all conversations in a recording using Llama 3.3 70B.

    For each conversation:
    1. Load transcript segments within the conversation's time range
    2. Send to LLM for analysis (intent, products, objections, outcome, etc.)
    3. Store analysis in conversation_analysis table
    4. Update conversation summary

    Returns:
        recording_id for the next pipeline stage
    """
    logger.info("[%s] Starting conversation analysis", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.ANALYZING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Load all conversations
        conversations = _get_conversations_sync(recording_id)
        if not conversations:
            logger.warning("[%s] No conversations found — skipping analysis", recording_id)
            return recording_id

        logger.info("[%s] Analyzing %d conversations", recording_id, len(conversations))

        analyzed_count = 0
        failed_count = 0

        for conv in conversations:
            conv_id = conv["id"]
            logger.info(
                "[%s] Analyzing conversation %s (%.1fs - %.1fs)",
                recording_id,
                conv_id,
                conv["start_time"],
                conv["end_time"],
            )

            # Get transcript segments for this conversation
            segments = _get_conversation_segments_sync(conv_id)
            if not segments:
                logger.warning("[%s] No segments for conversation %s", recording_id, conv_id)
                failed_count += 1
                continue

            # Analyze conversation
            analysis = analyze_conversation_ai(segments)
            if analysis is None:
                logger.warning("[%s] Analysis failed for conversation %s", recording_id, conv_id)
                failed_count += 1
                continue

            # Check confidence threshold before storing
            if analysis.get("confidence", 0) < MIN_CONFIDENCE_THRESHOLD:
                logger.warning(
                    "[%s] Analysis confidence %d%% below threshold %d%% — skipping",
                    recording_id,
                    analysis.get("confidence"),
                    MIN_CONFIDENCE_THRESHOLD,
                )
                failed_count += 1
                continue

            # Store analysis
            _store_analysis_sync(conv_id, analysis)

            # Update conversation summary
            summary = analysis.get("summary", "")
            if summary:
                _update_conversation_summary_sync(conv_id, summary)

            analyzed_count += 1
            logger.info(
                "[%s] Conversation %s: outcome=%s, confidence=%d",
                recording_id,
                conv_id,
                analysis.get("outcome"),
                analysis.get("confidence"),
            )

        logger.info(
            "[%s] Analysis complete: %d analyzed, %d failed out of %d",
            recording_id,
            analyzed_count,
            failed_count,
            len(conversations),
        )
        
        # Mark stage complete in pipeline_state
        from src.services.pipeline_state import mark_stage_complete_sync
        mark_stage_complete_sync(recording_id, "analyze")

        return recording_id

    except Exception as exc:
        logger.error("[%s] Analysis failed: %s", recording_id, exc, exc_info=True)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        
        # Mark stage failed in pipeline_state
        from src.services.pipeline_state import mark_stage_failed_sync
        mark_stage_failed_sync(recording_id, "analyze", str(exc))
        raise
