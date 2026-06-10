from celery import Celery
from sqlalchemy.orm import configure_mappers

from src.config import settings

# Import all models to register them with the mapper registry
from src.models import brand, conversation, recording, salesperson, store, transcript, user, metrics

# Configure relationships between all mapped models
configure_mappers()

celery_app = Celery(
    "samaa",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.workers.preprocessing",
        "src.workers.transcription",
        "src.workers.diarization",
        "src.workers.turn_builder",
        "src.workers.role_classification",
        "src.workers.segmentation",
        "src.workers.analysis",
        "src.workers.scoring",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=7200,  # 2 hour hard limit
)
