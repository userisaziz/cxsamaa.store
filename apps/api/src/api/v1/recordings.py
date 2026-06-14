from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from src.api.deps import require_brand_admin_up, require_operator_up, require_salesperson_up
from src.database import get_db
from src.models.user import User
from src.schemas.recording import (
    PaginatedRecordingsResponse,
    RecordingResponse,
    RecordingStatusResponse,
    RecordingSummaryResponse,
    SpeakerRoleCorrectionRequest,
    SpeakerRolesResponse,
    TranscriptSegmentResponse,
)
from src.schemas.conversation import ConversationResponse
from src.services.recording import (
    get_recording,
    get_recording_status,
    get_recording_summary,
    get_recording_transcript,
    get_enriched_transcript,
    correct_speaker_role,
    get_speaker_roles_summary,
    get_recording_conversations,
    list_recordings,
    reprocess_recording,
    upload_recording,
)
from src.storage.local import get_storage

router = APIRouter(prefix="/recordings", tags=["Recordings"])


@router.get('', response_model=PaginatedRecordingsResponse)
async def list_recordings_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    salesperson_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    date_from_dt = None
    date_to_dt = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO 8601.")
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO 8601.")

    return await list_recordings(
        db,
        page=page,
        page_size=page_size,
        status=status,
        salesperson_id=salesperson_id,
        date_from=date_from_dt,
        date_to=date_to_dt,
    )


@router.post("/upload", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED)
async def upload_recording_endpoint(
    file: UploadFile = File(...),
    salesperson_id: str = Form(...),
    recorded_at: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    recorded_at_dt = None
    if recorded_at:
        try:
            recorded_at_dt = datetime.fromisoformat(recorded_at)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid recorded_at format. Use ISO 8601 (e.g. 2025-06-09T14:30:00).",
            )

    try:
        result = await upload_recording(
            db=db,
            file=file,
            salesperson_id=salesperson_id,
            recorded_at=recorded_at_dt,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pipeline/active", response_model=list[dict])
async def get_active_pipeline_recordings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    """Get all recordings currently in the pipeline with progress info."""
    from src.models.recording import Recording, RecordingStatus
    from sqlalchemy import select
    
    active_statuses = [
        RecordingStatus.PREPROCESSING,
        RecordingStatus.TRANSCRIBING,
        RecordingStatus.DIARIZING,
        RecordingStatus.RECONCILING,
        RecordingStatus.SEGMENTING,
        RecordingStatus.STITCHING,
        RecordingStatus.ANALYZING,
        RecordingStatus.SCORING,
    ]
    
    result = await db.execute(
        select(Recording)
        .where(Recording.status.in_(active_statuses))
        .order_by(Recording.uploaded_at.desc())
    )
    recordings = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "status": r.status.value,
            "duration_seconds": r.duration_seconds,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
            "file_url": r.file_url,
            "salesperson_id": str(r.salesperson_id),
        }
        for r in recordings
    ]


@router.get("/{recording_id}/audio")
async def stream_recording_audio(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    recording = await get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    storage = get_storage()

    # For local storage, serve file directly
    if hasattr(storage, "base_dir"):
        file_path = storage.base_dir / recording.file_url
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        return FileResponse(
            path=str(file_path),
            media_type=recording.format,
            headers={"Accept-Ranges": "bytes"},
        )

    # For R2/cloud storage, redirect to signed URL
    try:
        signed_url = await storage.get_signed_url(recording.file_url, expires_in=900)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=signed_url, status_code=302)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Audio file not found: {e}")


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording_endpoint(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    recording = await get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording


@router.get("/{recording_id}/status", response_model=RecordingStatusResponse)
async def get_recording_status_endpoint(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    status_result = await get_recording_status(db, recording_id)
    if not status_result:
        raise HTTPException(status_code=404, detail="Recording not found")
    return status_result


@router.get("/{recording_id}/transcript", response_model=list[TranscriptSegmentResponse])
async def get_recording_transcript_endpoint(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    segments = await get_enriched_transcript(db, recording_id)
    if segments is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return segments


@router.patch("/{recording_id}/speaker-role")
async def correct_speaker_role_endpoint(
    recording_id: str,
    body: SpeakerRoleCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    """Manually correct a speaker's role classification.

    Updates the speaker_roles record and all related conversation_turns
    with the corrected role. Sets classification_method to 'Manual'.
    """
    try:
        updated = await correct_speaker_role(
            db,
            recording_id,
            body.speaker_label,
            body.corrected_role,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Recording not found")

    return {"status": "ok", "speaker_label": body.speaker_label, "role": body.corrected_role}


@router.get("/{recording_id}/speaker-roles", response_model=SpeakerRolesResponse)
async def get_speaker_roles_endpoint(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    """Get speaker role classification summary for a recording.

    Returns per-speaker role details, classification methods,
    and manual correction count.
    """
    result = await get_speaker_roles_summary(db, recording_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return result


@router.get("/{recording_id}/conversations", response_model=list[ConversationResponse])
async def get_recording_conversations_endpoint(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    conversations = await get_recording_conversations(db, recording_id)
    if conversations is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return conversations


@router.get("/{recording_id}/summary", response_model=RecordingSummaryResponse)
async def get_recording_summary_endpoint(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    summary = await get_recording_summary(db, recording_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return summary


@router.post("/{recording_id}/reprocess", response_model=RecordingResponse)
async def reprocess_recording_endpoint(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_brand_admin_up),
):
    recording = await get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    try:
        result = await reprocess_recording(db, recording)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
