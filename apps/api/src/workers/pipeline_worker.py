"""Celery transport layer for the AI pipeline.

This module is the Celery task wrapper ONLY. All pipeline business logic
(idempotency, progress tracking, stage execution, dispatch) lives in
``pipeline.py``. This file exists solely to bridge Celery's task registry
with the pipeline orchestrator.

Responsibilities:
  - Register ``execute_stage`` as a Celery task
  - Provide ``enqueue_next_stage_celery`` for dev-mode stage chaining
  - Provide ``enqueue_first_stage_celery`` for pipeline kickoff

NOT responsible for:
  - Stage execution logic (see pipeline.py :: run_stage)
  - Progress tracking (see services/pipeline_progress.py)
  - State management (see services/pipeline_state.py)
  - Cloud Tasks dispatch (see pipeline.py :: enqueue_next_stage_cloud_tasks)
"""
import logging

from src.workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=0, acks_late=True)
def execute_stage(
    self,
    recording_id: str,
    pipeline_version: str,
    stage_index: int,
    force_rerun: bool = False,
):
    """Celery task entrypoint -- delegates entirely to ``pipeline.run_stage()``.

    Parameters
    ----------
    recording_id : str
        UUID of the recording to process.
    pipeline_version : str
        Pipeline version tag (e.g. "v1") for message tracking.
    stage_index : int
        Zero-based index into ``pipeline.STAGES``.
    force_rerun : bool
        If True, skip idempotency check and re-execute the stage.
    """
    logger.info(
        "[celery] Executing stage %d for recording %s (version=%s, force=%s)",
        stage_index,
        recording_id,
        pipeline_version,
        force_rerun,
    )
    from src.workers.pipeline import run_stage  # lazy import to avoid circular dependency
    run_stage(recording_id, pipeline_version, stage_index, force_rerun)


def enqueue_next_stage_celery(
    recording_id: str,
    pipeline_version: str,
    stage_index: int,
) -> None:
    """Dispatch the next pipeline stage via Celery (dev-mode).

    Called by ``pipeline.run_stage()`` when ``settings.app_env == "development"``.
    """
    execute_stage.delay(recording_id, pipeline_version, stage_index)
    logger.info(
        "[celery] Enqueued stage %d for recording %s",
        stage_index,
        recording_id,
    )
