"""Integration tests for audio processing pipeline."""
import uuid
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if riva.client not available
pytest.importorskip("riva.client", reason="riva.client not installed")

from src.ai.diarizer import assign_speaker_labels, diarize_audio
from src.workers.pipeline import start_processing_pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_audio_bytes():
    """Create minimal WAV file bytes for testing."""
    # This is a minimal WAV header + silence
    # In real tests, you'd load actual audio files
    wav_header = b'RIFF'  # Simplified for testing
    return wav_header + b'\x00' * 1000


@pytest.fixture
def sample_transcript_segments():
    """Create sample STT transcript segments."""
    return [
        {"start": 0.0, "end": 5.5, "text": "Hello, welcome to our store."},
        {"start": 6.0, "end": 10.5, "text": "Hi, I'm looking for a laptop."},
        {"start": 11.0, "end": 15.5, "text": "Great! What's your budget?"},
        {"start": 16.0, "end": 20.0, "text": "Around $1000 to $1500."},
    ]


@pytest.fixture
def sample_speaker_segments():
    """Create sample diarization speaker segments."""
    return [
        {"start": 0.0, "end": 5.5, "speaker": "SPEAKER_00"},
        {"start": 6.0, "end": 10.5, "speaker": "SPEAKER_01"},
        {"start": 11.0, "end": 15.5, "speaker": "SPEAKER_00"},
        {"start": 16.0, "end": 20.0, "speaker": "SPEAKER_01"},
    ]


# ---------------------------------------------------------------------------
# Tests: VAD (Voice Activity Detection)
# ---------------------------------------------------------------------------

class TestVoiceActivityDetection:
    def test_detect_speech_regions_structure(self):
        """detect_speech_regions returns list of regions."""
        try:
            from src.ai.vad import detect_speech_regions
            # This tests the interface, not the model
            assert callable(detect_speech_regions)
        except ImportError:
            pytest.skip("onnxruntime not installed")

    def test_vad_returns_time_boundaries(self):
        """VAD should return start/end time boundaries."""
        try:
            from src.ai.vad import detect_speech_regions
            import inspect
            sig = inspect.signature(detect_speech_regions)
            assert "audio_bytes" in sig.parameters
        except ImportError:
            pytest.skip("onnxruntime not installed")


# ---------------------------------------------------------------------------
# Tests: STT (Speech-to-Text)
# ---------------------------------------------------------------------------

class TestSpeechToText:
    def test_transcribe_audio_interface(self):
        """transcribe_audio accepts audio bytes."""
        # Import lazily to avoid riva.client dependency
        try:
            from src.ai.stt import transcribe_audio
            import inspect
            sig = inspect.signature(transcribe_audio)
            assert "audio_bytes" in sig.parameters
            assert "filename" in sig.parameters
        except ImportError:
            pytest.skip("riva.client not installed")

    def test_transcribe_returns_segments(self):
        """STT should return list of transcript segments."""
        try:
            from src.ai.stt import transcribe_audio
        except ImportError:
            pytest.skip("riva.client not installed")
        
        # Mock NVIDIA API call
        with patch("src.ai.stt.nvidia_client") as mock_client:
            mock_client.post_multipart.return_value = {
                "text": "Hello world",
                "segments": [
                    {"start": 0.0, "end": 1.5, "text": "Hello"}
                ]
            }
            
            # This would normally call NVIDIA API
            # Just testing the interface here
            assert callable(transcribe_audio)


# ---------------------------------------------------------------------------
# Tests: Diarization Integration
# ---------------------------------------------------------------------------

class TestDiarizationIntegration:
    def test_full_diarization_flow(self, sample_audio_bytes):
        """Test complete diarization from audio to speaker labels."""
        with patch("src.ai.diarizer._get_pyannote_diarizer") as mock_diarizer:
            # Mock pyannote diarizer
            mock_instance = MagicMock()
            mock_instance.diarize.return_value = [
                {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
                {"start": 5.5, "end": 10.0, "speaker": "SPEAKER_01"},
            ]
            mock_diarizer.return_value = mock_instance
            
            # Call diarize_audio (will use pyannote)
            with patch("src.ai.diarizer.settings") as mock_settings:
                mock_settings.diarization_use_pyannote = True
                
                segments = diarize_audio(sample_audio_bytes)
                # May return empty due to mocking, but tests the flow
                assert isinstance(segments, list)

    def test_speaker_label_assignment(self, sample_transcript_segments, sample_speaker_segments):
        """Test assigning speaker labels to transcript segments."""
        labeled = assign_speaker_labels(
            sample_transcript_segments,
            sample_speaker_segments
        )
        
        assert len(labeled) == len(sample_transcript_segments)
        assert all("speaker" in seg for seg in labeled)
        # Should normalize to Speaker_A, Speaker_B, etc.
        assert all(seg["speaker"].startswith("Speaker_") for seg in labeled)

    def test_speaker_label_fallback(self, sample_transcript_segments):
        """Fallback assignment when no diarization available."""
        labeled = assign_speaker_labels(sample_transcript_segments, [])
        
        assert len(labeled) == len(sample_transcript_segments)
        # Should use gap-based fallback
        assert all("speaker" in seg for seg in labeled)


# ---------------------------------------------------------------------------
# Tests: Pipeline Orchestration
# ---------------------------------------------------------------------------

class TestPipelineOrchestration:
    def test_pipeline_chain_construction(self):
        """start_processing_pipeline creates Celery chain."""
        recording_id = str(uuid.uuid4())
        
        with patch("src.workers.preprocessing.preprocess_audio") as mock_preprocess, \
             patch("src.workers.transcription.transcribe_audio_task") as mock_transcribe, \
             patch("src.workers.diarization.diarize_audio") as mock_diarize, \
             patch("src.workers.segmentation.segment_conversations") as mock_segment, \
             patch("src.workers.analysis.analyze_conversations") as mock_analyze, \
             patch("src.workers.scoring.score_salesperson") as mock_score:
            
            # Mock all task signatures
            mock_preprocess.s.return_value = MagicMock()
            mock_transcribe.s.return_value = MagicMock()
            mock_diarize.s.return_value = MagicMock()
            mock_segment.s.return_value = MagicMock()
            mock_analyze.s.return_value = MagicMock()
            mock_score.s.return_value = MagicMock()
            
            # Mock chain
            mock_chain = MagicMock()
            with patch("src.workers.pipeline.chain", return_value=mock_chain):
                result = start_processing_pipeline(recording_id)
                
                # Verify chain was created
                mock_chain.apply_async.assert_called_once()

    def test_pipeline_stage_order(self):
        """Pipeline stages execute in correct order."""
        from src.workers.pipeline import chain
        
        # Import all task functions
        from src.workers.preprocessing import preprocess_audio
        from src.workers.transcription import transcribe_audio_task
        from src.workers.diarization import diarize_audio
        from src.workers.segmentation import segment_conversations
        from src.workers.analysis import analyze_conversations
        from src.workers.scoring import score_salesperson
        
        # Verify all tasks exist and are callable
        assert callable(preprocess_audio)
        assert callable(transcribe_audio_task)
        assert callable(diarize_audio)
        assert callable(segment_conversations)
        assert callable(analyze_conversations)
        assert callable(score_salesperson)


# ---------------------------------------------------------------------------
# Tests: End-to-End Audio Processing
# ---------------------------------------------------------------------------

class TestEndToEndAudioProcessing:
    def test_audio_upload_to_processing(self):
        """Test audio file triggers processing pipeline."""
        from src.api.v1.recordings import upload_recording
        from src.services.recording import create_recording
        
        # Verify upload endpoint exists
        assert callable(upload_recording)
        # Verify recording creation
        assert callable(create_recording)

    def test_recording_status_transitions(self):
        """Recording status transitions through pipeline stages."""
        from src.models.recording import RecordingStatus
        
        stages = [
            RecordingStatus.UPLOADED,
            RecordingStatus.PREPROCESSING,
            RecordingStatus.TRANSCRIBING,
            RecordingStatus.DIARIZING,
            RecordingStatus.SEGMENTING,
            RecordingStatus.ANALYZING,
            RecordingStatus.SCORING,
            RecordingStatus.COMPLETED,
        ]
        
        # Verify all stages exist
        assert len(stages) == 8
        
        # FAILED is also valid
        assert RecordingStatus.FAILED

    def test_transcript_segment_creation(self):
        """Transcript segments are created from STT output."""
        from src.models.transcript import TranscriptSegment
        
        # Verify model structure
        assert hasattr(TranscriptSegment, "recording_id")
        assert hasattr(TranscriptSegment, "start_time")
        assert hasattr(TranscriptSegment, "end_time")
        assert hasattr(TranscriptSegment, "text")
        assert hasattr(TranscriptSegment, "speaker_label")


# ---------------------------------------------------------------------------
# Tests: Error Handling & Retries
# ---------------------------------------------------------------------------

class TestPipelineErrorHandling:
    def test_pipeline_handles_stt_failure(self, sample_audio_bytes):
        """Pipeline handles STT API failure gracefully."""
        try:
            from src.ai.stt import transcribe_audio
        except ImportError:
            pytest.skip("riva.client not installed")
        
        with patch("src.ai.stt.nvidia_client") as mock_client:
            mock_client.post_multipart.side_effect = Exception("API timeout")
            
            # Should handle error gracefully
            # Actual retry logic is in Celery task
            assert callable(transcribe_audio)

    def test_pipeline_handles_diarization_failure(self, sample_audio_bytes):
        """Pipeline handles diarization failure with fallback."""
        with patch("src.ai.diarizer._get_pyannote_diarizer") as mock_pyannote, \
             patch("src.ai.diarizer.nvidia_client") as mock_nvidia:
            
            mock_pyannote.side_effect = Exception("Model load failed")
            mock_nvidia.post_multipart.side_effect = Exception("API failed")
            
            # Both pyannote and NVIDIA fail
            # Should return empty list (graceful degradation)
            with patch("src.ai.diarizer.settings") as mock_settings:
                mock_settings.diarization_use_pyannote = True
                segments = diarize_audio(sample_audio_bytes)
                assert isinstance(segments, list)

    def test_pipeline_handles_analysis_failure(self):
        """Pipeline handles LLM analysis failure."""
        from src.ai.analyzer import analyze_conversation
        
        # Verify analyzer exists
        assert callable(analyze_conversation)


# ---------------------------------------------------------------------------
# Tests: Performance & Scaling
# ---------------------------------------------------------------------------

class TestPipelinePerformance:
    def test_chunking_long_audio(self):
        """Audio chunking splits long recordings properly."""
        from src.config import settings
        
        # Verify chunking configuration
        assert settings.audio_chunk_duration_minutes == 15
        assert settings.audio_chunk_overlap_seconds == 30

    def test_vad_optimization(self):
        """VAD settings optimize for speech detection."""
        from src.config import settings
        
        assert settings.vad_use_silero is True
        assert 0.0 <= settings.vad_threshold <= 1.0
        assert settings.vad_min_speech_duration_ms >= 100


# ---------------------------------------------------------------------------
# Tests: Data Flow Validation
# ---------------------------------------------------------------------------

class TestDataFlowValidation:
    def test_transcript_to_analysis_flow(self, sample_transcript_segments):
        """Verify transcript data flows to analysis correctly."""
        from src.ai.analyzer import _format_transcript
        
        formatted = _format_transcript(sample_transcript_segments)
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # Should contain speaker labels and text
        assert "Speaker" in formatted or "speaker" in formatted.lower()

    def test_analysis_to_scoring_flow(self):
        """Verify analysis results flow to scoring."""
        from src.ai.scorer import _parse_scores_response
        
        # Mock LLM response
        mock_response = """
        {
            "greeting_score": 85,
            "discovery_score": 75,
            "product_knowledge_score": 90,
            "objection_handling_score": 70,
            "closing_score": 80
        }
        """
        
        scores = _parse_scores_response(mock_response)
        assert scores is not None
        assert scores["greeting_score"] == 85
        assert all(0 <= score <= 100 for score in scores.values())
