import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_salesperson_up
from src.database import get_db
from src.models.recording import RecordingStatus
from src.models.user import User
from src.schemas.recording import (
    ConversationSummaryResponse,
    PaginatedRecordingsResponse,
    RecordingResponse,
    RecordingStatusResponse,
    RecordingSummaryResponse,
    TranscriptSegmentResponse,
)
from src.services.recording import (
    create_recording,
    get_conversations,
    get_recording,
    get_recording_summary,
    get_transcript,
    list_recordings,
)
from src.services.export import export_recordings_csv, export_conversations_csv
from src.storage.local import get_storage
from src.workers.pipeline import start_processing_pipeline

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = {"wav", "mp3", "m4a"}
ALLOWED_MIME_TYPES = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/mp3"}

router = APIRouter(prefix="/recordings", tags=["Recordings"])


@router.get("", response_model=PaginatedRecordingsResponse)
async def list_recordings_endpoint(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    salesperson_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO 8601 (e.g. 2025-01-15)")
    if date_to:
        try:
            parsed_date_to = datetime.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO 8601 (e.g. 2025-01-15)")

    return await list_recordings(
        db,
        page=page,
        page_size=page_size,
        status=status,
        salesperson_id=salesperson_id,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
    )


@router.get("/export/recordings")
async def export_recordings(
    salesperson_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    """Export recordings as CSV."""
    csv_data = await export_recordings_csv(db, salesperson_id=salesperson_id, status=status_filter)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=recordings.csv"},
    )


@router.get("/export/conversations")
async def export_conversations(
    recording_id: str | None = None,
    salesperson_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    """Export conversation analyses as CSV."""
    csv_data = await export_conversations_csv(
        db, recording_id=recording_id, salesperson_id=salesperson_id
    )
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=conversations.csv"},
    )


@router.post("/upload", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED)
async def upload_recording(
    file: UploadFile = File(...),
    salesperson_id: str = Form(...),
    recorded_at: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    # Validate file format
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Allowed: {', '.join(ALLOWED_FORMATS)}",
        )

    # Parse recorded_at if provided
    parsed_recorded_at = None
    if recorded_at:
        try:
            parsed_recorded_at = datetime.fromisoformat(recorded_at)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid recorded_at format. Use ISO 8601 (e.g. 2025-01-15T10:30:00)",
            )

    # Read file
    file_data = await file.read()
    file_size = len(file_data)

    # Store file
    storage = get_storage()
    file_key = f"recordings/{uuid.uuid4()}/{file.filename}"
    file_url = await storage.upload(file_data, file_key)

    # Create recording record
    recording = await create_recording(
        db=db,
        salesperson_id=salesperson_id,
        file_url=file_url,
        file_size=file_size,
        duration_seconds=None,  # Will be determined during preprocessing
        format=ext.upper(),
        recorded_at=parsed_recorded_at,
    )

    # Enqueue Celery processing pipeline
    try:
        start_processing_pipeline(str(recording.id))
    except Exception as e:
        # If Redis/Celery is unavailable, recording stays in UPLOADED status
        logger.warning(f"Could not enqueue pipeline: {e}")

    return recording


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording_detail(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    recording = await get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording


@router.get("/{recording_id}/status", response_model=RecordingStatusResponse)
async def get_recording_status(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    recording = await get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return RecordingStatusResponse(
        id=str(recording.id),
        status=recording.status.value,
        error_message=recording.error_message,
    )


@router.get("/{recording_id}/transcript", response_model=list[TranscriptSegmentResponse])
async def get_recording_transcript(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    return await get_transcript(db, recording_id)


@router.get("/{recording_id}/conversations", response_model=list[ConversationSummaryResponse])
async def get_recording_conversations(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    return await get_conversations(db, recording_id)


@router.get("/{recording_id}/summary", response_model=RecordingSummaryResponse)
async def get_recording_summary(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    recording = await get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return await get_recording_summary(db, recording_id)


@router.post("/{recording_id}/reprocess", response_model=RecordingResponse)
async def reprocess_recording(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    """Re-trigger the processing pipeline for a failed or stale recording."""
    recording = await get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if recording.status == RecordingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Recording already completed")

    # Reset status to UPLOADED to re-trigger pipeline
    recording.status = RecordingStatus.UPLOADED
    recording.error_message = None
    await db.flush()

    try:
        start_processing_pipeline(str(recording.id))
    except Exception as e:
        logger.warning(f"Could not enqueue pipeline for reprocess: {e}")

    await db.refresh(recording)
    return recording
