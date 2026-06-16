#!/usr/bin/env python3
"""Reprocess analysis for conversations missing scores.

This script finds all ConversationAnalysis records where scores is NULL
and re-runs the AI analysis to populate the scores field.

Usage:
    uv run python scripts/reprocess_missing_scores.py
"""
import logging
import uuid
from sqlalchemy import select
from src.database import async_session_factory
from src.models.conversation import ConversationAnalysis
from src.workers.analysis import (
    _get_conversation_segments_sync,
    _store_analysis_sync,
    _update_conversation_summary_sync,
)
from src.ai.analyzer import analyze_conversation as analyze_conversation_ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_conversations_without_scores() -> list[str]:
    """Find all conversation analyses missing scores."""
    import asyncio
    
    async def query():
        async with async_session_factory() as db:
            result = await db.execute(
                select(ConversationAnalysis).where(
                    ConversationAnalysis.scores.is_(None)
                )
            )
            return [str(row.conversation_id) for row in result.scalars().all()]
    
    return asyncio.run(query())


def reprocess_conversation(conv_id: str) -> bool:
    """Reprocess a single conversation to generate scores."""
    logger.info(f"Reprocessing conversation {conv_id}")
    
    # Get transcript segments
    segments = _get_conversation_segments_sync(conv_id)
    if not segments:
        logger.warning(f"  No segments found for {conv_id}")
        return False
    
    logger.info(f"  Found {len(segments)} segment(s)")
    
    # Analyze conversation
    analysis = analyze_conversation_ai(segments)
    if not analysis:
        logger.warning(f"  Analysis failed for {conv_id}")
        return False
    
    # Check if scores were generated
    scores = analysis.get("scores")
    if not scores:
        logger.warning(f"  No scores in analysis for {conv_id}")
        return False
    
    logger.info(f"  Confidence: {analysis.get('confidence')}")
    logger.info(f"  Scores: {scores}")
    
    # Store analysis (including scores)
    _store_analysis_sync(conv_id, analysis)
    
    # Update summary
    summary = analysis.get("summary", "")
    if summary:
        _update_conversation_summary_sync(conv_id, summary)
    
    logger.info(f"  ✅ Successfully reprocessed")
    return True


def main():
    """Main entry point."""
    logger.info("Finding conversations without scores...")
    conv_ids = find_conversations_without_scores()
    
    if not conv_ids:
        logger.info("✅ All conversations have scores - nothing to reprocess")
        return
    
    logger.info(f"Found {len(conv_ids)} conversation(s) without scores")
    
    success_count = 0
    failed_count = 0
    
    for conv_id in conv_ids:
        try:
            if reprocess_conversation(conv_id):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"  ❌ Error reprocessing {conv_id}: {e}")
            failed_count += 1
    
    logger.info(f"\nReprocessing complete:")
    logger.info(f"  ✅ Success: {success_count}")
    logger.info(f"  ❌ Failed: {failed_count}")
    logger.info(f"  📊 Total: {len(conv_ids)}")


if __name__ == "__main__":
    main()
