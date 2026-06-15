#!/usr/bin/env python3
"""
Cleanup script to delete failed/pending recordings from database and R2.
Run this to start fresh with uploads.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import src
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models.recording import Recording, RecordingStatus
from src.storage.local import get_storage


def cleanup_recordings():
    """Delete PENDING_UPLOAD and FAILED recordings from DB and R2."""
    
    # Create sync engine for cleanup script
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        # Get all PENDING_UPLOAD and FAILED recordings
        stmt = delete(Recording).where(
            Recording.status.in_([
                RecordingStatus.PENDING_UPLOAD,
                RecordingStatus.FAILED
            ])
        )
        
        result = session.execute(stmt)
        deleted_count = result.rowcount
        session.commit()
        
        print(f"✅ Deleted {deleted_count} recordings from database")
        
        # Note: R2 files are not deleted (orphaned files)
        # You can manually delete them from Cloudflare R2 dashboard if needed


if __name__ == "__main__":
    print("🧹 Cleaning up failed and pending recordings...")
    print(f"📊 Database: {settings.database_url_sync.split('@')[1] if '@' in settings.database_url_sync else 'unknown'}")
    print(f"💾 Storage: {settings.storage_backend}")
    print()
    
    try:
        cleanup_recordings()
        print()
        print("✅ Cleanup complete!")
        print("You can now start fresh with new uploads.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
