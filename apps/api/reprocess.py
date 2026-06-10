"""Reprocess a recording and trigger the full pipeline."""
import asyncio
from sqlalchemy import select
from src.database import async_session_factory
from src.models.recording import Recording, RecordingStatus

async def reprocess():
    recording_id = "e82bfdc9-87ad-4013-9cfd-351252e51d65"
    
    async with async_session_factory() as session:
        # Get recording
        rec_result = await session.execute(
            select(Recording).where(Recording.id == recording_id)
        )
        recording = rec_result.scalar_one_or_none()
        
        if not recording:
            print(f"Recording {recording_id} not found")
            return
        
        print(f"Current status: {recording.status}")
        print(f"Resetting to UPLOADED and restarting pipeline...")
        
        # Reset status
        recording.status = RecordingStatus.UPLOADED
        recording.error_message = None
        await session.flush()
        await session.commit()
        
        # Restart pipeline
        from src.workers.pipeline import start_processing_pipeline
        result = start_processing_pipeline(str(recording.id))
        
        print(f"Pipeline started! Task ID: {result.id}")
        print("Check celery.log for progress")

if __name__ == "__main__":
    asyncio.run(reprocess())