from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from src.api.deps import require_brand_admin_up, require_operator_up, require_salesperson_up
from src.database import get_db
from src.models.user import User
from src.schemas.recording import PaginatedRecordingsResponse, RecordingResponse, RecordingStatusResponse
from src.services.recording import (
    get_recording,
    get_recording_status,
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
    file_path = storage.base_dir / recording.file_url
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        path=str(file_path),
        media_type=recording.format,
        headers={"Accept-Ranges": "bytes"},
    )


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
