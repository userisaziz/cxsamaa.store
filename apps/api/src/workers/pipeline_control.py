"""Pipeline control — shared helpers for halting the processing chain on failure."""
import logging

from celery.exceptions import Ignore

from src.models.recording import RecordingStatus
from src.workers.preprocessing import _update_recording_status_sync

logger = logging.getLogger(__name__)


class PipelineHalted(Exception):
    """Recording failed a validation step — do not retry, do not continue chain."""


def fail_and_halt(recording_id: str, reason: str) -> None:
    """Mark recording FAILED and halt the chain without retries.

    Raises PipelineHalted which callers must catch and convert to Ignore()
    so Celery marks the task as ignored (not failed/retried) and the chain stops.
    """
    logger.error("[%s] Pipeline halted: %s", recording_id, reason)
    _update_recording_status_sync(recording_id, RecordingStatus.FAILED, reason)
    raise PipelineHalted(reason)
