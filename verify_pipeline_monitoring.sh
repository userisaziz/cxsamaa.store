#!/bin/bash
# Quick verification script for new pipeline monitoring features

echo "🔍 Verifying Pipeline Monitoring Setup..."
echo ""

# 1. Test new pipeline endpoint
echo "1️⃣  Testing /recordings/pipeline/active endpoint..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@samaa.com","password":"admin123"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi

echo "✅ Logged in successfully"

# Test the new endpoint
PIPELINE_RESP=$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/recordings/pipeline/active)

HTTP_CODE=$(echo "$PIPELINE_RESP" | tail -n 1)
BODY=$(echo "$PIPELINE_RESP" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  ACTIVE_COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  echo "✅ Pipeline endpoint working! Active recordings: $ACTIVE_COUNT"
else
  echo "❌ Pipeline endpoint failed (HTTP $HTTP_CODE)"
  echo "$BODY"
  exit 1
fi

echo ""
echo "2️⃣  Checking current recordings..."
RECORDINGS=$(curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/recordings?page=1&page_size=5")

TOTAL=$(echo "$RECORDINGS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])")
echo "📊 Total recordings in database: $TOTAL"

echo ""
echo "3️⃣  Storage backend configuration..."
STORAGE_BACKEND=$(grep STORAGE_BACKEND .env | head -1 | cut -d'=' -f2)
echo "💾 Current storage: ${STORAGE_BACKEND:-local}"

echo ""
echo "4️⃣  Celery worker status..."
if pgrep -f "celery" > /dev/null; then
  echo "✅ Celery worker is running"
else
  echo "⚠️  Celery worker not detected"
fi

echo ""
echo "5️⃣  Frontend Operations page..."
if curl -s http://localhost:3000/operations | grep -q "Upload Recording"; then
  echo "✅ Operations page accessible at http://localhost:3000/operations"
else
  echo "⚠️  Operations page may have issues"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Verification complete!"
echo ""
echo "📍 Next steps:"
echo "   1. Open http://localhost:3000/operations"
echo "   2. Upload a test audio file"
echo "   3. Watch it appear in 'Active Pipeline Processing'"
echo "   4. Monitor real-time status updates (polls every 3s)"
echo ""
echo "📖 Full guide: PRODUCTION_TESTING_GUIDE.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
