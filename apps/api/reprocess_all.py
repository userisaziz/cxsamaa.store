#!/usr/bin/env python3
"""Reprocess all recordings with new segmentation logic and monitor every stage.

Usage:
  # Development (localhost:8000)
  python reprocess_all.py
  
  # Production (with env vars)
  API_URL=https://api.samaa.com python reprocess_all.py
  API_URL=https://api.samaa.com ADMIN_EMAIL=admin@samaa.com ADMIN_PASSWORD=xxx python reprocess_all.py
"""
import subprocess
import time
import json
import sys
import os
from datetime import datetime

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

# Configuration from environment (defaults to development)
API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@samaa.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
MAX_TIMEOUT = int(os.getenv("MAX_TIMEOUT", "600"))  # 10 minutes per recording
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

print(f"🌐 API URL: {API_URL}")
print(f"👤 Admin: {ADMIN_EMAIL}")
print(f"⏱️  Timeout: {MAX_TIMEOUT}s per recording\n")

# Pipeline stages in order
PIPELINE_STAGES = [
    "UPLOADED",
    "PREPROCESSING",
    "TRANSCRIBING",
    "DIARIZING",
    "SEGMENTING",
    "ANALYZING",
    "SCORING",
    "COMPLETED",
]

STAGE_EMOJIS = {
    "UPLOADED": "📤",
    "PREPROCESSING": "🔧",
    "TRANSCRIBING": "📝",
    "DIARIZING": "🎯",
    "SEGMENTING": "✂️",
    "ANALYZING": "🧠",
    "SCORING": "📊",
    "COMPLETED": "✅",
    "FAILED": "❌",
}

def get_recording_status(token, recording_id):
    """Fetch current recording status and details."""
    result = run_cmd(f'''curl -s -H "Authorization: Bearer {token}" \
"{API_URL}/api/v1/recordings/{recording_id}"''')
    try:
        return json.loads(result)
    except:
        return None

def monitor_recording_progress(token, recording_id, timeout=None, poll_interval=None):
    """Monitor a recording through all pipeline stages with real-time updates."""
    if timeout is None:
        timeout = MAX_TIMEOUT
    if poll_interval is None:
        poll_interval = POLL_INTERVAL
    
    start_time = time.time()
    last_status = None
    stage_times = {}
    
    print(f"\n{'='*80}")
    print(f"📊 Monitoring Recording: {recording_id[:8]}...")
    print(f"{'='*80}\n")
    
    while time.time() - start_time < timeout:
        recording = get_recording_status(token, recording_id)
        if not recording:
            print("⚠️  Failed to fetch recording status")
            time.sleep(poll_interval)
            continue
        
        current_status = recording.get("status", "UNKNOWN")
        error_msg = recording.get("error_message")
        duration = recording.get("duration_seconds", 0) or 0
        
        # Detect status change
        if current_status != last_status:
            timestamp = datetime.now().strftime("%H:%M:%S")
            emoji = STAGE_EMOJIS.get(current_status, "❓")
            
            # Record stage transition time
            if last_status:
                stage_times[last_status] = time.time() - start_time
            
            print(f"[{timestamp}] {emoji} {last_status or 'START'} → {current_status}")
            
            # Show additional info based on stage
            if current_status == "PREPROCESSING":
                print(f"   └─ Normalizing audio to 16kHz mono WAV")
            elif current_status == "TRANSCRIBING":
                print(f"   └─ Running NVIDIA Parakeet STT (word-level)")
            elif current_status == "DIARIZING":
                print(f"   └─ Speaker diarization (pyannote.audio)")
            elif current_status == "SEGMENTING":
                print(f"   └─ Splitting into discrete conversations")
            elif current_status == "ANALYZING":
                print(f"   └─ LLM analysis (Llama 3.3 70B)")
            elif current_status == "SCORING":
                print(f"   └─ Computing 5-dimension performance scores")
            elif current_status == "COMPLETED":
                elapsed = time.time() - start_time
                print(f"   └─ ✅ Pipeline complete! Duration: {duration}s, Elapsed: {elapsed:.1f}s")
                stage_times["COMPLETED"] = elapsed
            elif current_status == "FAILED":
                print(f"   └─ ❌ Error: {error_msg}")
                stage_times["FAILED"] = time.time() - start_time
            
            last_status = current_status
        
        # Terminal state reached
        if current_status in ["COMPLETED", "FAILED"]:
            print(f"\n{'='*80}")
            print(f"📈 Stage Timing Report:")
            print(f"{'='*80}")
            for stage in PIPELINE_STAGES:
                if stage in stage_times:
                    print(f"  {STAGE_EMOJIS[stage]} {stage:20s} → {stage_times[stage]:.2f}s")
            print(f"{'='*80}\n")
            return current_status, error_msg
        
        time.sleep(poll_interval)
    
    print(f"\n⏱️  Timeout after {timeout}s (last status: {last_status})")
    return "TIMEOUT", None

# Login
print("🔑 Logging in...")
token = run_cmd(f'''curl -s -X POST {API_URL}/api/v1/auth/login \
-H "Content-Type: application/json" \
-d '{{"email":"{ADMIN_EMAIL}","password":"{ADMIN_PASSWORD}"}}' | \
python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"''')

if not token:
    print("❌ Login failed")
    exit(1)

print("✓ Logged in\n")

# Get recordings
print("📊 Fetching recordings...")
recordings_json = run_cmd(f'''curl -s -H "Authorization: Bearer {token}" \
"{API_URL}/api/v1/recordings?page=1&page_size=100"''')

data = json.loads(recordings_json)
recordings = data.get("items", [])
print(f"Found {len(recordings)} recordings\n")

# Filter processed recordings
to_reprocess = [r for r in recordings if r["status"] not in ["UPLOADED"]]
print(f"🔄 {len(to_reprocess)} recordings need reprocessing\n")

if not to_reprocess:
    print("✅ No recordings to reprocess")
    exit(0)

# Trigger reprocess and monitor each recording
print("🚀 Triggering reprocessing pipeline with stage monitoring...\n")
results = {
    "completed": [],
    "failed": [],
    "timeout": [],
}

for i, recording in enumerate(to_reprocess, 1):
    rec_id = recording["id"]
    duration = recording.get("duration_seconds", 0) or 0
    initial_status = recording["status"]
    
    print(f"\n{'━'*80}")
    print(f"[{i}/{len(to_reprocess)}] Reprocessing {rec_id[:8]}... (Initial: {initial_status}, Duration: {duration:.0f}s)")
    print(f"{'━'*80}")
    
    # Trigger reprocess
    result = run_cmd(f'''curl -s -X POST \
-H "Authorization: Bearer {token}" \
"{API_URL}/api/v1/recordings/{rec_id}/reprocess"''')
    
    if "pipeline triggered" in result.lower() or "200" in result or "UPLOADED" in result:
        print(f"✓ Pipeline triggered successfully")
        
        # Wait a moment for pipeline to start
        time.sleep(2)
        
        # Monitor progress through all stages
        final_status, error = monitor_recording_progress(
            token, 
            rec_id, 
            timeout=MAX_TIMEOUT,
            poll_interval=POLL_INTERVAL
        )
        
        if final_status == "COMPLETED":
            results["completed"].append(rec_id)
        elif final_status == "FAILED":
            results["failed"].append((rec_id, error))
        else:
            results["timeout"].append(rec_id)
    else:
        print(f"⚠️  Failed to trigger: {result[:200]}")
        results["failed"].append((rec_id, "Trigger failed"))
    
    time.sleep(1)

# Final summary
print(f"\n{'='*80}")
print(f"🎯 REPROCESSING SUMMARY")
print(f"{'='*80}")
print(f"Total recordings: {len(to_reprocess)}")
print(f"✅ Completed: {len(results['completed'])}")
print(f"❌ Failed: {len(results['failed'])}")
print(f"⏱️  Timeout: {len(results['timeout'])}")

if results["completed"]:
    print(f"\n✅ Successful:")
    for rec_id in results["completed"]:
        print(f"   • {rec_id[:8]}...")

if results["failed"]:
    print(f"\n❌ Failed:")
    for rec_id, error in results["failed"]:
        print(f"   • {rec_id[:8]}... - {error}")

if results["timeout"]:
    print(f"\n⏱️  Timed out:")
    for rec_id in results["timeout"]:
        print(f"   • {rec_id[:8]}...")

print(f"{'='*80}")
print("\n✅ All reprocessing tasks completed!")
print("💡 Check Celery logs for detailed pipeline execution:")
print("   tail -f .logs/celery.log")
