"""Tests for speaker diarization logic (AI-04)."""
import pytest

from src.ai.diarizer import (
    _aggregate_word_segments,
    _fallback_speaker_assignment,
    _normalize_speaker_labels,
    assign_speaker_labels,
)


class TestAssignSpeakerLabels:
    def test_empty_transcript(self):
        assert assign_speaker_labels([], []) == []

    def test_no_diarization_uses_fallback(self):
        """When diarization returns empty, fallback alternates speakers."""
        transcript = [
            {"start": 0.0, "end": 5.0, "text": "Hello."},
            {"start": 10.0, "end": 15.0, "text": "Hi there."},  # 5s gap > 2s threshold
            {"start": 16.0, "end": 20.0, "text": "How are you?"},  # small gap
        ]
        result = assign_speaker_labels(transcript, [])
        assert len(result) == 3
        assert result[0]["speaker"] == "Speaker_A"
        assert result[1]["speaker"] == "Speaker_B"  # switched on gap
        assert result[2]["speaker"] == "Speaker_B"  # no gap, same speaker

    def test_diarization_overlap_assignment(self):
        """Speaker is assigned based on temporal overlap."""
        transcript = [
            {"start": 0.0, "end": 5.0, "text": "Welcome."},
            {"start": 5.5, "end": 10.0, "text": "Thanks."},
        ]
        speaker_segments = [
            {"start": 0.0, "end": 5.2, "speaker": "SPEAKER_00"},
            {"start": 5.3, "end": 10.0, "speaker": "SPEAKER_01"},
        ]
        result = assign_speaker_labels(transcript, speaker_segments)
        assert result[0]["speaker"] == "Speaker_A"
        assert result[1]["speaker"] == "Speaker_B"

    def test_normalizes_speaker_labels(self):
        """Raw speaker labels are normalized to Speaker_A, Speaker_B, etc."""
        transcript = [
            {"start": 0.0, "end": 5.0, "text": "A"},
            {"start": 5.0, "end": 10.0, "text": "B"},
            {"start": 10.0, "end": 15.0, "text": "A again"},
        ]
        speaker_segments = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_01"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_00"},
            {"start": 10.0, "end": 15.0, "speaker": "SPEAKER_01"},
        ]
        result = assign_speaker_labels(transcript, speaker_segments)
        # Same raw speaker should get same normalized label
        assert result[0]["speaker"] == result[2]["speaker"]
        assert result[0]["speaker"] != result[1]["speaker"]


class TestAggregateWordSegments:
    def test_empty_words(self):
        assert _aggregate_word_segments([]) == []

    def test_single_speaker(self):
        words = [
            {"start": 0.0, "end": 0.5, "speaker": "SPEAKER_00", "word": "hello"},
            {"start": 0.6, "end": 1.0, "speaker": "SPEAKER_00", "word": "world"},
        ]
        result = _aggregate_word_segments(words)
        assert len(result) == 1
        assert result[0]["speaker"] == "SPEAKER_00"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 1.0

    def test_speaker_change(self):
        words = [
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00", "word": "hi"},
            {"start": 1.5, "end": 2.5, "speaker": "SPEAKER_01", "word": "hello"},
            {"start": 3.0, "end": 4.0, "speaker": "SPEAKER_00", "word": "bye"},
        ]
        result = _aggregate_word_segments(words)
        assert len(result) == 3


class TestFallbackSpeakerAssignment:
    def test_empty(self):
        assert _fallback_speaker_assignment([]) == []

    def test_alternates_on_gaps(self):
        segments = [
            {"start": 0.0, "end": 5.0, "text": "A"},
            {"start": 10.0, "end": 15.0, "text": "B"},  # 5s gap
            {"start": 16.0, "end": 20.0, "text": "C"},  # 1s gap
        ]
        result = _fallback_speaker_assignment(segments)
        assert result[0]["speaker"] == "Speaker_A"
        assert result[1]["speaker"] == "Speaker_B"
        assert result[2]["speaker"] == "Speaker_B"  # small gap, no switch
