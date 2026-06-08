"""Salesperson scoring worker — placeholder for Sprint 3."""
import logging
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="score_salesperson")
def score_salesperson(self, recording_id: str) -> str:
    """Score salesperson performance across 5 dimensions."""
    logger.info(f"Scoring salesperson for recording {recording_id}")
    # TODO Sprint 3: Score greeting, discovery, product knowledge, objection handling, closing
    return recording_id
