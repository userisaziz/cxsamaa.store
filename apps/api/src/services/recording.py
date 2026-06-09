import math
import uuid
from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.conversation import Conversation, ConversationAnalysis
from src.models.recording import Recording, RecordingStatus
from src.models.transcript import TranscriptSegment
from src.schemas.recording import RecordingResponse, RecordingSummaryResponse


async def list_recordings(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    salesperson_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """List recordings with pagination and optional filters."""
    query = select(Recording)
    count_query = select(func.count(Recording.id))

    if status:
        query = query.where(Recording.status == RecordingStatus(status))
        count_query = count_query.where(Recording.status == RecordingStatus(status))
    if salesperson_id:
        query = query.where(Recording.salesperson_id == uuid.UUID(salesperson_id))
        count_query = count_query.where(Recording.salesperson_id == uuid.UUID(salesperson_id))
    if date_from:
        query = query.where(Recording.recorded_at >= date_from)
        count_query = count_query.where(Recording.recorded_at >= date_from)
    if date_to:
        query = query.where(Recording.recorded_at <= date_to)
        count_query = count_query.where(Recording.recorded_at <= date_to)

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    # Paginated results
    query = query.order_by(Recording.uploaded_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def get_recording(db: AsyncSession, recording_id: str) -> Recording | None:
    result = await db.execute(
        select(Recording).where(Recording.id == uuid.UUID(recording_id))
    )
    return result.scalar_one_or_none()


async def create_recording(
    db: AsyncSession,
    salesperson_id: str,
    file_url: str,
    file_size: int,
    duration_seconds: int | None,
    format: str,
    recorded_at: datetime | None = None,
) -> Recording:
    recording = Recording(
        salesperson_id=uuid.UUID(salesperson_id),
        file_url=file_url,
        file_size=file_size,
        duration_seconds=duration_seconds,
        format=format,
        status=RecordingStatus.UPLOADED,
        recorded_at=recorded_at,
    )
    db.add(recording)
    await db.flush()
    await db.refresh(recording)
    return recording


async def update_recording_status(
    db: AsyncSession, recording_id: str, status: RecordingStatus, error_message: str | None = None
) -> Recording | None:
    recording = await get_recording(db, recording_id)
    if not recording:
        return None
    recording.status = status
    if error_message:
        recording.error_message = error_message
    await db.flush()
    await db.refresh(recording)
    return recording


async def get_transcript(db: AsyncSession, recording_id: str) -> list[TranscriptSegment]:
    result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.recording_id == uuid.UUID(recording_id))
        .order_by(TranscriptSegment.start_time)
    )
    return list(result.scalars().all())


async def get_conversations(db: AsyncSession, recording_id: str) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.recording_id == uuid.UUID(recording_id))
        .order_by(Conversation.start_time)
    )
    return list(result.scalars().all())


async def get_recording_summary(db: AsyncSession, recording_id: str) -> RecordingSummaryResponse:
    """Build a recording-level summary from all conversation analyses."""
    recording = await get_recording(db, recording_id)
    if not recording:
        raise ValueError("Recording not found")

    # Load conversations with analysis
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.analysis))
        .where(Conversation.recording_id == uuid.UUID(recording_id))
        .order_by(Conversation.start_time)
    )
    conversations = list(result.scalars().all())

    total_conversations = len(conversations)
    intents: list[str] = []
    objections: list[str] = []
    outcomes: Counter = Counter()
    confidences: list[int] = []
    missed = 0

    for conv in conversations:
        if conv.analysis:
            a = conv.analysis
            if a.intent:
                intents.append(a.intent)
            if a.objections:
                objections.extend(a.objections)
            if a.outcome:
                outcomes[a.outcome] += 1
                if a.outcome == "LOST":
                    missed += 1
            if a.confidence:
                confidences.append(a.confidence)

    # Top intent and objection
    top_intent = Counter(intents).most_common(1)[0][0] if intents else None
    top_objection = Counter(objections).most_common(1)[0][0] if objections else None
    avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else None

    return RecordingSummaryResponse(
        id=str(recording.id),
        status=recording.status.value,
        duration_seconds=recording.duration_seconds,
        total_conversations=total_conversations,
        top_intent=top_intent,
        top_objection=top_objection,
        missed_opportunities=missed,
        outcomes=dict(outcomes),
        avg_confidence=avg_confidence,
    )
