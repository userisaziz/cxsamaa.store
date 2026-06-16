from datetime import datetime
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from src.api.deps import require_authenticated, require_brand_admin_up, require_operator_up, require_salesperson_up
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
    PresignedUploadRequest,
    PresignedUploadResponse,
    ConfirmUploadRequest,
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
from src.services.upload import (
    generate_presigned_upload_url,
    confirm_upload,
)
from src.storage.local import get_storage

router = APIRouter(prefix="/recordings", tags=["Recordings"])
logger = logging.getLogger(__name__)


@router.get('', response_model=PaginatedRecordingsResponse)
async def list_recordings_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    salesperson_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_authenticated),
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
    """Legacy endpoint: Upload via server proxy (kept for backwards compatibility).
    
    For large files, use /presign-upload instead for direct-to-R2 upload.
    """
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


@router.post("/presign-upload", response_model=PresignedUploadResponse, status_code=status.HTTP_201_CREATED)
async def presign_upload_endpoint(
    body: PresignedUploadRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    """Generate a pre-signed URL for direct browser-to-R2 upload.
    
    This bypasses the API server, allowing large files (5TB max) to upload
    directly to Cloudflare R2 without consuming server memory or bandwidth.
    
    Flow:
    1. Frontend calls this endpoint to get upload_url + recording_id
    2. Frontend PUTs file directly to upload_url (R2)
    3. Frontend calls /confirm-upload with recording_id
    """
    try:
        result = await generate_presigned_upload_url(
            db=db,
            filename=body.filename,
            content_type=body.content_type,
            salesperson_id=body.salesperson_id,
            recorded_at=body.recorded_at,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{recording_id}/confirm-upload", response_model=RecordingResponse)
async def confirm_upload_endpoint(
    recording_id: str,
    body: ConfirmUploadRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    """Confirm a direct-to-R2 upload and start the processing pipeline.
    
    Called by the frontend after successfully uploading a file directly to R2
    using a pre-signed URL.
    """
    try:
        result = await confirm_upload(
            db=db,
            recording_id=recording_id,
            file_size=body.file_size,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{recording_id}/start-pipeline", response_model=RecordingResponse)
async def start_pipeline_endpoint(
    recording_id: str,
    force_rerun: bool = Query(False, description="Force re-run all stages even if completed"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator_up),
):
    """Manually start or resume pipeline processing for a recording.
    
    Supports:
    - Starting processing for UPLOADED recordings (Upload Now, Process Later)
    - Resuming from failed stage
    - Force re-running entire pipeline (force_rerun=True)
    """
    from sqlalchemy import select
    from src.models.recording import Recording, RecordingStatus
    from src.config import settings
    
    # Get recording
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
    
    # Validate recording status for pipeline start
    # Allow starting from: UPLOADED, FAILED, or any processing state (for recovery)
    block_start_statuses = [
        RecordingStatus.PENDING_UPLOAD,  # Must complete upload first
    ]
    
    if recording.status == RecordingStatus.COMPLETED and not force_rerun:
        raise HTTPException(
            status_code=400,
            detail="Recording already completed. Use force_rerun=True to reprocess.",
        )
    
    if recording.status in block_start_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start pipeline for recording in {recording.status.value} status. "
                   f"Complete the upload first.",
        )
    
    # Reset any non-terminal status to UPLOADED before starting pipeline
    # This handles recovery from stuck intermediate states (PREPROCESSING, TRANSCRIBING, etc.)
    processing_statuses = [
        RecordingStatus.PREPROCESSING,
        RecordingStatus.TRANSCRIBING,
        RecordingStatus.DIARIZING,
        RecordingStatus.RECONCILING,
        RecordingStatus.SEGMENTING,
        RecordingStatus.STITCHING,
        RecordingStatus.ANALYZING,
        RecordingStatus.SCORING,
    ]
    
    if recording.status == RecordingStatus.FAILED or recording.status in processing_statuses:
        recording.status = RecordingStatus.UPLOADED
        recording.error_message = None
        await db.flush()
    
    # Update state to indicate pipeline starting
    from src.services.pipeline_state import update_state
    await update_state(db, recording_id, {
        "current_stage": "QUEUED",
        "last_updated_by": str(user.id)
    })
    
    # Start pipeline (dev: run directly, prod: enqueue via Cloud Tasks)
    try:
        if settings.app_env == "development":
            from src.workers.pipeline import run_stage
            import threading
            thread = threading.Thread(
                target=run_stage,
                args=(recording_id, settings.pipeline_version, 0, force_rerun),
                daemon=True,
            )
            thread.start()
        else:
            from src.workers.pipeline import enqueue_first_stage
            enqueue_first_stage(recording_id, settings.pipeline_version)
    except Exception as e:
        # Rollback status change if pipeline start fails
        recording.status = RecordingStatus.FAILED
        recording.error_message = f"Failed to start pipeline: {str(e)}"
        await db.flush()
        
        logger.error(
            "Failed to start pipeline for recording %s: %s",
            recording_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start pipeline: {str(e)}",
        )
    
    return recording


@router.post("/{recording_id}/resume-pipeline", response_model=dict)
async def resume_pipeline_from_stage(
    recording_id: str,
    body: dict = {"from_stage": "preprocess"},
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator_up),
):
    """Resume pipeline from a specific stage.
    
    Resets the specified stage and all downstream stages,
    then restarts processing from that stage.
    
    Request body:
    - from_stage: Stage name to resume from (e.g., "stt", "diarization")
    """
    from sqlalchemy import select
    from src.models.recording import Recording, RecordingStatus
    from src.config import settings
    from src.services.pipeline_state import STAGE_ORDER, reset_stage_and_downstream
    
    # Get recording
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
    
    from_stage = body.get("from_stage")
    if not from_stage or from_stage not in STAGE_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {from_stage}. Must be one of: {STAGE_ORDER}",
        )
    
    if recording.status not in [RecordingStatus.FAILED, RecordingStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Can only resume FAILED or COMPLETED recordings",
        )
    
    # Reset stage and downstream
    new_state = await reset_stage_and_downstream(db, recording_id, from_stage, updated_by=str(user.id))
    
    # Calculate stage index
    stage_index = STAGE_ORDER.index(from_stage)
    
    # Start pipeline (dev: Celery, prod: Cloud Tasks)
    if settings.app_env == "development":
        from src.workers.pipeline_worker import execute_stage
        execute_stage.delay(recording_id, settings.pipeline_version, stage_index, False)
        logger.info("[%s] Enqueued resume from stage %d via Celery", recording_id, stage_index)
    else:
        from src.workers.pipeline import enqueue_next_stage_cloud_tasks
        stage_path = f"/stage/{from_stage}"
        enqueue_next_stage_cloud_tasks(recording_id, settings.pipeline_version, stage_path)
        logger.info("[%s] Enqueued resume from stage via Cloud Tasks: %s", recording_id, stage_path)
    
    return {
        "status": "ok",
        "message": f"Resuming from stage '{from_stage}' (index {stage_index})",
        "pipeline_state": new_state,
    }


@router.post("/{recording_id}/retry-failed-stage", response_model=dict)
async def retry_failed_stage(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator_up),
):
    """Smart retry: Auto-detect failed/stuck stage and resume from there.
    
    This endpoint:
    1. Reads pipeline_state to find the failed_stage or current_stage
    2. Resets that stage (not downstream stages)
    3. Restarts processing from that stage
    
    Use this when:
    - Pipeline failed at a specific stage
    - Pipeline got stuck and needs to be restarted from current stage
    - Worker crashed mid-stage and needs retry
    """
    from sqlalchemy import select
    from src.models.recording import Recording, RecordingStatus
    from src.config import settings
    from src.services.pipeline_state import STAGE_ORDER, mark_stage_complete_sync
    
    # Get recording
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
    
    # Extract failed stage from pipeline_state
    pipeline_state = recording.pipeline_state or {}
    failed_stage = pipeline_state.get("failed_stage")
    current_stage = pipeline_state.get("current_stage")
    
    # Determine which stage to retry
    retry_stage = failed_stage or current_stage
    
    if not retry_stage or retry_stage not in STAGE_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot determine failed stage. pipeline_state: {pipeline_state}",
        )
    
    # Calculate stage index
    stage_index = STAGE_ORDER.index(retry_stage)
    
    # Reset only the failed stage (not downstream)
    # We do this by clearing the stage from completed_stages if it's there
    if retry_stage in pipeline_state.get("completed_stages", []):
        pipeline_state["completed_stages"].remove(retry_stage)
    if retry_stage in pipeline_state.get("stage_timestamps", {}):
        del pipeline_state["stage_timestamps"][retry_stage]
    
    pipeline_state["failed_stage"] = None
    pipeline_state["error_message"] = None
    recording.pipeline_state = pipeline_state
    recording.status = RecordingStatus.UPLOADED  # Reset to allow pipeline start
    recording.error_message = None
    await db.flush()
    
    logger.info(
        "[%s] Retrying failed stage '%s' (index %d)",
        recording_id, retry_stage, stage_index,
    )
    
    # Start pipeline (dev: Celery, prod: Cloud Tasks)
    if settings.app_env == "development":
        from src.workers.pipeline_worker import execute_stage
        execute_stage.delay(recording_id, settings.pipeline_version, stage_index, False)
        logger.info("[%s] Enqueued retry from stage %d via Celery", recording_id, stage_index)
    else:
        from src.workers.pipeline import enqueue_next_stage_cloud_tasks
        stage_path = f"/stage/{retry_stage}"
        enqueue_next_stage_cloud_tasks(recording_id, settings.pipeline_version, stage_path)
        logger.info("[%s] Enqueued retry from stage via Cloud Tasks: %s", recording_id, stage_path)
    
    return {
        "status": "ok",
        "message": f"Retrying stage '{retry_stage}' (index {stage_index})",
        "failed_stage": retry_stage,
        "pipeline_state": pipeline_state,
    }


@router.delete("/{recording_id}/cancel-pipeline", response_model=dict)
async def cancel_pipeline(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator_up),
):
    """Cancel active pipeline processing.
    
    Marks recording as FAILED with 'Cancelled by user' message.
    Stops further stage execution.
    """
    from sqlalchemy import select
    from src.models.recording import Recording, RecordingStatus
    from src.services.pipeline_state import update_state
    
    # Get recording
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
    
    if recording.status in [RecordingStatus.COMPLETED, RecordingStatus.FAILED, RecordingStatus.UPLOADED]:
        raise HTTPException(
            status_code=400,
            detail="Can only cancel actively processing recordings",
        )
    
    # Update status and pipeline state
    recording.status = RecordingStatus.FAILED
    recording.error_message = f"Pipeline cancelled by user {user.id}"
    
    await update_state(db, recording_id, {
        "current_stage": "CANCELLED",
        "failed_stage": recording.pipeline_state.get("current_stage"),
        "error_message": f"Cancelled by {user.id}",
        "last_updated_by": str(user.id),
    })
    
    await db.flush()
    await db.refresh(recording)
    
    return {
        "status": "ok",
        "message": "Pipeline cancelled",
        "recording_id": recording_id,
    }


@router.delete("/{recording_id}", response_model=dict)
async def delete_recording(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator_up),
):
    """Delete a recording (and optionally its file from storage).
    
    Use this to clean up:
    - PENDING_UPLOAD recordings (dangling, no file)
    - FAILED recordings (processing errors)
    - COMPLETED recordings (if needed)
    
    This removes the recording from the database and deletes the file from R2/local storage.
    """
    from sqlalchemy import select
    from src.models.recording import Recording, RecordingStatus
    
    # Get recording
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
    
    # Delete file from storage if it exists
    if recording.file_url and recording.status != RecordingStatus.PENDING_UPLOAD:
        try:
            storage = get_storage()
            await storage.delete(recording.file_url)
        except Exception as e:
            # Log but don't fail - recording should still be deleted from DB
            from src.config import logger
            logger.warning("Failed to delete file %s from storage: %s", recording.file_url, e)
    
    # Delete from database
    await db.delete(recording)
    await db.flush()
    
    return {
        "status": "ok",
        "message": f"Recording {recording_id} deleted",
        "recording_id": recording_id,
        "file_deleted": recording.file_url is not None and recording.status != RecordingStatus.PENDING_UPLOAD,
    }


@router.post("/{recording_id}/re-upload", response_model=dict)
async def reupload_recording(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator_up),
):
    """Generate a new presigned upload URL for a PENDING_UPLOAD or FAILED recording.
    
    Use this to retry an upload that failed or was interrupted.
    The recording stays in PENDING_UPLOAD status until confirm-upload is called.
    
    Returns:
    - upload_url: Pre-signed PUT URL for direct browser-to-R2 upload
    - file_key: Storage key in R2
    - recording_id: Same recording ID (reused)
    """
    from sqlalchemy import select
    from src.models.recording import Recording, RecordingStatus
    
    # Get recording
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
    
    # Only allow re-upload for PENDING_UPLOAD or FAILED
    if recording.status not in [RecordingStatus.PENDING_UPLOAD, RecordingStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail="Can only re-upload PENDING_UPLOAD or FAILED recordings",
        )
    
    # Generate new presigned upload URL for the same file_key
    storage = get_storage()
    upload_url = await storage.generate_presigned_upload_url(
        key=recording.file_url,
        content_type=recording.format,
        expires_in=3600,  # 1 hour
    )
    
    # Reset status to PENDING_UPLOAD if it was FAILED
    if recording.status == RecordingStatus.FAILED:
        recording.status = RecordingStatus.PENDING_UPLOAD
        recording.error_message = None
        await db.flush()
    
    return {
        "upload_url": upload_url,
        "recording_id": str(recording_id),
        "file_key": recording.file_url,
        "message": "Upload URL generated. Use PUT to upload file, then call /confirm-upload.",
    }


@router.get("/{recording_id}/pipeline-state", response_model=dict)
async def get_pipeline_state_endpoint(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    """Get detailed pipeline state for a recording.
    
    Returns:
    - current_stage: Current processing stage
    - completed_stages: List of completed stage names
    - failed_stage: Which stage failed (if any)
    - error_message: Error details (if failed)
    - stage_timestamps: When each stage completed
    - retry_count: How many times each stage has been retried
    """
    from src.services.pipeline_state import get_state
    
    try:
        state = await get_state(db, recording_id)
        return state
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/pipeline/active", response_model=list[dict])
async def get_active_pipeline_recordings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    """Get all recordings currently in the pipeline with progress info.
    
    Enhanced to include pipeline_state information for granular visibility.
    """
    from src.models.recording import Recording, RecordingStatus
    from sqlalchemy import select
    
    # Get all non-completed, non-failed recordings
    active_statuses = [
        RecordingStatus.PENDING_UPLOAD,
        RecordingStatus.UPLOADED,
        RecordingStatus.PREPROCESSING,
        RecordingStatus.TRANSCRIBING,
        RecordingStatus.DIARIZING,
        RecordingStatus.RECONCILING,
        RecordingStatus.SEGMENTING,
        RecordingStatus.STITCHING,
        RecordingStatus.ANALYZING,
        RecordingStatus.SCORING,
        RecordingStatus.FAILED,  # Include failed for retry visibility
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
            # Pipeline state info
            "pipeline_state": r.pipeline_state,
            "current_stage": r.pipeline_state.get("current_stage"),
            "completed_stages": r.pipeline_state.get("completed_stages", []),
            "failed_stage": r.pipeline_state.get("failed_stage"),
            "error_message": r.pipeline_state.get("error_message"),
            "completed_stages_count": len(r.pipeline_state.get("completed_stages", [])),
            "total_stages": 9,
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
