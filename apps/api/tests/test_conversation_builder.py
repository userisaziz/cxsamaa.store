"""Unit tests for conversation turn builder."""
import pytest
from src.ai.conversation_builder import build_conversation_turns


class TestBuildConversationTurns:
    """Test suite for build_conversation_turns function."""

    def test_empty_transcripts(self):
        """Test with empty word_transcripts returns empty list."""
        result = build_conversation_turns([])
        assert result == []

    def test_single_word(self):
        """Test with single word creates single turn."""
        words = [
            {"word": "Hello", "start_time": 0.1, "end_time": 0.5, "speaker_label": "Speaker_A"}
        ]
        result = build_conversation_turns(words)
        assert len(result) == 1
        assert result[0]["speaker"] == "Speaker_A"
        assert result[0]["text"] == "Hello"
        assert result[0]["word_count"] == 1
        assert result[0]["start_time"] == 0.1
        assert result[0]["end_time"] == 0.5

    def test_same_speaker_small_gaps(self):
        """Test merging words into single turn (same speaker, small gaps)."""
        words = [
            {"word": "Hello", "start_time": 0.1, "end_time": 0.5, "speaker_label": "Speaker_A"},
            {"word": "how", "start_time": 0.6, "end_time": 0.8, "speaker_label": "Speaker_A"},
            {"word": "are", "start_time": 0.9, "end_time": 1.1, "speaker_label": "Speaker_A"},
            {"word": "you", "start_time": 1.2, "end_time": 1.5, "speaker_label": "Speaker_A"},
        ]
        result = build_conversation_turns(words, gap_threshold=1.0)
        assert len(result) == 1
        assert result[0]["text"] == "Hello how are you"
        assert result[0]["word_count"] == 4
        assert result[0]["speaker"] == "Speaker_A"

    def test_speaker_change_creates_new_turn(self):
        """Test creating new turn on speaker change."""
        words = [
            {"word": "Hi", "start_time": 0.1, "end_time": 0.5, "speaker_label": "Speaker_A"},
            {"word": "Hello", "start_time": 1.0, "end_time": 1.5, "speaker_label": "Speaker_B"},
        ]
        result = build_conversation_turns(words)
        assert len(result) == 2
        assert result[0]["speaker"] == "Speaker_A"
        assert result[0]["text"] == "Hi"
        assert result[1]["speaker"] == "Speaker_B"
        assert result[1]["text"] == "Hello"

    def test_gap_exceeded_creates_new_turn(self):
        """Test creating new turn when gap exceeds threshold (same speaker)."""
        words = [
            {"word": "Hello", "start_time": 0.1, "end_time": 0.5, "speaker_label": "Speaker_A"},
            {"word": "world", "start_time": 2.0, "end_time": 2.5, "speaker_label": "Speaker_A"},  # Gap > 1s
        ]
        result = build_conversation_turns(words, gap_threshold=1.0)
        assert len(result) == 2
        assert result[0]["text"] == "Hello"
        assert result[1]["text"] == "world"

    def test_multiple_speakers_alternating(self):
        """Test multiple speaker changes."""
        words = [
            {"word": "Hi", "start_time": 0.1, "end_time": 0.5, "speaker_label": "Speaker_A"},
            {"word": "Hello", "start_time": 1.0, "end_time": 1.5, "speaker_label": "Speaker_B"},
            {"word": "How", "start_time": 2.0, "end_time": 2.3, "speaker_label": "Speaker_A"},
            {"word": "are", "start_time": 2.4, "end_time": 2.6, "speaker_label": "Speaker_A"},
            {"word": "you", "start_time": 3.0, "end_time": 3.5, "speaker_label": "Speaker_B"},
        ]
        result = build_conversation_turns(words)
        assert len(result) == 4
        assert result[0]["speaker"] == "Speaker_A"
        assert result[1]["speaker"] == "Speaker_B"
        assert result[2]["speaker"] == "Speaker_A"
        assert result[3]["speaker"] == "Speaker_B"
        assert result[2]["text"] == "How are"  # Merged due to small gap

    def test_custom_gap_threshold(self):
        """Test custom gap threshold parameter."""
        words = [
            {"word": "Hello", "start_time": 0.1, "end_time": 0.5, "speaker_label": "Speaker_A"},
            {"word": "world", "start_time": 1.2, "end_time": 1.5, "speaker_label": "Speaker_A"},  # Gap 0.7s
        ]

        # With 1.0s threshold, should split (gap > threshold)
        result_1s = build_conversation_turns(words, gap_threshold=1.0)
        assert len(result_1s) == 2

        # With 2.0s threshold, should merge (gap < threshold)
        result_2s = build_conversation_turns(words, gap_threshold=2.0)
        assert len(result_2s) == 1
        assert result_2s[0]["text"] == "Hello world"

    def test_text_spacing_cleanup(self):
        """Test that text spacing is cleaned up properly."""
        words = [
            {"word": "Hello", "start_time": 0.1, "end_time": 0.5, "speaker_label": "Speaker_A"},
            {"word": ",", "start_time": 0.5, "end_time": 0.5, "speaker_label": "Speaker_A"},
            {"word": "world", "start_time": 0.6, "end_time": 1.0, "speaker_label": "Speaker_A"},
        ]
        result = build_conversation_turns(words)
        assert len(result) == 1
        # Should clean up spacing around punctuation
        assert result[0]["text"] == "Hello, world"

    def test_timestamps_rounded(self):
        """Test that timestamps are rounded to 3 decimal places."""
        words = [
            {"word": "Hello", "start_time": 0.123456, "end_time": 0.567890, "speaker_label": "Speaker_A"}
        ]
        result = build_conversation_turns(words)
        assert result[0]["start_time"] == 0.123
        assert result[0]["end_time"] == 0.568

    def test_long_turn(self):
        """Test handling of very long turns (>30s)."""
        words = [
            {"word": f"word{i}", "start_time": float(i), "end_time": float(i + 0.5), "speaker_label": "Speaker_A"}
            for i in range(100)  # 100 words, ~100 seconds
        ]
        result = build_conversation_turns(words)
        assert len(result) == 1
        assert result[0]["word_count"] == 100
        assert result[0]["end_time"] - result[0]["start_time"] > 30.0
