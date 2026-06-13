"""Fix all recordings with UNKNOWN speaker labels."""
import uuid
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models.transcript import WordTranscript, ConversationTurn, SpeakerRole
from src.models.recording import Recording

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_affected_recordings():
    """Find all recordings with UNKNOWN word speaker labels."""
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        # Find all completed recordings
        recordings = session.query(Recording).filter(
            Recording.status == "COMPLETED"
        ).all()
        
        affected = []
        for recording in recordings:
            # Check word transcripts
            word_count = session.query(WordTranscript).filter(
                WordTranscript.recording_id == recording.id
            ).count()
            
            unknown_count = session.query(WordTranscript).filter(
                WordTranscript.recording_id == recording.id,
                WordTranscript.speaker_label == "UNKNOWN"
            ).count()
            
            if word_count > 0 and unknown_count == word_count:
                affected.append(str(recording.id))
        
        return affected

if __name__ == "__main__":
    affected = find_affected_recordings()
    
    if not affected:
        print("✅ No affected recordings found!")
    else:
        print(f"Found {len(affected)} affected recordings:")
        for rec_id in affected:
            print(f"  - {rec_id}")
        
        response = input("\nFix all of them? (y/N): ")
        if response.lower() == 'y':
            import subprocess
            for i, rec_id in enumerate(affected, 1):
                print(f"\n[{i}/{len(affected)}] Fixing {rec_id}...")
                result = subprocess.run(
                    ["uv", "run", "python", "fix_word_speaker_labels.py", rec_id],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"  ✅ Fixed")
                else:
                    print(f"  ❌ Failed: {result.stderr[-200:]}")
        else:
            print("Cancelled")
