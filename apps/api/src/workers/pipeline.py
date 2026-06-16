"""Pipeline orchestration — Dual-mode (Celery for Dev, Cloud Tasks for Prod).

Development: Uses Celery + Redis for process isolation and retry logic.
Production: Uses Cloud Tasks for serverless orchestration.

This ensures dev/prod parity and prevents threading-related bugs.
"""
import json
import logging
import os

from src.config import settings
from src.services.pipeline_progress import (
    log_stage_start,
    log_stage_complete,
    log_stage_error,
    log_pipeline_complete,
    log_pipeline_halted,
)
from src.workers.pipeline_control import PipelineHalted
from src.workers.preprocessing import (
    preprocess_audio,
    _update_recording_status_sync,
    _get_recording_sync,
)
from src.workers.transcription import dispatch_transcription
from src.workers.diarization import dispatch_diarization
from src.workers.turn_builder import build_conversation_turns
from src.workers.role_classification import classify_speaker_roles
from src.workers.segmentation import segment_conversations
from src.workers.audio_stitcher import extract_conversation_audio
from src.workers.analysis import analyze_conversations
from src.workers.scoring import score_salesperson

logger = logging.getLogger(__name__)

# Ordered stage definitions: (endpoint_path, function, status_label)
# Status labels must match RecordingStatus enum in src/models/recording.py
# Note: Diarization stage is conditionally included based on settings.enable_diarization
STAGES = [
    ("/stage/preprocess", preprocess_audio, "TRANSCRIBING"),
    ("/stage/stt", dispatch_transcription, "DIARIZING"),
    ("/stage/diarization", dispatch_diarization, "RECONCILING"),  # Optional: skipped if enable_diarization=False
    ("/stage/turns", build_conversation_turns, "RECONCILING"),  # Next status after turns
    ("/stage/roles", classify_speaker_roles, "SEGMENTING"),
    ("/stage/segmentation", segment_conversations, "SEGMENTING"),  # Stays SEGMENTING until extraction
    ("/stage/extract-audio", extract_conversation_audio, "STITCHING"),
    ("/stage/analyze", analyze_conversations, "ANALYZING"),
    ("/stage/scoring", score_salesperson, "SCORING"),
]


def get_active_stages() -> list[tuple]:
    """Get pipeline stages, optionally excluding diarization.
    
    When enable_diarization=False, the diarization stage is removed from the pipeline.
    This allows faster processing when speaker identification isn't needed.
    """
    if settings.enable_diarization:
        return STAGES
    
    # Skip diarization stage (index 2)
    return [stage for i, stage in enumerate(STAGES) if i != 2]


def run_stage(recording_id: str, pipeline_version: str, stage_index: int, force_rerun: bool = False) -> None:
    """Execute a single pipeline stage and enqueue the next one.

    Each stage:
    1. Checks if already completed (idempotency)
    2. Checks if already running (prevent duplicate tasks)
    3. Runs its processing function
    4. Updates recording status in DB
    5. Enqueues the next stage via Cloud Tasks
    6. If last stage, marks recording COMPLETED
    """
    active_stages = get_active_stages()
    
    if stage_index >= len(active_stages):
        log_pipeline_complete(recording_id, len(active_stages))
        logger.info("[%s] Pipeline completed", recording_id)
        return

    path, func, status_label = active_stages[stage_index]
    stage_name = path.split("/")[-1]  # "preprocess", "stt", etc.
    
    # Idempotency check: skip if stage already completed (unless force_rerun)
    if not force_rerun:
        from src.services.pipeline_state import is_stage_completed_sync
        if is_stage_completed_sync(recording_id, stage_name):
            logger.info(
                "[%s] Skipping stage %d/%d: %s (already completed)",
                recording_id, stage_index + 1, len(active_stages), stage_name,
            )
            # Still enqueue next stage
            if stage_index + 1 < len(active_stages):
                next_index = stage_index + 1
                next_path = active_stages[next_index][0]
                
                if settings.app_env == "development":
                    from src.workers.pipeline_worker import enqueue_next_stage_celery
                    enqueue_next_stage_celery(recording_id, pipeline_version, next_index)
                else:
                    enqueue_next_stage_cloud_tasks(recording_id, pipeline_version, next_path)
                    logger.info("[%s] Enqueued next stage (skipped): %s", recording_id, next_path)
            else:
                log_pipeline_complete(recording_id, len(active_stages))
                logger.info("[%s] Pipeline completed", recording_id)
            return
    
    # Duplicate task prevention: check if recording is already processing this stage
    # by comparing current status with expected status for this stage
    # MUST run BEFORE log_stage_start (which overwrites status to TRANSCRIBING)
    current_recording = _get_recording_sync(recording_id)
    if current_recording and current_recording.get("status") == status_label:
        # Status already set to this stage's label - another task is likely running
        logger.warning(
            "[%s] Stage %d/%d: %s already in progress (status=%s) — skipping duplicate task",
            recording_id, stage_index + 1, len(STAGES), stage_name, status_label,
        )
        return
    
    # Log stage start with progress tracking (updates status to TRANSCRIBING etc.)
    log_stage_start(recording_id, stage_name, len(STAGES), stage_index)
    
    logger.info(
        "[%s] Running stage %d/%d: %s",
        recording_id, stage_index + 1, len(active_stages), path,
    )

    try:
        func(recording_id)
        _update_status(recording_id, status_label)
        
        # Log stage completion
        log_stage_complete(recording_id, stage_name, len(active_stages), stage_index)

        # Enqueue next stage (dev: Celery, prod: Cloud Tasks)
        if stage_index + 1 < len(active_stages):
            next_index = stage_index + 1
            next_path = active_stages[next_index][0]
            
            if settings.app_env == "development":
                # Development: enqueue via Celery for process isolation
                from src.workers.pipeline_worker import enqueue_next_stage_celery
                enqueue_next_stage_celery(recording_id, pipeline_version, next_index)
            else:
                # Production: enqueue via Cloud Tasks
                enqueue_next_stage_cloud_tasks(recording_id, pipeline_version, next_path)
                logger.info("[%s] Enqueued next stage via Cloud Tasks: %s", recording_id, next_path)
        else:
            log_pipeline_complete(recording_id, len(active_stages))
            logger.info("[%s] Pipeline completed", recording_id)

    except PipelineHalted as e:
        logger.warning("[%s] Pipeline halted at %s: %s", recording_id, path, e)
        _update_status(recording_id, "FAILED", str(e))
        
        # Mark stage failed in pipeline_state
        from src.services.pipeline_state import mark_stage_failed_sync
        mark_stage_failed_sync(recording_id, stage_name, str(e))
        
        # Check retry limit
        from src.services.pipeline_state import get_state_sync
        MAX_RETRIES = 3
        state = get_state_sync(recording_id)
        retry_count = state.get("retry_count", {}).get(stage_name, 0)
        
        # Log pipeline halt with retry information
        log_pipeline_halted(recording_id, stage_name, str(e), retry_count, MAX_RETRIES)
        
        if retry_count >= MAX_RETRIES:
            logger.error(
                "[%s] Stage %s exceeded retry limit (%d/%d). Halting pipeline.",
                recording_id, stage_name, retry_count, MAX_RETRIES,
            )
            _update_status(
                recording_id,
                "FAILED",
                f"Stage '{stage_name}' failed {retry_count} times. Manual intervention required.",
            )
        
    except Exception as e:
        logger.error("[%s] Stage %s failed: %s", recording_id, path, e, exc_info=True)
        _update_status(recording_id, "FAILED", str(e))
        
        # Log stage error
        log_stage_error(recording_id, stage_name, str(e), len(STAGES), stage_index)
        
        # Mark stage failed in pipeline_state
        from src.services.pipeline_state import mark_stage_failed_sync
        mark_stage_failed_sync(recording_id, stage_name, str(e))
        
        # Check retry limit
        from src.services.pipeline_state import get_state_sync
        MAX_RETRIES = 3
        state = get_state_sync(recording_id)
        retry_count = state.get("retry_count", {}).get(stage_name, 0)
        
        if retry_count >= MAX_RETRIES:
            logger.error(
                "[%s] Stage %s exceeded retry limit (%d/%d). Halting pipeline.",
                recording_id, stage_name, retry_count, MAX_RETRIES,
            )
            _update_status(
                recording_id,
                "FAILED",
                f"Stage '{stage_name}' failed {retry_count} times. Manual intervention required.",
            )
        
        raise


def _update_status(recording_id: str, status: str, reason: str = None) -> None:
    """Update DB status so the dashboard shows real-time progress."""
    _update_recording_status_sync(recording_id, status, reason)


# ---------------------------------------------------------------------------
# Cloud Tasks queue management (Production only)
# ---------------------------------------------------------------------------

def _enqueue_cloud_task(
    recording_id: str,
    pipeline_version: str,
    stage_path: str,
    stage_index: int,
    dispatch_deadline: int = 550,  # 550s = 9 min 10s (buffer vs Cloud Run's 600s)
) -> None:
    """Enqueue a single stage as a Cloud Task."""
    from google.cloud import tasks_v2
    
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(
        settings.gcp_project,
        settings.gcp_region,
        "cxsamaa-pipeline",
    )

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{settings.worker_url}{stage_path}",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "recording_id": recording_id,
                "pipeline_version": pipeline_version,
                "stage_path": stage_path,
                "stage_index": stage_index,
            }).encode(),
            "oidc_token": {
                "service_account_email": settings.gcp_worker_sa_email,
            },
        },
        "dispatch_deadline": {"seconds": dispatch_deadline},
        "retry_config": {
            "max_attempts": 3,
            "min_backoff": {"seconds": 10},
            "max_backoff": {"seconds": 300},
        },
    }

    client.create_task(parent=parent, task=task)
    logger.info(
        "Enqueued Cloud Task stage %s (index %d) for recording %s",
        stage_path, stage_index, recording_id,
    )


def enqueue_first_stage(recording_id: str, pipeline_version: str = "v1") -> None:
    """Kick off the pipeline from the FastAPI upload endpoint."""
    if settings.app_env == "development":
        from src.workers.pipeline_worker import execute_stage
        execute_stage.delay(recording_id, pipeline_version, 0, False)
        logger.info("[%s] Enqueued first stage via Celery", recording_id)
    else:
        enqueue_next_stage_cloud_tasks(recording_id, pipeline_version, "/stage/preprocess")
        logger.info("[%s] Enqueued first stage via Cloud Tasks", recording_id)


def enqueue_next_stage_cloud_tasks(recording_id: str, pipeline_version: str, stage_path: str) -> None:
    """Called at the end of each stage to trigger the next one via Cloud Tasks."""
    active_stages = get_active_stages()
    for index, (path, _, _) in enumerate(active_stages):
        if path == stage_path:
            _enqueue_cloud_task(recording_id, pipeline_version, stage_path, index)
            return

    logger.error("Unknown stage path: %s", stage_path)
