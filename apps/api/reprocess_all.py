#!/usr/bin/env python3
"""Reprocess all recordings with new segmentation logic."""
import subprocess
import time
import json

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

# Login
print("🔑 Logging in...")
token = run_cmd('''curl -s -X POST http://localhost:8000/api/v1/auth/login \
-H "Content-Type: application/json" \
-d '{"email":"admin@samaa.com","password":"admin123"}' | \
python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"''')

if not token:
    print("❌ Login failed")
    exit(1)

print("✓ Logged in\n")

# Get recordings
print("📊 Fetching recordings...")
recordings_json = run_cmd(f'''curl -s -H "Authorization: Bearer {token}" \
"http://localhost:8000/api/v1/recordings?page=1&page_size=100"''')

data = json.loads(recordings_json)
recordings = data.get("items", [])
print(f"Found {len(recordings)} recordings\n")

# Filter processed recordings
to_reprocess = [r for r in recordings if r["status"] not in ["UPLOADED"]]
print(f"🔄 {len(to_reprocess)} recordings need reprocessing\n")

if not to_reprocess:
    print("✅ No recordings to reprocess")
    exit(0)

# Trigger reprocess
print("🚀 Triggering reprocessing pipeline...\n")
for i, recording in enumerate(to_reprocess, 1):
    rec_id = recording["id"]
    duration = recording.get("duration_seconds", 0) or 0
    
    print(f"{i}. Reprocessing {rec_id[:8]}... ({duration:.0f}s)")
    
    result = run_cmd(f'''curl -s -X POST \
-H "Authorization: Bearer {token}" \
"http://localhost:8000/api/v1/recordings/{rec_id}/reprocess"''')
    
    if "pipeline triggered" in result.lower() or "200" in result:
        print(f"   ✓ Pipeline triggered")
    else:
        print(f"   ⚠️  Response: {result[:100]}")
    
    time.sleep(2)

print("\n✅ All reprocessing tasks triggered!")
print("⏳ Pipeline will run in background. Check Celery logs for progress.")
