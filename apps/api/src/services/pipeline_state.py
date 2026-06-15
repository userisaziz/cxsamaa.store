"""Pipeline state management service.

Provides centralized functions for managing pipeline state transitions
with idempotency checks for granular stage tracking and recovery.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.models.recording import Recording

logger = logging.getLogger(__name__)

# Ordered list of all pipeline stages
STAGE_ORDER = [
    "preprocess",
    "stt",
    "diarization",
    "turns",
    "roles",
    "segmentation",
    "stitch",
    "analyze",
    "scoring",
]


def create_initial_state(current_stage: str = "UPLOADED") -> dict:
    """Create a default pipeline state object."""
    return {
        "current_stage": current_stage,
        "completed_stages": [],
        "failed_stage": None,
        "error_message": None,
        "last_updated_by": "system",
        "retry_count": {},
        "stage_timestamps": {},
    }


async def get_state(db: AsyncSession, recording_id: str) -> dict:
    """Get the current pipeline state for a recording."""
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise ValueError(f"Recording {recording_id} not found")
    
    return recording.get_pipeline_state()


async def update_state(db: AsyncSession, recording_id: str, updates: dict, updated_by: str = "system") -> dict:
    """Update pipeline state with merged updates."""
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise ValueError(f"Recording {recording_id} not found")
    
    updates["last_updated_by"] = updated_by
    recording.update_pipeline_state(updates)
    await db.flush()
    await db.refresh(recording)
    
    return recording.get_pipeline_state()


async def mark_stage_complete(db: AsyncSession, recording_id: str, stage_name: str, updated_by: str = "system") -> dict:
    """Mark a pipeline stage as completed."""
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise ValueError(f"Recording {recording_id} not found")
    
    recording.mark_stage_complete(stage_name)
    recording.pipeline_state["last_updated_by"] = updated_by
    await db.flush()
    await db.refresh(recording)
    
    logger.info("[%s] Marked stage '%s' as completed", recording_id, stage_name)
    return recording.get_pipeline_state()


async def mark_stage_failed(db: AsyncSession, recording_id: str, stage_name: str, error: str, updated_by: str = "system") -> dict:
    """Mark a pipeline stage as failed."""
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise ValueError(f"Recording {recording_id} not found")
    
    recording.mark_stage_failed(stage_name, error)
    recording.pipeline_state["last_updated_by"] = updated_by
    
    # Increment retry count for this stage
    retry_count = recording.pipeline_state.get("retry_count", {})
    retry_count[stage_name] = retry_count.get(stage_name, 0) + 1
    recording.pipeline_state["retry_count"] = retry_count
    
    await db.flush()
    await db.refresh(recording)
    
    logger.error("[%s] Stage '%s' failed: %s", recording_id, stage_name, error)
    return recording.get_pipeline_state()


async def can_skip_stage(db: AsyncSession, stage_name: str, recording_id: str) -> bool:
    """Check if a stage can be skipped (already completed)."""
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise ValueError(f"Recording {recording_id} not found")
    
    return recording.is_stage_completed(stage_name)


async def reset_stage_and_downstream(db: AsyncSession, recording_id: str, from_stage: str, updated_by: str = "system") -> dict:
    """Reset a stage and all downstream stages from completed_stages.
    
    Used when restarting from a specific stage - clears that stage
    and all subsequent stages so they will be re-executed.
    """
    stmt = select(Recording).where(Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    
    if not recording:
        raise ValueError(f"Recording {recording_id} not found")
    
    if from_stage not in STAGE_ORDER:
        raise ValueError(f"Invalid stage '{from_stage}'. Must be one of {STAGE_ORDER}")
    
    state = recording.get_pipeline_state()
    completed = state.get("completed_stages", [])
    
    # Find the index of the stage to reset from
    from_index = STAGE_ORDER.index(from_stage)
    
    # Keep only stages before the reset point
    stages_to_keep = STAGE_ORDER[:from_index]
    new_completed = [s for s in completed if s in stages_to_keep]
    
    # Remove timestamps for reset stages
    timestamps = state.get("stage_timestamps", {})
    for stage in STAGE_ORDER[from_index:]:
        timestamps.pop(stage, None)
    
    # Update state
    state["completed_stages"] = new_completed
    state["stage_timestamps"] = timestamps
    state["current_stage"] = from_stage
    state["failed_stage"] = None
    state["error_message"] = None
    state["last_updated_by"] = updated_by
    
    recording.pipeline_state = state
    await db.flush()
    await db.refresh(recording)
    
    logger.info(
        "[%s] Reset stage '%s' and all downstream stages. Remaining completed: %s",
        recording_id,
        from_stage,
        new_completed,
    )
    
    return recording.get_pipeline_state()


# ---------------------------------------------------------------------------
# Synchronous versions for use in workers (which use sync DB connections)
# ---------------------------------------------------------------------------

def get_state_sync(recording_id: str) -> dict:
    """Synchronous version of get_state for workers (no db param)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.config import settings
    
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")
        
        return recording.get_pipeline_state()


def get_state_sync_with_db(db: Session, recording_id: str) -> dict:
    """Synchronous version of get_state for workers (with db param)."""
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        raise ValueError(f"Recording {recording_id} not found")
    
    return recording.get_pipeline_state()


def mark_stage_complete_sync(recording_id: str, stage_name: str, updated_by: str = "system") -> None:
    """Synchronous version of mark_stage_complete for workers."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.config import settings
    
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")
        
        recording.mark_stage_complete(stage_name)
        recording.pipeline_state["last_updated_by"] = updated_by
        session.commit()
        
        logger.info("[%s] Marked stage '%s' as completed (sync)", recording_id, stage_name)


def mark_stage_failed_sync(recording_id: str, stage_name: str, error: str, updated_by: str = "system") -> None:
    """Synchronous version of mark_stage_failed for workers."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.config import settings
    
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")
        
        recording.mark_stage_failed(stage_name, error)
        recording.pipeline_state["last_updated_by"] = updated_by
        
        # Increment retry count
        retry_count = recording.pipeline_state.get("retry_count", {})
        retry_count[stage_name] = retry_count.get(stage_name, 0) + 1
        recording.pipeline_state["retry_count"] = retry_count
        
        session.commit()
        
        logger.error("[%s] Stage '%s' failed (sync): %s", recording_id, stage_name, error)


def is_stage_completed_sync(recording_id: str, stage_name: str) -> bool:
    """Synchronous version of can_skip_stage for workers."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.config import settings
    
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")
        
        return recording.is_stage_completed(stage_name)
