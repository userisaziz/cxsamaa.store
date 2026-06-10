"""Unit tests for Silero VAD integration."""
import pytest
from unittest.mock import patch, MagicMock
from src.ai.vad import detect_speech_segments, extract_speech_regions
from src.config import settings


class TestSileroVAD:
    """Test suite for Silero VAD speech detection."""

    @patch("src.ai.vad.settings")
    def test_vad_disabled_returns_empty(self, mock_settings):
        """Test VAD_USE_SILERO=false returns empty list."""
        mock_settings.vad_use_silero = False
        mock_settings.vad_threshold = 0.5

        # Mock audio bytes
        mock_audio = b"\x00" * 1000

        result = detect_speech_segments(mock_audio)
        assert result == []

    @patch("src.ai.vad._get_silero_vad_model")
    @patch("src.ai.vad.settings")
    def test_vad_model_load_failure_returns_empty(self, mock_settings, mock_get_model):
        """Test VAD model load failure returns empty list."""
        mock_settings.vad_use_silero = True
        mock_get_model.return_value = (None, None)

        mock_audio = b"\x00" * 1000
        result = detect_speech_segments(mock_audio)
        assert result == []

    @patch("src.ai.vad.settings")
    def test_extract_speech_regions_no_segments(self, mock_settings):
        """Test extract_speech_regions with empty segments returns original audio."""
        mock_settings.vad_use_silero = True

        mock_audio = b"\x00" * 1000
        result = extract_speech_regions(mock_audio, [])

        # Should return original audio when no segments
        assert result == mock_audio

    @patch("src.ai.vad.settings")
    def test_extract_speech_regions_with_segments(self, mock_settings):
        """Test extract_speech_regions extracts only speech regions."""
        mock_settings.vad_use_silero = True

        # This test would require actual audio processing
        # For now, just verify the function doesn't crash
        mock_audio = b"\x00" * 1000
        speech_segments = [
            {"start": 0.0, "end": 0.5},
            {"start": 1.0, "end": 1.5},
        ]

        try:
            result = extract_speech_regions(mock_audio, speech_segments)
            # Function should return bytes
            assert isinstance(result, bytes)
        except Exception as e:
            # Expected if torchaudio not available
            assert "torchaudio" in str(e) or "audio" in str(e).lower()
