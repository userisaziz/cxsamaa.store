"""Pipeline control — shared helpers for halting the processing chain on failure."""
import logging

from src.models.recording import RecordingStatus
from src.services.pipeline_state import mark_stage_failed_sync
from src.workers.preprocessing import _update_recording_status_sync

logger = logging.getLogger(__name__)


class PipelineHalted(Exception):
    """Recording failed a validation step — do not retry, do not continue chain."""


def _update_status(recording_id: str, status: str, reason: str = None) -> None:
    """Update DB status so the dashboard shows real-time progress."""
    _update_recording_status_sync(recording_id, status, reason)


def fail_and_halt(recording_id: str, reason: str) -> None:
    """Mark recording FAILED and halt the chain without retries.

    Raises PipelineHalted which callers must catch and log.
    The chain stops — no retries, no continuation.
    """
    logger.error("[%s] Pipeline halted: %s", recording_id, reason)
    _update_recording_status_sync(recording_id, "FAILED", reason)
    raise PipelineHalted(reason)