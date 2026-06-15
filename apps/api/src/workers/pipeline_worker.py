"""Celery task definitions for pipeline stages.

This module wraps the pipeline stage functions as Celery tasks for local development.
Production uses Cloud Tasks, but Celery provides process isolation and retry logic
that threading cannot match.

Start worker:
  celery -A src.workers.celery_app worker --loglevel=info --pool=solo
"""
import logging

from src.workers.celery_app import celery_app
from src.workers.pipeline import STAGES
from src.workers.pipeline_control import PipelineHalted, _update_status
from src.services.pipeline_state import (
    is_stage_completed_sync,
    mark_stage_failed_sync,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute between retries
    acks_late=True,
)
def execute_stage(
    self,
    recording_id: str,
    pipeline_version: str,
    stage_index: int,
    force_rerun: bool = False,
) -> dict:
    """Execute a single pipeline stage as a Celery task.

    This is the Celery equivalent of pipeline.run_stage, with process
    isolation and retry semantics.

    Returns:
        dict with stage execution result
    """
    # Pipeline completion check
    if stage_index >= len(STAGES):
        _update_status(recording_id, "COMPLETED")
        logger.info("[%s] Pipeline completed", recording_id)
        return {"status": "completed", "recording_id": recording_id}

    path, func, status_label = STAGES[stage_index]
    stage_name = path.split("/")[-1]

    # Idempotency check — skip already-completed stages
    if not force_rerun and is_stage_completed_sync(recording_id, stage_name):
        logger.info(
            "[%s] Skipping stage %d/%d: %s (already completed)",
            recording_id, stage_index + 1, len(STAGES), stage_name,
        )
        _enqueue_next_or_complete(recording_id, pipeline_version, stage_index)
        return {"status": "skipped", "stage": stage_name}

    logger.info(
        "[%s] Running stage %d/%d: %s",
        recording_id, stage_index + 1, len(STAGES), path,
    )

    try:
        func(recording_id)
        _update_status(recording_id, status_label)
        _enqueue_next_or_complete(recording_id, pipeline_version, stage_index)
        return {
            "status": "success",
            "stage": stage_name,
            "recording_id": recording_id,
        }

    except PipelineHalted as e:
        # Halt means: validation failed, do not retry, do not continue.
        # fail_and_halt() already marked the recording FAILED before raising.
        logger.warning("[%s] Pipeline halted at %s: %s", recording_id, path, e)
        mark_stage_failed_sync(recording_id, stage_name, str(e))
        return {"status": "halted", "stage": stage_name, "error": str(e)}

    except Exception as e:
        logger.error(
            "[%s] Stage %s failed unexpectedly: %s",
            recording_id, path, e, exc_info=True,
        )
        mark_stage_failed_sync(recording_id, stage_name, str(e))

        # Let Celery handle retry counting via self.request.retries
        if self.request.retries < self.max_retries:
            logger.info(
                "[%s] Retrying stage %s (%d/%d)",
                recording_id, stage_name,
                self.request.retries + 1, self.max_retries,
            )
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        # Max retries exceeded
        logger.error(
            "[%s] Stage %s exceeded retry limit (%d). Halting.",
            recording_id, stage_name, self.max_retries,
        )
        _update_status(
            recording_id,
            "FAILED",
            f"Stage '{stage_name}' failed after {self.max_retries} retries: {e}",
        )
        return {"status": "failed", "stage": stage_name, "error": str(e)}


def _enqueue_next_or_complete(
    recording_id: str,
    pipeline_version: str,
    current_index: int,
) -> None:
    """Enqueue the next stage, or mark pipeline complete if this was the last."""
    next_index = current_index + 1
    if next_index < len(STAGES):
        execute_stage.delay(
            recording_id=recording_id,
            pipeline_version=pipeline_version,
            stage_index=next_index,
            force_rerun=False,
        )
        logger.info(
            "[%s] Enqueued next stage via Celery: %s",
            recording_id, STAGES[next_index][0],
        )
    else:
        _update_status(recording_id, "COMPLETED")
        logger.info("[%s] Pipeline completed", recording_id)