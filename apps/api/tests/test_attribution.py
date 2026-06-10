"""Unit tests for word-level speaker attribution."""
import pytest
from src.ai.attribution import assign_speaker_to_word


class TestWordAttribution:
    """Test suite for word-level speaker attribution."""

    def test_empty_words(self):
        """Test with empty words returns empty list."""
        result = assign_speaker_to_word([], [])
        assert result == []

    def test_no_diarization_segments(self):
        """Test attribution without diarization marks all as UNKNOWN."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "world", "start": 0.6, "end": 1.0, "confidence": 0.95},
        ]
        result = assign_speaker_to_word(words, [])
        assert len(result) == 2
        assert result[0]["speaker"] == "UNKNOWN"
        assert result[1]["speaker"] == "UNKNOWN"

    def test_single_speaker_attribution(self):
        """Test attribution with single speaker covering full audio."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "world", "start": 0.6, "end": 1.0, "confidence": 0.95},
        ]
        segments = [
            {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
        ]
        result = assign_speaker_to_word(words, segments)
        assert len(result) == 2
        assert result[0]["speaker"] == "Speaker_A"
        assert result[1]["speaker"] == "Speaker_A"

    def test_multi_speaker_attribution(self):
        """Test attribution with multiple speakers."""
        words = [
            {"word": "Hi", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "Hello", "start": 5.0, "end": 5.5, "confidence": 0.95},
        ]
        segments = [
            {"start": 0.0, "end": 4.0, "speaker": "SPEAKER_00"},
            {"start": 4.5, "end": 10.0, "speaker": "SPEAKER_01"},
        ]
        result = assign_speaker_to_word(words, segments)
        assert len(result) == 2
        assert result[0]["speaker"] == "Speaker_A"
        assert result[1]["speaker"] == "Speaker_B"

    def test_word_attribution_gap_fallback(self):
        """Test attribution when word falls between diarization segments."""
        words = [
            {"word": "Hello", "start": 4.2, "end": 4.5, "confidence": 0.98},
        ]
        segments = [
            {"start": 0.0, "end": 4.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
        ]
        result = assign_speaker_to_word(words, segments)
        # Word at 4.35 (midpoint), should use nearest segment (SPEAKER_00 at distance 0.35s)
        assert len(result) == 1
        assert result[0]["speaker"] == "Speaker_A"

    def test_speaker_normalization(self):
        """Test that SPEAKER_XX is normalized to Speaker_X."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
        ]
        segments = [
            {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_05"},
        ]
        result = assign_speaker_to_word(words, segments)
        # Should normalize to Speaker_A (first unique speaker)
        assert result[0]["speaker"] == "Speaker_A"

    def test_word_metadata_preserved(self):
        """Test that word metadata is preserved after attribution."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
        ]
        segments = [
            {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
        ]
        result = assign_speaker_to_word(words, segments)
        assert result[0]["word"] == "Hello"
        assert result[0]["start"] == 0.1
        assert result[0]["end"] == 0.5
        assert result[0]["confidence"] == 0.98
        assert "speaker" in result[0]

    def test_rapid_speaker_changes(self):
        """Test rapid speaker changes in conversation."""
        words = [
            {"word": "Hi", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "Hello", "start": 1.0, "end": 1.5, "confidence": 0.95},
            {"word": "How", "start": 2.0, "end": 2.3, "confidence": 0.92},
            {"word": "are", "start": 2.4, "end": 2.6, "confidence": 0.91},
        ]
        segments = [
            {"start": 0.0, "end": 1.5, "speaker": "SPEAKER_00"},
            {"start": 1.5, "end": 3.0, "speaker": "SPEAKER_01"},
        ]
        result = assign_speaker_to_word(words, segments)
        assert len(result) == 4
        assert result[0]["speaker"] == "Speaker_A"  # 0.3 midpoint
        assert result[1]["speaker"] == "Speaker_B"  # 1.25 midpoint
        assert result[2]["speaker"] == "Speaker_B"  # 2.15 midpoint
        assert result[3]["speaker"] == "Speaker_B"  # 2.5 midpoint
