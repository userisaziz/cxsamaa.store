"""Pipeline health check unit tests.

Run these tests BEFORE reprocessing to ensure all pipeline stages are working.

Usage:
  cd /Users/almabetter/xsamaa-ai-pipeline/apps/api
  PYTHONPATH=$(pwd) uv run pytest tests/test_pipeline_health.py -v
"""
import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime

# Skip if critical dependencies missing
pytest.importorskip("celery", reason="Celery not installed")

from src.models.recording import Recording, RecordingStatus
from src.workers.pipeline import STAGES, run_stage, get_active_stages
from src.services.pipeline_progress import (
    update_pipeline_progress,
    log_stage_start,
    log_stage_complete,
    log_stage_error,
)


class TestPipelineConfiguration:
    """Test pipeline stage configuration is correct."""
    
    def test_pipeline_has_9_stages_when_diarization_enabled(self):
        """Pipeline should have 9 stages when diarization is enabled."""
        from src.config import settings
        if settings.enable_diarization:
            assert len(STAGES) == 9, f"Expected 9 stages, got {len(STAGES)}"
        else:
            assert len(STAGES) == 9, "STAGES constant should always define 9 stages"
            active = get_active_stages()
            assert len(active) == 8, f"Expected 8 active stages when diarization disabled, got {len(active)}"
    
    def test_stage_names_are_valid(self):
        """All stage names should be non-empty strings."""
        for path, func, status in STAGES:
            assert isinstance(path, str) and len(path) > 0
            assert callable(func), f"Stage {path} function is not callable"
            assert isinstance(status, str) and len(status) > 0
    
    def test_stage_order_is_correct(self):
        """Stages should be in correct execution order."""
        from src.config import settings
        
        expected_order_full = [
            "preprocess",
            "stt",
            "diarization",
            "turns",
            "roles",
            "segmentation",
            "extract-audio",
            "analyze",
            "scoring",
        ]
        
        expected_order_no_diar = [
            "preprocess",
            "stt",
            # diarization skipped
            "turns",
            "roles",
            "segmentation",
            "extract-audio",
            "analyze",
            "scoring",
        ]
        
        active_stages = get_active_stages()
        actual_order = [path.split("/")[-1] for path, _, _ in active_stages]
        
        if settings.enable_diarization:
            assert actual_order == expected_order_full, f"Stage order mismatch: {actual_order}"
        else:
            assert actual_order == expected_order_no_diar, f"Stage order mismatch: {actual_order}"
    
    def test_status_labels_match_enum(self):
        """All status labels should be valid RecordingStatus enum values."""
        valid_statuses = {s.value for s in RecordingStatus}
        
        for _, _, status_label in STAGES:
            assert status_label in valid_statuses, f"Invalid status: {status_label}"


class TestPipelineProgressTracking:
    """Test progress tracking functions work correctly."""
    
    @patch('src.workers.preprocessing._update_recording_status_sync')
    def test_log_stage_start_updates_db(self, mock_update):
        """log_stage_start should call DB update."""
        log_stage_start("test-id", "stt", total_stages=9, current_index=1)
        
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == "test-id"
        # update_pipeline_progress prepends "Processing stage X/Y: name — " before the message
        assert "Starting stage 2/9: stt" in call_args[0][2]
    
    @patch('src.workers.preprocessing._update_recording_status_sync')
    def test_log_stage_complete_updates_db(self, mock_update):
        """log_stage_complete should call DB update."""
        log_stage_complete("test-id", "stt", total_stages=9, current_index=1)
        
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert "Completed stage 2/9" in call_args[0][2]
    
    @patch('src.workers.preprocessing._update_recording_status_sync')
    def test_log_stage_error_updates_db(self, mock_update):
        """log_stage_error should call DB update with error message."""
        log_stage_error("test-id", "stt", "Test error", total_stages=9, current_index=1)
        
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert "Failed at stage 2/9" in call_args[0][2]
        assert "Test error" in call_args[0][2]


class TestPipelineStageFunctions:
    """Test individual stage functions exist and are callable."""
    
    def test_preprocess_function_exists(self):
        """preprocess_audio function should exist."""
        from src.workers.preprocessing import preprocess_audio
        assert callable(preprocess_audio)
    
    def test_transcription_function_exists(self):
        """dispatch_transcription function should exist."""
        from src.workers.transcription import dispatch_transcription
        assert callable(dispatch_transcription)
    
    def test_diarization_function_exists(self):
        """dispatch_diarization function should exist."""
        from src.workers.diarization import dispatch_diarization
        assert callable(dispatch_diarization)
    
    def test_turn_builder_function_exists(self):
        """build_conversation_turns function should exist."""
        from src.workers.turn_builder import build_conversation_turns
        assert callable(build_conversation_turns)
    
    def test_role_classification_function_exists(self):
        """classify_speaker_roles function should exist."""
        from src.workers.role_classification import classify_speaker_roles
        assert callable(classify_speaker_roles)
    
    def test_segmentation_function_exists(self):
        """segment_conversations function should exist."""
        from src.workers.segmentation import segment_conversations
        assert callable(segment_conversations)
    
    def test_audio_stitcher_function_exists(self):
        """extract_conversation_audio function should exist."""
        from src.workers.audio_stitcher import extract_conversation_audio
        assert callable(extract_conversation_audio)
    
    def test_analysis_function_exists(self):
        """analyze_conversations function should exist."""
        from src.workers.analysis import analyze_conversations
        assert callable(analyze_conversations)
    
    def test_scoring_function_exists(self):
        """score_salesperson function should exist."""
        from src.workers.scoring import score_salesperson
        assert callable(score_salesperson)


class TestCeleryWorkerConfiguration:
    """Test Celery worker is properly configured."""
    
    def test_celery_app_imports(self):
        """Celery app should import successfully."""
        from src.workers.celery_app import app
        assert app is not None
        assert app.conf.broker_url == 'redis://localhost:6379/0'
    
    def test_pipeline_worker_task_registered(self):
        """execute_stage task should be registered."""
        from src.workers.celery_app import app
        # Task should be in registry
        assert 'src.workers.pipeline_worker.execute_stage' in app.tasks
    
    def test_retry_decorator_exists(self):
        """pipeline_retry decorator should exist."""
        from src.workers.retry import pipeline_retry
        assert pipeline_retry is not None


class TestDatabaseConnectivity:
    """Test database connection is working."""
    
    def test_database_connection(self):
        """Should be able to connect to database."""
        from sqlalchemy import create_engine
        from src.config import settings
        
        engine = create_engine(settings.database_url_sync)
        try:
            with engine.connect() as conn:
                # Simple query to test connection
                from sqlalchemy import text
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            engine.dispose()
    
    def test_recording_model_accessible(self):
        """Should be able to query Recording model."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.config import settings
        
        engine = create_engine(settings.database_url_sync)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Count recordings
            count = session.query(Recording).count()
            assert count >= 0  # Should not raise error
        finally:
            session.close()
            engine.dispose()


class TestRedisConnectivity:
    """Test Redis connection for Celery."""
    
    def test_redis_connection(self):
        """Should be able to connect to Redis."""
        import redis
        from src.config import settings
        
        r = redis.from_url(settings.redis_url)
        try:
            # Ping Redis
            assert r.ping() is True
        finally:
            r.close()


class TestRecordingStatusEnum:
    """Test RecordingStatus enum has all required values."""
    
    def test_all_pipeline_statuses_exist(self):
        """All pipeline stage statuses should exist."""
        required_statuses = [
            "UPLOADED",
            "PREPROCESSING",
            "TRANSCRIBING",
            "DIARIZING",
            "RECONCILING",
            "SEGMENTING",
            "STITCHING",
            "ANALYZING",
            "SCORING",
            "COMPLETED",
            "FAILED",
        ]
        
        for status_name in required_statuses:
            assert hasattr(RecordingStatus, status_name), f"Missing status: {status_name}"
    
    def test_status_values_are_strings(self):
        """All status values should be strings."""
        for status in RecordingStatus:
            assert isinstance(status.value, str)


class TestStageExecution:
    """Test stage execution logic (mocked)."""
    
    def test_run_stage_executes_function(self):
        """run_stage should execute stage function and log progress."""
        from src.workers.pipeline import STAGES
        recording_id = str(uuid.uuid4())
        mock_func = MagicMock()
        original = STAGES[0]
        STAGES[0] = (original[0], mock_func, original[2])

        try:
            with patch('src.services.pipeline_state.is_stage_completed_sync', return_value=False), \
                 patch('src.workers.pipeline._get_recording_sync', return_value=None), \
                 patch('src.workers.pipeline._update_status'), \
                 patch('src.workers.pipeline.log_stage_start'), \
                 patch('src.workers.pipeline.log_stage_complete'), \
                 patch('src.workers.pipeline.settings') as mock_settings, \
                 patch('src.workers.pipeline_worker.enqueue_next_stage_celery'):

                mock_settings.app_env = "development"
                run_stage(recording_id, "v1", stage_index=0)

                mock_func.assert_called_once_with(recording_id)
        finally:
            STAGES[0] = original

    def test_run_stage_handles_errors(self):
        """run_stage should handle and log errors."""
        from src.workers.pipeline import STAGES
        recording_id = str(uuid.uuid4())
        failing_func = MagicMock(side_effect=Exception("Test error"))
        original = STAGES[0]
        STAGES[0] = (original[0], failing_func, original[2])

        try:
            with patch('src.services.pipeline_state.is_stage_completed_sync', return_value=False), \
                 patch('src.services.pipeline_state.mark_stage_failed_sync'), \
                 patch('src.services.pipeline_state.get_state_sync', return_value={"retry_count": {}}), \
                 patch('src.workers.pipeline._get_recording_sync', return_value=None), \
                 patch('src.workers.pipeline._update_status'), \
                 patch('src.workers.pipeline.log_stage_start'), \
                 patch('src.workers.pipeline.log_stage_error') as mock_log_error:

                with pytest.raises(Exception, match="Test error"):
                    run_stage(recording_id, "v1", stage_index=0)

                mock_log_error.assert_called_once()
        finally:
            STAGES[0] = original


class TestPipelineStateManagement:
    """Test pipeline state management functions."""
    
    def test_create_initial_state(self):
        """Should create valid initial pipeline state."""
        from src.services.pipeline_state import create_initial_state
        
        state = create_initial_state()
        assert "current_stage" in state
        assert "completed_stages" in state
        assert "retry_count" in state
        assert state["completed_stages"] == []
    
    def test_stage_order_constant(self):
        """STAGE_ORDER should contain all stages."""
        from src.services.pipeline_state import STAGE_ORDER
        
        expected = [
            "preprocess", "stt", "diarization", "turns", "roles",
            "segmentation", "extract-audio", "analyze", "scoring"
        ]
        assert STAGE_ORDER == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
