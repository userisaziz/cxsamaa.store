"""Celery app for local development task queue.

Production uses Cloud Tasks, but Celery provides:
- Process isolation (vs threading's shared memory)
- Retry logic and failure handling
- Task visibility via Flower
- DB connection pool safety

Start local worker:
  celery -A src.workers.celery_app worker --loglevel=info --pool=solo
"""
from celery import Celery
from sqlalchemy.orm import configure_mappers

from src.config import settings

# Import all models to register them with the mapper registry
from src.models import (
    brand, conversation, recording,
    salesperson, store, transcript, user, metrics,
)

# Configure relationships between all mapped models
configure_mappers()

celery_app = Celery(
    "samaa",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.workers.pipeline_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # acks_late + prefetch_multiplier=1 ensures tasks are redelivered on worker crash.
    # All pipeline tasks are idempotent (idempotency check at stage entry).
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Global limits serve as upper bounds; individual tasks set their own tighter timeouts.
    task_soft_time_limit=3600,   # 1 hour soft limit
    task_time_limit=7200,        # 2 hour hard limit
)