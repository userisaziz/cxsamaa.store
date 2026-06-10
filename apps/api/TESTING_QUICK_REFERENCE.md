# SAMAA Testing Quick Reference

## 🚀 Quick Commands

### Run All Tests
```bash
cd apps/api
uv run python -m pytest tests/ -v
```

### Run with Coverage
```bash
uv run python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Run Specific Test File
```bash
# Only AI tests
uv run python -m pytest tests/test_analyzer.py tests/test_diarizer.py tests/test_segmenter.py -v

# Only service tests
uv run python -m pytest tests/test_services.py -v

# Only pipeline tests
uv run python -m pytest tests/test_pipeline_integration.py -v

# Only API route tests
uv run python -m pytest tests/test_api_routes.py -v
```

### Run Only Passing Tests (Skip Failing)
```bash
uv run python -m pytest tests/ -k "not test_api_routes"
```

### Generate HTML Coverage Report
```bash
uv run python -m pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Run Tests Matching Pattern
```bash
# Only authentication tests
uv run python -m pytest tests/ -k "auth" -v

# Only diarization tests  
uv run python -m pytest tests/ -k "diariz" -v

# Only tests with "pipeline" in name
uv run python -m pytest tests/ -k "pipeline" -v
```

---

## 📊 Current Status

```
✅ 126 tests PASSED (87%)
❌ 17 tests FAILED (12% - API route tests need DB fixtures)
⏭️ 1 test SKIPPED (<1% - requires riva.client)
📈 39.25% Coverage (target: 75%)
```

---

## ✅ Passing Test Suites

| Test File | Tests | Status | Coverage Impact |
|-----------|-------|--------|----------------|
| `test_analyzer.py` | 13 | ✅ All Pass | +61% analyzer.py |
| `test_diarizer.py` | 9 | ✅ All Pass | +62% diarizer.py |
| `test_segmenter.py` | 22 | ✅ All Pass | +92% segmenter.py |
| `test_services.py` | 21 | ✅ All Pass | +90% auth.py |
| `test_pipeline_integration.py` | 18 | ⏭️ 1 Skip | Pipeline validation |
| `test_api_routes.py` | 28 | ❌ 17 Fail | Needs fixing |

---

## 🔧 Fix Failing API Tests

The 17 failing API tests need proper database fixtures. Here's how to fix them:

### Option 1: Use Test Database (Recommended)
```bash
# Create test database
createdb samaa_test

# Set test environment variable
export DATABASE_URL=postgresql+asyncpg://samaa:samaa_dev_password@localhost:5432/samaa_test

# Run tests with database
uv run python -m pytest tests/test_api_routes.py -v
```

### Option 2: Mock Database (Quick Fix)
Update `test_api_routes.py` to use comprehensive mocking:
```python
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

@pytest.fixture
def test_client_with_db():
    \"\"\"Test client with mocked database.\"\"\"
    with patch("src.api.v1.auth.get_db") as mock_db:
        mock_db.return_value = AsyncMock()
        yield TestClient(app)
```

---

## 📈 Coverage by Module (Top 10)

| Module | Coverage | Trend |
|--------|----------|-------|
| `src/ai/segmenter.py` | 92% | ✅ Excellent |
| `src/services/auth.py` | 90% | ✅ Excellent |
| `src/api/v1/analytics.py` | 87% | ✅ Good |
| `src/api/v1/router.py` | 100% | ✅ Perfect |
| `src/ai/analyzer.py` | 61% | ✅ Good |
| `src/ai/diarizer.py` | 62% | ✅ Good |
| `src/api/v1/brands.py` | 62% | ⚠️ Moderate |
| `src/api/v1/conversations.py` | 62% | ⚠️ Moderate |
| `src/api/v1/search.py` | 55% | ⚠️ Moderate |
| `src/ai/scorer.py` | 49% | ⚠️ Moderate |

---

## 🎯 Next Steps

### Immediate (Today)
1. ✅ **DONE**: Fix service test async mocking → **126 passing**
2. Fix API route tests → Add database fixtures → **143 passing**
3. Coverage target: **45%**

### This Week
4. Test Celery workers (preprocessing, transcription)
5. Add more AI module edge cases
6. Coverage target: **55%**

### Next Week  
7. Add integration tests with real audio files
8. Test export and analytics services end-to-end
9. Coverage target: **65%**

### This Month
10. Add frontend component tests
11. Add Playwright E2E tests
12. Coverage target: **75%** ✅

---

## 💡 Tips

### Skip Optional Dependencies
Tests automatically skip if optional packages aren't installed:
- `riva.client` (NVIDIA Riva STT)
- `onnxruntime` (Silero VAD)

### View Coverage for Specific File
```bash
uv run python -m pytest tests/ --cov=src.ai.diarizer --cov-report=term-missing
```

### Stop on First Failure
```bash
uv run python -m pytest tests/ -x  # Stop on first failure
uv run python -m pytest tests/ --maxfail=3  # Stop after 3 failures
```

### Verbose Output
```bash
uv run python -m pytest tests/ -vv  # Very verbose
uv run python -m pytest tests/ -v --tb=long  # Full tracebacks
```

### Parallel Execution (Faster)
```bash
# Install pytest-xdist
uv pip install pytest-xdist

# Run tests in parallel
uv run python -m pytest tests/ -n auto
```

---

## 📝 Test File Structure

```
tests/
├── test_analyzer.py              # ✅ AI analysis logic (166 lines)
├── test_diarizer.py              # ✅ Speaker diarization (99 lines)
├── test_segmenter.py             # ✅ Conversation segmentation (632 lines)
├── test_api_routes.py            # ⚠️ API endpoints (281 lines)
├── test_services.py              # ✅ Business logic (350 lines)
└── test_pipeline_integration.py  # ⏭️ Full pipeline (336 lines)
```

---

## 🏆 Achievements

- ✅ **126 passing tests** (from 9 initially)
- ✅ **39.25% coverage** (from ~25% initially)
- ✅ **Zero import errors** (proper skip logic)
- ✅ **Production patterns** (mocking, fixtures, async)
- ✅ **Coverage threshold** set to 30% (will increase)

---

**Last Updated**: June 10, 2026  
**Python**: 3.12.13 | **pytest**: 9.0.3 | **Coverage**: 39.25%
