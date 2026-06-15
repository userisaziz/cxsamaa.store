import math
import uuid
from collections import Counter
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.conversation import Conversation, ConversationAnalysis
from src.models.recording import Recording, RecordingStatus
from src.models.transcript import TranscriptSegment, SpeakerRole, SpeakerRoleCorrection
from src.schemas.recording import (
    RecordingResponse,
    RecordingStatusResponse,
    RecordingSummaryResponse,
    SpeakerRoleSummary,
    SpeakerRolesResponse,
)
from src.storage.local import get_storage


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
        "items": [RecordingResponse.model_validate(item) for item in items],
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


async def get_recording_status(db: AsyncSession, recording_id: str) -> RecordingStatusResponse | None:
    """Get the status of a recording."""
    recording = await get_recording(db, recording_id)
    if not recording:
        return None
    
    # Count transcript segments
    from src.models.transcript import TranscriptSegment
    from sqlalchemy import func
    segment_count = await db.scalar(
        func.count(TranscriptSegment.id).where(TranscriptSegment.recording_id == recording.id)
    ) or 0
    
    # Count conversations
    from src.models.conversation import Conversation
    conversation_count = await db.scalar(
        func.count(Conversation.id).where(Conversation.recording_id == recording.id)
    ) or 0
    
    return RecordingStatusResponse(
        id=str(recording.id),
        status=recording.status.value,
        error_message=recording.error_message,
        transcript_segment_count=segment_count,
        conversation_count=conversation_count,
    )


async def upload_recording(
    db: AsyncSession,
    file: UploadFile,
    salesperson_id: str,
    recorded_at: datetime | None = None,
) -> Recording:
    """Upload a new recording file and start processing pipeline."""
    from pathlib import Path
    
    # Validate file
    if not file.filename or not file.content_type:
        raise ValueError("Invalid file upload")
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Upload to storage
    storage = get_storage()
    file_url = await storage.upload(file_content, unique_filename)
    
    # Create recording record
    recording = Recording(
        salesperson_id=uuid.UUID(salesperson_id),
        file_url=file_url,
        file_size=file_size,
        duration_seconds=None,  # Will be updated after preprocessing
        format=file.content_type,
        status=RecordingStatus.UPLOADED,
        recorded_at=recorded_at,
    )
    db.add(recording)
    await db.flush()
    await db.refresh(recording)
    
    # Start processing pipeline
    from src.workers.pipeline import enqueue_first_stage
    from src.config import settings
    enqueue_first_stage(str(recording.id), settings.pipeline_version)
    
    return recording


async def reprocess_recording(db: AsyncSession, recording: Recording) -> Recording:
    """Reprocess a recording by restarting the pipeline."""
    # Only allow reprocessing if recording is in UPLOADED or terminal state
    if recording.status not in [
        RecordingStatus.UPLOADED,
        RecordingStatus.FAILED,
        RecordingStatus.COMPLETED,
    ]:
        raise ValueError(
            f"Cannot reprocess recording with status {recording.status.value}. "
            "Only FAILED or COMPLETED recordings can be reprocessed."
        )
    
    # Reset status
    recording.status = RecordingStatus.UPLOADED
    recording.error_message = None
    await db.flush()
    await db.refresh(recording)
    
    # Restart pipeline
    from src.workers.pipeline import enqueue_first_stage
    from src.config import settings
    enqueue_first_stage(str(recording.id), settings.pipeline_version)
    
    return recording


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


async def get_recording_transcript(db: AsyncSession, recording_id: str) -> list[TranscriptSegment] | None:
    """Get transcript segments for a recording. Returns None if recording doesn't exist."""
    recording = await get_recording(db, recording_id)
    if not recording:
        return None
    return await get_transcript(db, recording_id)


async def get_enriched_transcript(db: AsyncSession, recording_id: str) -> list[dict] | None:
    """Get transcript segments enriched with speaker role data.

    LEFT JOINs with speaker_roles to attach role_label and role_confidence
    to each transcript segment based on matching speaker_label.
    Returns None if recording doesn't exist.
    """
    recording = await get_recording(db, recording_id)
    if not recording:
        return None

    # Fetch transcript segments
    segments = await get_transcript(db, recording_id)

    # Fetch speaker roles for this recording
    role_result = await db.execute(
        select(SpeakerRole).where(
            SpeakerRole.recording_id == uuid.UUID(recording_id)
        )
    )
    speaker_roles = {
        role.speaker_label: {
            "role_label": role.role_label,
            "confidence": role.confidence,
        }
        for role in role_result.scalars().all()
    }

    # Build enriched response dicts
    enriched = []
    for seg in segments:
        role_info = speaker_roles.get(seg.speaker_label, {})
        enriched.append({
            "id": seg.id,
            "recording_id": seg.recording_id,
            "speaker_label": seg.speaker_label,
            "role_label": role_info.get("role_label"),
            "role_confidence": role_info.get("confidence"),
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "text": seg.text,
        })

    return enriched


async def correct_speaker_role(
    db: AsyncSession,
    recording_id: str,
    speaker_label: str,
    corrected_role: str,
) -> bool:
    """Manually correct a speaker's role classification.

    Updates the speaker_roles record with the corrected role,
    setting classification_method to 'Manual' and confidence to 1.0.
    Also updates all conversation_turns for this recording that
    match the speaker_label.

    Returns True if a record was updated, False if no matching record found.
    """
    if corrected_role not in ("Salesperson", "Customer"):
        raise ValueError(f"Invalid role: {corrected_role}. Must be 'Salesperson' or 'Customer'.")

    rid = uuid.UUID(recording_id)

    # Check recording exists
    recording = await get_recording(db, recording_id)
    if not recording:
        return False

    # Audit trail — log the correction
    from src.models.transcript import ConversationTurn

    # Look up original role before updating
    original_role = None
    previous_confidence = None
    existing = await db.execute(
        select(SpeakerRole).where(
            SpeakerRole.recording_id == rid,
            SpeakerRole.speaker_label == speaker_label,
        )
    )
    existing_role = existing.scalar_one_or_none()
    if existing_role:
        original_role = existing_role.role_label
        previous_confidence = existing_role.confidence

    # Update speaker_roles table
    result = await db.execute(
        update(SpeakerRole)
        .where(
            SpeakerRole.recording_id == rid,
            SpeakerRole.speaker_label == speaker_label,
        )
        .values(
            role_label=corrected_role,
            classification_method="Manual",
            confidence=1.0,
        )
    )

    if result.rowcount == 0:
        # No existing record — create one
        new_role = SpeakerRole(
            recording_id=rid,
            speaker_label=speaker_label,
            role_label=corrected_role,
            classification_method="Manual",
            confidence=1.0,
        )
        db.add(new_role)

    # Create audit record
    audit = SpeakerRoleCorrection(
        recording_id=rid,
        speaker_label=speaker_label,
        original_role=original_role,
        corrected_role=corrected_role,
        previous_confidence=previous_confidence,
        new_confidence=1.0,
    )
    db.add(audit)

    # Also update conversation_turns for this recording with matching speaker
    await db.execute(
        update(ConversationTurn)
        .where(
            ConversationTurn.recording_id == rid,
            ConversationTurn.speaker_label == speaker_label,
        )
        .values(role_label=corrected_role)
    )

    await db.commit()
    return True


async def get_speaker_roles_summary(
    db: AsyncSession,
    recording_id: str,
) -> SpeakerRolesResponse | None:
    """Get speaker role classification summary for a recording.

    Returns classification method breakdown, correction stats,
    and per-speaker role details.
    """
    recording = await get_recording(db, recording_id)
    if not recording:
        return None

    result = await db.execute(
        select(SpeakerRole)
        .where(SpeakerRole.recording_id == uuid.UUID(recording_id))
        .order_by(SpeakerRole.speaker_label)
    )
    roles = result.scalars().all()

    if not roles:
        return SpeakerRolesResponse(
            recording_id=recording_id,
            speakers=[],
            total_speakers=0,
            manually_corrected_count=0,
            primary_method=None,
        )

    speakers = []
    methods: list[str] = []
    corrected_count = 0

    for role in roles:
        is_manual = role.classification_method == "Manual"
        if is_manual:
            corrected_count += 1
        if role.classification_method:
            methods.append(role.classification_method)

        speakers.append(SpeakerRoleSummary(
            speaker_label=role.speaker_label,
            role_label=role.role_label,
            classification_method=role.classification_method,
            confidence=role.confidence,
            is_manually_corrected=is_manual,
        ))

    # Most common classification method
    primary_method = Counter(methods).most_common(1)[0][0] if methods else None

    return SpeakerRolesResponse(
        recording_id=recording_id,
        speakers=speakers,
        total_speakers=len(speakers),
        manually_corrected_count=corrected_count,
        primary_method=primary_method,
    )


async def get_conversations(db: AsyncSession, recording_id: str) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.recording_id == uuid.UUID(recording_id))
        .order_by(Conversation.start_time)
    )
    return list(result.scalars().all())


async def get_recording_conversations(db: AsyncSession, recording_id: str) -> list[Conversation] | None:
    """Get conversations for a recording. Returns None if recording doesn't exist."""
    recording = await get_recording(db, recording_id)
    if not recording:
        return None
    return await get_conversations(db, recording_id)


async def get_recording_summary(db: AsyncSession, recording_id: str) -> RecordingSummaryResponse | None:
    """Build a recording-level summary from all conversation analyses. Returns None if recording doesn't exist."""
    recording = await get_recording(db, recording_id)
    if not recording:
        return None

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
                for obj in a.objections:
                    if isinstance(obj, dict):
                        issue = obj.get("issue", "")
                        if issue:
                            objections.append(issue)
                    elif isinstance(obj, str) and obj:
                        objections.append(obj)
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
