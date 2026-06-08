"""Tests for conversation segmentation logic (AI-05)."""
import pytest

from src.ai.segmenter import (
    GREETING_PATTERNS,
    FAREWELL_PATTERNS,
    _find_boundaries,
    _filter_conversations,
    _text_matches_patterns,
    segment_conversations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_segments(*texts_with_times: tuple[float, float, str, str]) -> list[dict]:
    """Create transcript segments: (start, end, text, speaker)."""
    return [
        {"start": s, "end": e, "text": t, "speaker": sp}
        for s, e, t, sp in texts_with_times
    ]


# ---------------------------------------------------------------------------
# Tests: Basic segmentation
# ---------------------------------------------------------------------------

class TestSegmentConversations:
    def test_empty_input(self):
        assert segment_conversations([]) == []

    def test_single_conversation_no_gaps(self):
        """Segments with no large gaps form a single conversation."""
        segments = _make_segments(
            (0.0, 5.0, "Hello, how can I help you?", "Speaker_A"),
            (5.5, 10.0, "I'm looking for a phone.", "Speaker_B"),
            (10.5, 15.0, "Let me show you our selection.", "Speaker_A"),
        )
        result = segment_conversations(segments)
        assert len(result) == 1
        assert result[0]["segment_count"] == 3
        assert result[0]["start_time"] == 0.0
        assert result[0]["end_time"] == 15.0

    def test_silence_gap_creates_boundary(self):
        """A gap > 30 seconds splits into two conversations."""
        segments = _make_segments(
            (0.0, 5.0, "Hello, welcome!", "Speaker_A"),
            (5.5, 10.0, "Thanks, I need a laptop.", "Speaker_B"),
            (50.0, 55.0, "Next customer please!", "Speaker_A"),
            (55.5, 60.0, "I want to return this.", "Speaker_C"),
        )
        result = segment_conversations(segments)
        assert len(result) == 2
        assert result[0]["end_time"] == 10.0
        assert result[1]["start_time"] == 50.0

    def test_greeting_creates_boundary(self):
        """A greeting phrase starts a new conversation even without a large gap."""
        segments = _make_segments(
            (0.0, 5.0, "That's everything, thank you.", "Speaker_A"),
            (5.5, 12.0, "Let me process that for you.", "Speaker_A"),
            (13.0, 18.0, "Good morning! Welcome to our store.", "Speaker_B"),
            (18.5, 25.0, "I'm looking for a new laptop.", "Speaker_C"),
        )
        result = segment_conversations(segments)
        assert len(result) == 2

    def test_farewell_creates_boundary(self):
        """A farewell phrase ends a conversation."""
        segments = _make_segments(
            (0.0, 5.0, "Let me check that for you.", "Speaker_A"),
            (5.5, 10.0, "Great, I'll take it.", "Speaker_B"),
            (10.5, 15.0, "Goodbye, have a nice day!", "Speaker_A"),
            (20.0, 25.0, "Welcome! How can I help you today?", "Speaker_A"),
            (25.5, 35.0, "I need to find a replacement part.", "Speaker_C"),
        )
        result = segment_conversations(segments)
        assert len(result) == 2

    def test_short_conversations_filtered(self):
        """Conversations shorter than 10s or with < 2 segments are filtered out."""
        segments = _make_segments(
            (0.0, 3.0, "Hi.", "Speaker_A"),  # too short, single segment
            (40.0, 45.0, "Hello, welcome!", "Speaker_B"),
            (45.5, 55.0, "I'm looking for shoes.", "Speaker_C"),
        )
        result = segment_conversations(segments)
        # First segment should be filtered (< 10s and < 2 segments)
        assert len(result) == 1
        assert result[0]["start_time"] == 40.0


# ---------------------------------------------------------------------------
# Tests: Boundary detection
# ---------------------------------------------------------------------------

class TestFindBoundaries:
    def test_no_boundaries(self):
        segments = _make_segments(
            (0.0, 5.0, "I need a new phone case.", "A"),
            (6.0, 10.0, "Sure, let me show you some options.", "B"),
        )
        assert _find_boundaries(segments, []) == []

    def test_silence_gap_boundary(self):
        segments = _make_segments(
            (0.0, 5.0, "Hello.", "A"),
            (50.0, 55.0, "Hi.", "B"),
        )
        boundaries = _find_boundaries(segments, [])
        assert 0 in boundaries  # boundary after segment 0

    def test_preprocessing_silence_gaps(self):
        segments = _make_segments(
            (0.0, 100.0, "Talking.", "A"),
            (200.0, 210.0, "More talking.", "B"),
        )
        # Preprocessing detected a silence gap from 100s to 200s
        silence_gaps = [(100.0, 200.0)]
        boundaries = _find_boundaries(segments, silence_gaps)
        assert 0 in boundaries


# ---------------------------------------------------------------------------
# Tests: Pattern matching
# ---------------------------------------------------------------------------

class TestPatternMatching:
    def test_greeting_patterns(self):
        assert _text_matches_patterns("Hello, welcome to our store!", GREETING_PATTERNS)
        assert _text_matches_patterns("Good morning! How can I help you?", GREETING_PATTERNS)
        assert not _text_matches_patterns("I want to buy a phone.", GREETING_PATTERNS)

    def test_farewell_patterns(self):
        assert _text_matches_patterns("Goodbye, have a nice day!", FAREWELL_PATTERNS)
        assert _text_matches_patterns("Thanks for coming, see you!", FAREWELL_PATTERNS)
        assert not _text_matches_patterns("Let me check the stock.", FAREWELL_PATTERNS)

    def test_case_insensitive(self):
        assert _text_matches_patterns("HELLO THERE", GREETING_PATTERNS)
        assert _text_matches_patterns("GOODBYE EVERYONE", FAREWELL_PATTERNS)


# ---------------------------------------------------------------------------
# Tests: Filtering
# ---------------------------------------------------------------------------

class TestFilterConversations:
    def test_filters_short_duration(self):
        conversations = [
            {"start_time": 0.0, "end_time": 5.0, "segments": [{"text": "hi"}, {"text": "hello"}], "segment_count": 2},
            {"start_time": 100.0, "end_time": 200.0, "segments": [{"text": "a"}, {"text": "b"}], "segment_count": 2},
        ]
        result = _filter_conversations(conversations)
        assert len(result) == 1
        assert result[0]["start_time"] == 100.0

    def test_filters_single_segment(self):
        conversations = [
            {"start_time": 0.0, "end_time": 30.0, "segments": [{"text": "hi"}], "segment_count": 1},
        ]
        result = _filter_conversations(conversations)
        assert len(result) == 0
