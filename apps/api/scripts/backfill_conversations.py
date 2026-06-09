#!/usr/bin/env python3
"""Backfill script — populate salesperson_id, recorded_at, duration_seconds on existing Conversation rows.

Run after applying the alembic migration that adds these columns.

Usage:
    cd apps/api
    uv run python -m scripts.backfill_conversations
"""
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path so we can import src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from src.config import settings
from src.models.conversation import Conversation
from src.models.recording import Recording


def backfill_conversations():
    """Populate denormalized fields on existing Conversation rows."""
    engine = create_engine(settings.database_url_sync)

    with Session(engine) as session:
        # Count conversations that need backfilling
        convs = (
            session.query(Conversation)
            .filter(Conversation.salesperson_id.is_(None))
            .all()
        )

        if not convs:
            logger.info("No conversations need backfilling — all already populated.")
            return

        logger.info(f"Backfilling {len(convs)} conversations...")

        # Build a lookup of recording_id -> (salesperson_id, recorded_at)
        recordings = session.query(Recording).all()
        recording_lookup = {
            r.id: (r.salesperson_id, r.recorded_at) for r in recordings
        }

        updated = 0
        skipped = 0

        for conv in convs:
            recording_info = recording_lookup.get(conv.recording_id)
            if recording_info:
                salesperson_id, recorded_at = recording_info
                conv.salesperson_id = salesperson_id
                conv.recorded_at = recorded_at
                conv.duration_seconds = conv.end_time - conv.start_time
                updated += 1
            else:
                logger.warning(f"Recording {conv.recording_id} not found for conversation {conv.id}")
                skipped += 1

        session.commit()
        logger.info(f"Backfill complete: {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    backfill_conversations()
