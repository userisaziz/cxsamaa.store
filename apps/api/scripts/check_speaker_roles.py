"""Diagnostic script to check speaker role classification for a recording."""
import sys
import uuid

# Add project root to path  
sys.path.insert(0, "/Users/almabetter/xsamaa-ai-pipeline/apps/api")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models.transcript import SpeakerRole, ConversationTurn, SpeakerRoleCorrection
from src.models.recording import Recording

RECORDING_ID = "1ff124fd-f47a-4a8b-a3fb-387cbf5efa5e"

# Create sync engine for diagnostic
engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

def diagnose():
    print(f"\n{'='*80}")
    print(f"Speaker Role Diagnosis for Recording: {RECORDING_ID}")
    print(f"{'='*80}\n")

    db = SessionLocal()
    try:
        # 1. Check if recording exists
        recording = db.execute(
            select(Recording).where(Recording.id == uuid.UUID(RECORDING_ID))
        ).scalar_one_or_none()
        
        if not recording:
            print("❌ Recording not found!")
            return
            
        print(f"✅ Recording found:")
        print(f"   - Status: {recording.status}")
        print(f"   - Salesperson ID: {recording.salesperson_id}")
        print(f"   - Duration: {recording.duration_seconds}s\n")

        # 2. Check speaker_roles table
        roles = db.execute(
            select(SpeakerRole).where(SpeakerRole.recording_id == uuid.UUID(RECORDING_ID))
        ).scalars().all()
        
        print(f"📊 Speaker Roles Found: {len(roles)}")
        if roles:
            for role in roles:
                print(f"   ✅ {role.speaker_label} → {role.role_label} "
                      f"(method: {role.classification_method}, confidence: {role.confidence})")
        else:
            print("   ❌ NO SPEAKER ROLES FOUND - Role classification did not run or failed!")
        print()

        # 3. Check conversation_turns table
        turns = db.execute(
            select(ConversationTurn).where(
                ConversationTurn.recording_id == uuid.UUID(RECORDING_ID)
            ).order_by(ConversationTurn.start_time)
        ).scalars().all()
        
        print(f"📊 Conversation Turns Found: {len(turns)}")
        if turns:
            unique_speakers = set(turn.speaker_label for turn in turns)
            print(f"   - Unique speakers: {', '.join(sorted(unique_speakers))}")
            
            # Check if turns have role_label
            turns_with_roles = [t for t in turns if t.role_label]
            print(f"   - Turns with role_label: {len(turns_with_roles)}/{len(turns)}")
            
            if turns_with_roles:
                # Show sample
                print(f"\n   Sample turns:")
                for turn in turns[:5]:
                    role_display = turn.role_label or "❌ None"
                    print(f"     {turn.speaker_label} [{role_display}]: {turn.text[:60]}...")
            else:
                print("   ❌ NO TURNS HAVE ROLE_LABEL - Classification failed!")
        else:
            print("   ❌ NO CONVERSATION TURNS FOUND - Turn builder didn't run!")
        print()

        # 4. Check pipeline stage completion from recording status
        print(f"🔍 Pipeline Status:")
        print(f"   Recording status: {recording.status}")
        if recording.status == "COMPLETED":
            print("   ✅ Pipeline completed successfully")
            if not roles:
                print("   ⚠️  But speaker roles are missing - possible role classification task failure")
        else:
            print(f"   ⚠️  Pipeline not completed (status: {recording.status})")
            print("   This explains why roles are missing")
        print()

        # 5. Check for role correction audit trail
        corrections = db.execute(
            select(SpeakerRoleCorrection).where(
                SpeakerRoleCorrection.recording_id == uuid.UUID(RECORDING_ID)
            )
        ).scalars().all()
        
        if corrections:
            print(f"📝 Manual Corrections Found: {len(corrections)}")
            for corr in corrections:
                print(f"   - {corr.speaker_label}: {corr.original_role} → {corr.corrected_role}")
        else:
            print("📝 No manual corrections found")
        print()

        # 6. Recommendation
        print(f"{'='*80}")
        print("RECOMMENDATION:")
        print(f"{'='*80}")
        if not roles and not turns:
            print("❌ Turn builder and role classification didn't run")
            print("→ Reprocess this recording: cd apps/api && uv run python reprocess.py " + RECORDING_ID)
        elif not roles and turns:
            print("❌ Role classification failed but turns exist")
            print("→ Check Celery logs for role_classification task errors")
            print("→ Or reprocess: cd apps/api && uv run python reprocess.py " + RECORDING_ID)
        elif roles:
            print("✅ Speaker roles exist in database")
            print("→ Frontend should display them - check API response")
            print("→ Test endpoint: curl http://localhost:8000/recordings/" + RECORDING_ID + "/transcript")
        print()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
