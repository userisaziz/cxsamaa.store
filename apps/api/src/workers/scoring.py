"""Salesperson scoring worker — scores performance across 5 dimensions."""
import logging
import uuid
from datetime import datetime, timezone

from src.ai.scorer import score_salesperson_performance
from src.config import settings
from src.models.conversation import Conversation, ConversationAnalysis
from src.models.metrics import DailyMetrics
from src.models.recording import Recording, RecordingStatus
from src.models.transcript import TranscriptSegment
from src.workers.pipeline_control import PipelineHalted
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


def _get_conversations_with_segments_sync(recording_id: str) -> list[dict]:
    """Load conversations with their transcript segments."""
    with _SessionLocal() as session:
        conversations = (
            session.query(Conversation)
            .filter(Conversation.recording_id == uuid.UUID(recording_id))
            .order_by(Conversation.start_time)
            .all()
        )

        result = []
        for conv in conversations:
            segments = (
                session.query(TranscriptSegment)
                .filter(
                    TranscriptSegment.recording_id == uuid.UUID(recording_id),
                    TranscriptSegment.start_time >= conv.start_time,  # no lower buffer
                    TranscriptSegment.end_time <= conv.end_time + 1.0,
                )
                .order_by(TranscriptSegment.start_time)
                .all()
            )
            result.append({
                "conversation_id": str(conv.id),
                "segments": [
                    {
                        "start": seg.start_time,
                        "end": seg.end_time,
                        "text": seg.text,
                        "speaker": seg.speaker_label,
                    }
                    for seg in segments
                ],
            })
    return result


def _store_scores_sync(conversation_id: str, scores: dict):
    """Store scoring results in conversation_analysis.scores."""
    with _SessionLocal() as session:
        analysis = session.query(ConversationAnalysis).filter(
            ConversationAnalysis.conversation_id == uuid.UUID(conversation_id)
        ).first()

        if analysis:
            analysis.scores = scores
        else:
            # Create analysis record with just scores
            ca = ConversationAnalysis(
                conversation_id=uuid.UUID(conversation_id),
                scores=scores,
            )
            session.add(ca)

        session.commit()


def _complete_recording_sync(recording_id: str):
    """Mark recording as COMPLETED with processed_at timestamp."""
    with _SessionLocal() as session:
        recording = session.query(Recording).filter(
            Recording.id == uuid.UUID(recording_id)
        ).first()
        if recording:
            recording.status = RecordingStatus.COMPLETED
            recording.processed_at = datetime.now(timezone.utc)
            recording.error_message = None
        session.commit()


def _update_daily_metrics_sync(recording_id: str):
    """Update daily metrics for the salesperson and store after scoring."""
    with _SessionLocal() as session:
        # Get recording info
        recording = session.query(Recording).filter(
            Recording.id == uuid.UUID(recording_id)
        ).first()
        if not recording:
            return

        salesperson_id = recording.salesperson_id
        today = datetime.now(timezone.utc).date()

        # Get store_id from salesperson
        from src.models.salesperson import Salesperson
        salesperson = session.query(Salesperson).filter(
            Salesperson.id == salesperson_id
        ).first()
        if not salesperson:
            return

        store_id = salesperson.store_id

        # Compute metrics for salesperson today
        _upsert_daily_metrics(session, salesperson_id, "SALESPERSON", today)
        _upsert_daily_metrics(session, store_id, "STORE", today)

        session.commit()
    logger.info("[%s] Updated daily metrics", recording_id)


def _upsert_daily_metrics(session, entity_id, entity_type: str, date_val):
    """Insert or update daily metrics for an entity."""
    from sqlalchemy import func, cast, Date

    # Get recordings for this entity ON THE TARGET DATE
    if entity_type == "SALESPERSON":
        from src.models.recording import Recording
        recording_ids = [
            r.id for r in session.query(Recording.id).filter(
                Recording.salesperson_id == entity_id,
                cast(Recording.uploaded_at, Date) == date_val,
            ).all()
        ]
    else:
        from src.models.salesperson import Salesperson
        from src.models.recording import Recording
        sp_ids = [
            s.id for s in session.query(Salesperson.id).filter(
                Salesperson.store_id == entity_id
            ).all()
        ]
        recording_ids = [
            r.id for r in session.query(Recording.id).filter(
                Recording.salesperson_id.in_(sp_ids),
                cast(Recording.uploaded_at, Date) == date_val,
            ).all()
        ]

    if not recording_ids:
        return

    # Count conversations
    conv_count = session.query(Conversation).filter(
        Conversation.recording_id.in_(recording_ids)
    ).count()

    # Get average performance scores from the scores JSONB field
    # (not confidence, which is the AI's self-rating)
    scored_analyses = session.query(ConversationAnalysis).join(
        Conversation
    ).filter(
        Conversation.recording_id.in_(recording_ids),
        ConversationAnalysis.scores.isnot(None),
    ).all()

    dimension_avgs = []
    for a in scored_analyses:
        if isinstance(a.scores, dict):
            vals = [v for v in a.scores.values() if v is not None]
            if vals:
                dimension_avgs.append(sum(vals) / len(vals))

    avg_score = sum(dimension_avgs) / len(dimension_avgs) if dimension_avgs else None

    # Count sales
    sale_count = session.query(ConversationAnalysis).join(
        Conversation
    ).filter(
        Conversation.recording_id.in_(recording_ids),
        ConversationAnalysis.outcome == "SALE_MADE",
    ).count()

    conversion_rate = (sale_count / conv_count * 100) if conv_count > 0 else 0

    # Upsert
    existing = session.query(DailyMetrics).filter(
        DailyMetrics.entity_id == entity_id,
        DailyMetrics.entity_type == entity_type,
        DailyMetrics.date == date_val,
    ).first()

    if existing:
        existing.conversation_count = conv_count
        existing.avg_score = avg_score
        existing.conversion_rate = round(conversion_rate, 1)
    else:
        dm = DailyMetrics(
            entity_id=entity_id,
            entity_type=entity_type,
            date=date_val,
            conversation_count=conv_count,
            avg_score=avg_score,
            conversion_rate=round(conversion_rate, 1),
        )
        session.add(dm)


from src.workers.retry import pipeline_retry


@pipeline_retry
def score_salesperson(recording_id: str) -> str:
    """Score salesperson performance across 5 dimensions for each conversation.

    After scoring:
    - Stores scores in conversation_analysis.scores
    - Marks recording as COMPLETED
    - Updates daily metrics

    Returns:
        recording_id (final stage in pipeline)
    """
    logger.info("[%s] Starting salesperson scoring", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.SCORING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Load conversations with segments
        conversations = _get_conversations_with_segments_sync(recording_id)
        if not conversations:
            logger.warning("[%s] No conversations to score — pipeline may have skipped segmentation", recording_id)
            # Halt pipeline — scoring without conversations is meaningless.
            # This is a safety net: segmentation should have halted already.
            _update_recording_status_sync(
                recording_id,
                RecordingStatus.FAILED,
                "No conversations found for scoring. Segmentation may have produced 0 conversations.",
            )
            from src.services.pipeline_state import mark_stage_failed_sync
            mark_stage_failed_sync(
                recording_id,
                "scoring",
                "No conversations found for scoring. Retry from segmentation stage.",
            )
            raise PipelineHalted(
                f"No conversations to score for recording {recording_id}. "
                "Retry from segmentation stage."
            )

        logger.info("[%s] Scoring %d conversations", recording_id, len(conversations))

        all_scores = []
        scored_count = 0

        for conv in conversations:
            conv_id = conv["conversation_id"]
            segments = conv["segments"]

            if not segments:
                continue

            scores = score_salesperson_performance(segments)
            if scores is None:
                logger.warning("[%s] Scoring failed for conversation %s", recording_id, conv_id)
                continue

            _store_scores_sync(conv_id, scores)
            all_scores.append(scores)
            scored_count += 1

            logger.info(
                "[%s] Conversation %s scores: greeting=%s, discovery=%s, product=%s, objection=%s, closing=%s",
                recording_id,
                conv_id,
                scores.get("greeting_score"),
                scores.get("discovery_score"),
                scores.get("product_knowledge_score"),
                scores.get("objection_handling_score"),
                scores.get("closing_score"),
            )

        # Mark recording as completed
        _complete_recording_sync(recording_id)

        # Update daily metrics
        _update_daily_metrics_sync(recording_id)

        logger.info(
            "[%s] Scoring complete: %d/%d scored",
            recording_id,
            scored_count,
            len(conversations),
        )
        
        # Mark stage complete in pipeline_state
        from src.services.pipeline_state import mark_stage_complete_sync
        mark_stage_complete_sync(recording_id, "scoring")
        
        return recording_id

    except PipelineHalted:
        # PipelineHalted already marked recording FAILED and stage failed.
        # Re-raise so the pipeline orchestrator knows to stop.
        raise

    except Exception as exc:
        logger.error("[%s] Scoring failed: %s", recording_id, exc, exc_info=True)
        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        
        # Mark stage failed in pipeline_state
        from src.services.pipeline_state import mark_stage_failed_sync
        mark_stage_failed_sync(recording_id, "scoring", str(exc))
        raise
