"""Check pipeline status for a specific recording."""
import asyncio
from sqlalchemy import select
from src.database import async_session_factory
from src.models.recording import Recording
from src.models.transcript import TranscriptSegment

async def check_pipeline():
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
        
        print(f"Recording ID: {recording.id}")
        print(f"Status: {recording.status}")
        print(f"Duration: {recording.duration_seconds}s")
        print(f"Salesperson ID: {recording.salesperson_id}")
        print(f"File URL: {recording.file_url}")
        print(f"Error: {recording.error_message}")
        print(f"Silence gaps: {recording.silence_gaps}")
        print(f"Speech regions: {recording.speech_regions}")
        
        # Check transcript segments
        seg_result = await session.execute(
            select(TranscriptSegment).where(
                TranscriptSegment.recording_id == recording_id
            ).order_by(TranscriptSegment.start_time)
        )
        segments = seg_result.scalars().all()
        print(f"\nTranscript segments: {len(segments)}")
        
        for seg in segments[:10]:  # Show first 10
            print(f"  - {seg.start_time:.1f}s - {seg.end_time:.1f}s: {seg.speaker_label}: {seg.text[:50]}")

if __name__ == "__main__":
    asyncio.run(check_pipeline())