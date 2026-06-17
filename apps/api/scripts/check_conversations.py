"""Check database for conversations and recordings."""
import asyncio
from sqlalchemy import select
from src.database import async_session_factory
from src.models.conversation import Conversation, ConversationAnalysis
from src.models.recording import Recording

async def check_conversations():
    async with async_session_factory() as session:
        # Count conversations
        conv_result = await session.execute(select(Conversation))
        conversations = conv_result.scalars().all()
        print(f'Total conversations: {len(conversations)}')
        
        for conv in conversations[:5]:
            print(f'  - {conv.id}: {conv.start_time:.1f}s - {conv.end_time:.1f}s ({conv.segment_count} segments)')
            # Check analysis
            analysis_result = await session.execute(
                select(ConversationAnalysis).where(ConversationAnalysis.conversation_id == conv.id)
            )
            analysis = analysis_result.scalar_one_or_none()
            if analysis:
                print(f'    Analysis: outcome={analysis.outcome}, confidence={analysis.confidence}%')
            else:
                print(f'    No analysis')
        
        # Check recent recordings
        rec_result = await session.execute(
            select(Recording).order_by(Recording.uploaded_at.desc()).limit(5)
        )
        recordings = rec_result.scalars().all()
        print(f'\nRecent recordings:')
        for rec in recordings:
            print(f'  - {rec.id}: status={rec.status}, duration={rec.duration_seconds}s')

if __name__ == "__main__":
    asyncio.run(check_conversations())