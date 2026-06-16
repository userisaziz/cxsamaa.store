#!/usr/bin/env python3
"""Reprocess all stuck/failed recordings with comprehensive monitoring.

This script:
1. Identifies all stuck/failed recordings
2. Resets them to UPLOADED status
3. Triggers pipeline reprocessing
4. Monitors each recording through all stages
5. Generates detailed success/failure report

Usage:
  cd /Users/almabetter/xsamaa-ai-pipeline/apps/api
  PYTHONPATH=$(pwd) uv run python scripts/reprocess_all_with_monitoring.py
  
  # Production
  API_URL=https://api.samaa.com ADMIN_EMAIL=admin@samaa.com ADMIN_PASSWORD=xxx \\
    uv run python scripts/reprocess_all_with_monitoring.py
"""
import subprocess
import time
import json
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models.recording import Recording, RecordingStatus

# Configuration from environment
API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@samaa.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
MAX_TIMEOUT = int(os.getenv("MAX_TIMEOUT", "600"))  # 10 minutes per recording
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

# Pipeline stages
PIPELINE_STAGES = [
    "UPLOADED", "PREPROCESSING", "TRANSCRIBING", "DIARIZING",
    "RECONCILING", "SEGMENTING", "STITCHING", "ANALYZING", "SCORING", "COMPLETED"
]

STAGE_EMOJIS = {
    "UPLOADED": "📤", "PREPROCESSING": "🔧", "TRANSCRIBING": "📝",
    "DIARIZING": "🎯", "RECONCILING": "🔄", "SEGMENTING": "✂️",
    "STITCHING": "🎬", "ANALYZING": "🧠", "SCORING": "📊",
    "COMPLETED": "✅", "FAILED": "❌",
}

def run_cmd(cmd):
    """Run shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def get_db_session():
    """Get database session."""
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def login():
    """Login and get auth token."""
    print("🔑 Logging in...")
    token = run_cmd(f'''curl -s -X POST {API_URL}/api/v1/auth/login \\
-H "Content-Type: application/json" \\
-d '{{"email":"{ADMIN_EMAIL}","password":"{ADMIN_PASSWORD}"}}' | \\
python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"''')
    
    if not token:
        print("❌ Login failed")
        sys.exit(1)
    
    print("✓ Logged in\n")
    return token

def get_stuck_recordings():
    """Get all stuck or failed recordings from database."""
    session = get_db_session()
    try:
        # Stuck in processing states
        processing_statuses = [
            RecordingStatus.PREPROCESSING,
            RecordingStatus.TRANSCRIBING,
            RecordingStatus.DIARIZING,
            RecordingStatus.RECONCILING,
            RecordingStatus.SEGMENTING,
            RecordingStatus.STITCHING,
            RecordingStatus.ANALYZING,
            RecordingStatus.SCORING,
        ]
        
        stuck = session.query(Recording).filter(
            Recording.status.in_(processing_statuses)
        ).all()
        
        failed = session.query(Recording).filter(
            Recording.status == RecordingStatus.FAILED
        ).all()
        
        return stuck + failed
    finally:
        session.close()

def reset_recording_to_uploaded(recording_id):
    """Reset recording status to UPLOADED for reprocessing."""
    session = get_db_session()
    try:
        recording = session.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            print(f"  ⚠️  Recording {recording_id} not found")
            return False
        
        old_status = recording.status
        recording.status = RecordingStatus.UPLOADED
        recording.error_message = None
        recording.pipeline_state = {
            "current_stage": "UPLOADED",
            "completed_stages": [],
            "failed_stage": None,
            "error_message": None,
            "last_updated_by": "reprocess_script",
            "retry_count": {},
            "stage_timestamps": {},
        }
        session.commit()
        
        print(f"  ✓ Reset {str(recording_id)[:8]}... from {old_status} → UPLOADED")
        return True
    except Exception as e:
        session.rollback()
        print(f"  ❌ Failed to reset {recording_id}: {e}")
        return False
    finally:
        session.close()

def trigger_pipeline(token, recording_id):
    """Trigger pipeline reprocessing via API."""
    result = run_cmd(f'''curl -s -X POST \\
-H "Authorization: Bearer {token}" \\
"{API_URL}/api/v1/recordings/{recording_id}/reprocess"''')
    
    return "pipeline triggered" in result.lower() or "200" in result or "UPLOADED" in result

def get_recording_status(token, recording_id):
    """Fetch current recording status."""
    result = run_cmd(f'''curl -s -H "Authorization: Bearer {token}" \\
"{API_URL}/api/v1/recordings/{recording_id}"''')
    try:
        return json.loads(result)
    except:
        return None

def monitor_recording(token, recording_id, timeout=None):
    """Monitor recording through pipeline with real-time updates."""
    if timeout is None:
        timeout = MAX_TIMEOUT
    
    start_time = time.time()
    last_status = None
    stage_times = {}
    
    print(f"\n{'='*80}")
    print(f"📊 Monitoring: {str(recording_id)[:8]}...")
    print(f"{'='*80}\n")
    
    while time.time() - start_time < timeout:
        recording = get_recording_status(token, recording_id)
        if not recording:
            time.sleep(POLL_INTERVAL)
            continue
        
        current_status = recording.get("status", "UNKNOWN")
        error_msg = recording.get("error_message")
        duration = recording.get("duration_seconds", 0) or 0
        
        # Detect status change
        if current_status != last_status:
            timestamp = datetime.now().strftime("%H:%M:%S")
            emoji = STAGE_EMOJIS.get(current_status, "❓")
            
            if last_status:
                stage_times[last_status] = time.time() - start_time
            
            print(f"[{timestamp}] {emoji} {last_status or 'START'} → {current_status}")
            
            # Stage descriptions
            stage_info = {
                "PREPROCESSING": "Normalizing audio to 16kHz mono WAV",
                "TRANSCRIBING": "Running STT (Deepgram/NVIDIA Riva)",
                "DIARIZING": "Speaker diarization (pyannote.audio)",
                "RECONCILING": "Reconciling speaker labels",
                "SEGMENTING": "Splitting into conversations",
                "STITCHING": "Extracting conversation audio clips",
                "ANALYZING": "LLM coaching analysis",
                "SCORING": "Computing performance scores",
            }
            
            if current_status in stage_info:
                print(f"   └─ {stage_info[current_status]}")
            elif current_status == "COMPLETED":
                elapsed = time.time() - start_time
                print(f"   └─ ✅ Complete! Audio: {duration}s, Pipeline: {elapsed:.1f}s")
                stage_times["COMPLETED"] = elapsed
            elif current_status == "FAILED":
                print(f"   └─ ❌ Error: {error_msg}")
                stage_times["FAILED"] = time.time() - start_time
            
            last_status = current_status
        
        # Terminal state
        if current_status in ["COMPLETED", "FAILED"]:
            print(f"\n{'='*80}")
            print(f"📈 Stage Timing:")
            print(f"{'='*80}")
            for stage in PIPELINE_STAGES:
                if stage in stage_times:
                    print(f"  {STAGE_EMOJIS[stage]} {stage:20s} → {stage_times[stage]:.2f}s")
            print(f"{'='*80}\n")
            return current_status, error_msg
        
        time.sleep(POLL_INTERVAL)
    
    print(f"\n⏱️  Timeout after {timeout}s (last: {last_status})")
    return "TIMEOUT", None

def main():
    print("🚀 CXSAMAA Pipeline Reprocessing & Monitoring")
    print(f"{'='*80}\n")
    print(f"🌐 API: {API_URL}")
    print(f"👤 Admin: {ADMIN_EMAIL}")
    print(f"⏱️  Timeout: {MAX_TIMEOUT}s per recording\n")
    
    # Login
    token = login()
    
    # Get stuck recordings
    print("🔍 Scanning database for stuck/failed recordings...")
    stuck_recordings = get_stuck_recordings()
    
    if not stuck_recordings:
        print("✅ No stuck recordings found!")
        sys.exit(0)
    
    print(f"\n📊 Found {len(stuck_recordings)} recordings to reprocess:\n")
    for rec in stuck_recordings:
        print(f"  • {str(rec.id)[:8]}... - {rec.status} - {rec.error_message or 'No error'}")
    
    # Reset all to UPLOADED
    print(f"\n{'='*80}")
    print("🔄 Step 1: Resetting recordings to UPLOADED status")
    print(f"{'='*80}\n")
    
    reset_success = []
    for rec in stuck_recordings:
        if reset_recording_to_uploaded(rec.id):
            reset_success.append(rec)
    
    if not reset_success:
        print("\n❌ No recordings successfully reset. Aborting.")
        sys.exit(1)
    
    print(f"\n✓ Reset {len(reset_success)}/{len(stuck_recordings)} recordings\n")
    
    # Reprocess and monitor
    print(f"{'='*80}")
    print("🚀 Step 2: Triggering pipeline & monitoring progress")
    print(f"{'='*80}\n")
    
    results = {"completed": [], "failed": [], "timeout": []}
    
    for i, rec in enumerate(reset_success, 1):
        rec_id = rec.id
        duration = rec.duration_seconds or 0
        
        print(f"\n{'━'*80}")
        print(f"[{i}/{len(reset_success)}] Processing {str(rec_id)[:8]}... (Duration: {duration:.0f}s)")
        print(f"{'━'*80}")
        
        # Trigger pipeline
        if trigger_pipeline(token, str(rec_id)):
            print("✓ Pipeline triggered")
            time.sleep(2)  # Wait for pipeline to start
            
            # Monitor
            final_status, error = monitor_recording(token, str(rec_id))
            
            if final_status == "COMPLETED":
                results["completed"].append(str(rec_id))
            elif final_status == "FAILED":
                results["failed"].append((str(rec_id), error))
            else:
                results["timeout"].append(str(rec_id))
        else:
            print("⚠️  Failed to trigger pipeline")
            results["failed"].append((str(rec_id), "Trigger failed"))
        
        time.sleep(1)
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"🎯 REPROCESSING SUMMARY")
    print(f"{'='*80}")
    print(f"Total reprocessed: {len(reset_success)}")
    print(f"✅ Completed: {len(results['completed'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"⏱️  Timeout: {len(results['timeout'])}")
    print(f"{'='*80}\n")
    
    if results["completed"]:
        print("✅ Successful:")
        for rec_id in results["completed"]:
            print(f"   • {rec_id[:8]}...")
    
    if results["failed"]:
        print("\n❌ Failed:")
        for rec_id, error in results["failed"]:
            print(f"   • {rec_id[:8]}... - {error}")
    
    if results["timeout"]:
        print("\n⏱️  Timed out:")
        for rec_id in results["timeout"]:
            print(f"   • {rec_id[:8]}...")
    
    print(f"\n{'='*80}")
    success_rate = len(results['completed']) / len(reset_success) * 100 if reset_success else 0
    print(f"📊 Success rate: {success_rate:.1f}%")
    print(f"{'='*80}\n")
    
    if success_rate == 100:
        print("🎉 All recordings processed successfully!")
    elif success_rate >= 50:
        print("⚠️  Partial success - check failed recordings")
    else:
        print("❌ Low success rate - pipeline needs debugging")
    
    print("\n💡 Monitor Celery logs:")
    print("   tail -f .logs/celery.log")

if __name__ == "__main__":
    main()
