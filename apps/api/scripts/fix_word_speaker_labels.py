"""Fix word transcript speaker labels by propagating from transcript segments."""
import uuid
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models.transcript import TranscriptSegment, WordTranscript

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_recording(recording_id: str):
    """Fix word speaker labels for a specific recording."""
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        # Get transcript segments with speaker labels
        segments = (
            session.query(TranscriptSegment)
            .filter(TranscriptSegment.recording_id == uuid.UUID(recording_id))
            .order_by(TranscriptSegment.start_time)
            .all()
        )
        
        if not segments:
            logger.error(f"No transcript segments found for {recording_id}")
            return False
        
        # Check if segments have proper speaker labels
        speaker_counts = {}
        for seg in segments:
            speaker_counts[seg.speaker_label] = speaker_counts.get(seg.speaker_label, 0) + 1
        
        logger.info(f"Transcript segments: {len(segments)}")
        logger.info(f"Speaker distribution: {speaker_counts}")
        
        if all(sp == "UNKNOWN" for sp in speaker_counts.keys()):
            logger.error("All transcript segments have UNKNOWN speaker - diarization failed!")
            return False
        
        # Get word transcripts
        words = (
            session.query(WordTranscript)
            .filter(WordTranscript.recording_id == uuid.UUID(recording_id))
            .order_by(WordTranscript.start_time)
            .all()
        )
        
        if not words:
            logger.error(f"No word transcripts found for {recording_id}")
            return False
        
        logger.info(f"Word transcripts: {len(words)}")
        
        # Prepare segments for efficient lookup (sorted by start time)
        segs = sorted([
            {"start": seg.start_time, "end": seg.end_time, "speaker": seg.speaker_label}
            for seg in segments
        ], key=lambda s: s["start"])
        
        # Update word speaker labels
        updated_count = 0
        si = 0
        for word in words:
            mid = (word.start_time + word.end_time) / 2.0
            
            # Advance segment pointer
            while si < len(segs) - 1 and segs[si]["end"] < mid:
                si += 1
            
            # Assign speaker based on containment
            if segs[si]["start"] <= mid <= segs[si]["end"]:
                new_speaker = segs[si]["speaker"]
            else:
                new_speaker = "UNKNOWN"
            
            if word.speaker_label != new_speaker:
                word.speaker_label = new_speaker
                updated_count += 1
        
        session.commit()
        
        # Verify the fix
        word_speakers = {}
        for word in words:
            word_speakers[word.speaker_label] = word_speakers.get(word.speaker_label, 0) + 1
        
        logger.info(f"Updated {updated_count}/{len(words)} word speaker labels")
        logger.info(f"New word speaker distribution: {word_speakers}")
        
        return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python fix_word_speaker_labels.py <recording_id>")
        sys.exit(1)
    
    recording_id = sys.argv[1]
    success = fix_recording(recording_id)
    
    if success:
        print("\n✅ Fixed! Now re-running role classification...")
        # Now rebuild turns and reclassify
        from src.ai.conversation_builder import build_conversation_turns
        from src.ai.role_classifier import classify_speaker_roles
        from src.models.transcript import ConversationTurn, SpeakerRole
        
        engine = create_engine(settings.database_url_sync)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as session:
            # Get updated word transcripts
            words = (
                session.query(WordTranscript)
                .filter(WordTranscript.recording_id == uuid.UUID(recording_id))
                .order_by(WordTranscript.start_time)
                .all()
            )
            
            word_dicts = [
                {
                    "word": w.word,
                    "start_time": w.start_time,
                    "end_time": w.end_time,
                    "confidence": w.confidence,
                    "speaker_label": w.speaker_label,
                }
                for w in words
            ]
            
            # Build turns
            turns = build_conversation_turns(word_dicts)
            logger.info(f"Built {len(turns)} conversation turns")
            
            # Clear old turns
            session.query(ConversationTurn).filter(
                ConversationTurn.recording_id == uuid.UUID(recording_id)
            ).delete()
            
            # Store new turns
            for turn in turns:
                conversation_turn = ConversationTurn(
                    recording_id=uuid.UUID(recording_id),
                    speaker_label=turn["speaker"],
                    start_time=turn["start_time"],
                    end_time=turn["end_time"],
                    text=turn["text"],
                    word_count=turn["word_count"],
                )
                session.add(conversation_turn)
            
            session.commit()
            
            # Check unique speakers
            turn_speakers = set(t["speaker"] for t in turns)
            logger.info(f"Turn speakers: {turn_speakers}")
            
            if len(turn_speakers) >= 2:
                # Classify roles
                classifications = classify_speaker_roles(turns, use_llm=True)
                logger.info(f"Role classifications: {classifications}")
                
                # Clear old roles
                session.query(SpeakerRole).filter(
                    SpeakerRole.recording_id == uuid.UUID(recording_id)
                ).delete()
                
                # Store new roles
                for speaker_label, role_info in classifications.items():
                    speaker_role = SpeakerRole(
                        recording_id=uuid.UUID(recording_id),
                        speaker_label=speaker_label,
                        role_label=role_info["role"],
                        classification_method=role_info["method"],
                        confidence=role_info["confidence"],
                    )
                    session.add(speaker_role)
                    
                    # Update turns with role_label
                    session.query(ConversationTurn).filter(
                        ConversationTurn.recording_id == uuid.UUID(recording_id),
                        ConversationTurn.speaker_label == speaker_label,
                    ).update({"role_label": role_info["role"]})
                
                session.commit()
                logger.info("✅ Role classification complete!")
            else:
                logger.warning(f"Cannot classify roles: only {len(turn_speakers)} speaker(s)")
    else:
        print("\n❌ Fix failed - check logs above")
