"""Unit tests for transcription chunking, word deduplication, and VAD timestamp remapping."""
import pytest
from src.workers.transcription import _deduplicate_words, _remap_timestamps, _apply_vad_filter


class TestWordDeduplication:
    """Test suite for _deduplicate_words function."""

    def test_empty_words(self):
        """Test with empty word list returns empty."""
        result = _deduplicate_words([])
        assert result == []

    def test_no_duplicates(self):
        """Test words without duplicates are preserved."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "world", "start": 1.0, "end": 1.5, "confidence": 0.95},
            {"word": "test", "start": 2.0, "end": 2.5, "confidence": 0.92},
        ]
        result = _deduplicate_words(words, tolerance_ms=50.0)
        assert len(result) == 3
        assert result == words

    def test_duplicate_removal_keep_higher_confidence(self):
        """Test duplicate words are removed, keeping higher confidence."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "Hello", "start": 0.12, "end": 0.52, "confidence": 0.95},  # Duplicate, lower confidence
        ]
        result = _deduplicate_words(words, tolerance_ms=50.0)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.98  # Kept higher confidence version

    def test_duplicate_removal_replace_with_higher(self):
        """Test duplicate with lower confidence is replaced by higher."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.90},
            {"word": "Hello", "start": 0.12, "end": 0.52, "confidence": 0.98},  # Duplicate, higher confidence
        ]
        result = _deduplicate_words(words, tolerance_ms=50.0)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.98  # Replaced with higher confidence

    def test_tolerance_boundary(self):
        """Test tolerance boundary behavior."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "Hello", "start": 0.15, "end": 0.55, "confidence": 0.95},  # Exactly 50ms apart
        ]

        # With 50ms tolerance, should be considered duplicate
        result_50ms = _deduplicate_words(words, tolerance_ms=50.0)
        assert len(result_50ms) == 1

        # With 40ms tolerance, should NOT be duplicate
        result_40ms = _deduplicate_words(words, tolerance_ms=40.0)
        assert len(result_40ms) == 2

    def test_different_words_not_duplicates(self):
        """Test different words are not considered duplicates even if overlapping."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "world", "start": 0.12, "end": 0.52, "confidence": 0.95},  # Different word
        ]
        result = _deduplicate_words(words, tolerance_ms=50.0)
        assert len(result) == 2  # Both preserved (different words)

    def test_case_insensitive_duplicate_detection(self):
        """Test duplicate detection is case-insensitive."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
            {"word": "hello", "start": 0.12, "end": 0.52, "confidence": 0.95},  # Same word, different case
        ]
        result = _deduplicate_words(words, tolerance_ms=50.0)
        assert len(result) == 1

    def test_multiple_duplicates_in_sequence(self):
        """Test multiple duplicates in a sequence are handled correctly."""
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.90},
            {"word": "Hello", "start": 0.12, "end": 0.52, "confidence": 0.95},  # Duplicate 1
            {"word": "Hello", "start": 0.13, "end": 0.53, "confidence": 0.98},  # Duplicate 2 (highest)
            {"word": "world", "start": 1.0, "end": 1.5, "confidence": 0.95},
        ]
        result = _deduplicate_words(words, tolerance_ms=50.0)
        assert len(result) == 2
        assert result[0]["confidence"] == 0.98  # Kept highest confidence duplicate
        assert result[1]["word"] == "world"

    def test_sorted_output(self):
        """Test output is sorted by start time."""
        words = [
            {"word": "world", "start": 1.0, "end": 1.5, "confidence": 0.95},
            {"word": "Hello", "start": 0.1, "end": 0.5, "confidence": 0.98},
        ]
        result = _deduplicate_words(words, tolerance_ms=50.0)
        assert result[0]["word"] == "Hello"
        assert result[1]["word"] == "world"

    def test_overlap_region_scenario(self):
        """Test realistic overlap region with multiple words."""
        # Simulating words from two overlapping chunks
        words = [
            # Chunk 1 words
            {"word": "the", "start": 10.0, "end": 10.2, "confidence": 0.95},
            {"word": "price", "start": 10.3, "end": 10.6, "confidence": 0.92},
            {"word": "is", "start": 10.7, "end": 10.9, "confidence": 0.98},
            # Chunk 2 overlap (same words, slightly different timestamps)
            {"word": "the", "start": 10.02, "end": 10.22, "confidence": 0.97},  # Higher confidence
            {"word": "price", "start": 10.32, "end": 10.62, "confidence": 0.90},  # Lower confidence
            {"word": "is", "start": 10.72, "end": 10.92, "confidence": 0.96},  # Lower confidence
            # New words after overlap
            {"word": "$50", "start": 11.0, "end": 11.3, "confidence": 0.99},
        ]

        result = _deduplicate_words(words, tolerance_ms=50.0)

        # Should have 4 unique words (the, price, is, $50)
        assert len(result) == 4
        # "the" should have confidence 0.97 (higher from overlap)
        assert result[0]["word"] == "the"
        assert result[0]["confidence"] == 0.97
        # "price" should have confidence 0.92 (higher from chunk 1)
        assert result[1]["word"] == "price"
        assert result[1]["confidence"] == 0.92


class TestVADTimestampRemapping:
    """Test suite for _remap_timestamps — VAD filtered → original timeline."""

    def test_no_speech_segments_passthrough(self):
        """Empty speech segments returns timestamps unchanged."""
        segments = [{"start": 1.0, "end": 5.0, "text": "hello"}]
        words = [{"word": "hello", "start": 1.0, "end": 1.5, "confidence": 0.9}]
        r_segs, r_words = _remap_timestamps(segments, words, [])
        assert r_segs == segments
        assert r_words == words

    def test_single_speech_segment_no_silence(self):
        """Single segment covering full audio — timestamps unchanged."""
        speech = [{"start": 0.0, "end": 30.0}]
        segments = [{"start": 5.0, "end": 10.0, "text": "test"}]
        words = [{"word": "test", "start": 5.0, "end": 5.5, "confidence": 0.9}]
        r_segs, r_words = _remap_timestamps(segments, words, speech)
        assert r_segs[0]["start"] == pytest.approx(5.0)
        assert r_segs[0]["end"] == pytest.approx(10.0)
        assert r_words[0]["start"] == pytest.approx(5.0)

    def test_two_segments_with_silence_gap(self):
        """Two speech segments with a 5s silence gap — timestamps remap correctly.

        Original timeline:  [speech 0-10] [silence 10-15] [speech 15-25]
        Filtered timeline:  [speech 0-10] [speech 10-20]  (20s total)

        STT sees word at filtered t=14 → should map to original t=19.
        """
        speech = [
            {"start": 0.0, "end": 10.0},   # 10s speech
            {"start": 15.0, "end": 25.0},   # 10s speech (after 5s silence)
        ]
        # STT output from filtered audio (20s total)
        segments = [{"start": 14.0, "end": 16.0, "text": "word_in_second_segment"}]
        words = [{"word": "word_in_second_segment", "start": 14.0, "end": 15.0, "confidence": 0.9}]

        r_segs, r_words = _remap_timestamps(segments, words, speech)

        # filtered t=14 → second segment, offset = 14 - 10 = 4 → original = 15 + 4 = 19
        assert r_segs[0]["start"] == pytest.approx(19.0)
        # filtered t=16 → second segment, offset = 16 - 10 = 6 → original = 15 + 6 = 21
        assert r_segs[0]["end"] == pytest.approx(21.0)
        # Word: filtered t=14 → original 19.0
        assert r_words[0]["start"] == pytest.approx(19.0)

    def test_three_segments_two_gaps(self):
        """Three speech segments with two silence gaps."""
        speech = [
            {"start": 0.0, "end": 5.0},    # 5s speech
            {"start": 10.0, "end": 20.0},   # 10s speech (5s gap)
            {"start": 30.0, "end": 40.0},   # 10s speech (10s gap)
        ]
        # Total filtered duration: 5 + 10 + 10 = 25s
        # Word at filtered t=20 (in 3rd segment) → original = 30 + (20-15) = 35
        segments = [{"start": 20.0, "end": 22.0, "text": "late_word"}]
        words = []

        r_segs, _ = _remap_timestamps(segments, words, speech)
        assert r_segs[0]["start"] == pytest.approx(35.0)
        assert r_segs[0]["end"] == pytest.approx(37.0)

    def test_timestamp_at_segment_boundary(self):
        """Timestamp exactly at the boundary between two speech segments."""
        speech = [
            {"start": 0.0, "end": 10.0},
            {"start": 15.0, "end": 25.0},
        ]
        # filtered t=10 is exactly at end of first / start of second segment
        segments = [{"start": 10.0, "end": 12.0, "text": "boundary"}]
        words = []

        r_segs, _ = _remap_timestamps(segments, words, speech)
        # t=10 → second segment start: 15 + (10-10) = 15
        assert r_segs[0]["start"] == pytest.approx(15.0)

    def test_timestamp_beyond_end_clamps(self):
        """Timestamp beyond filtered duration clamps to last segment end.

        When both start and end clamp to the same value, the segment collapses
        and is filtered out (start == end means zero-width).
        """
        speech = [{"start": 5.0, "end": 15.0}]
        # filtered duration = 10s, but STT returns t=12 (beyond end)
        segments = [{"start": 8.0, "end": 12.0, "text": "overflow"}]
        words = []

        r_segs, _ = _remap_timestamps(segments, words, speech)
        # start=8 maps to 5+(8-0)=13, end=12 clamps to 15
        assert len(r_segs) == 1
        assert r_segs[0]["start"] == pytest.approx(13.0)
        assert r_segs[0]["end"] == pytest.approx(15.0)

    def test_timestamp_before_start_clamps(self):
        """Negative or zero timestamp clamps to first segment start."""
        speech = [{"start": 5.0, "end": 15.0}]
        segments = [{"start": -0.5, "end": 2.0, "text": "early"}]
        words = []

        r_segs, _ = _remap_timestamps(segments, words, speech)
        # Clamps to first segment start = 5.0
        assert r_segs[0]["start"] == pytest.approx(5.0)

    def test_preserves_extra_segment_fields(self):
        """Extra fields in segment/word dicts are preserved through remapping."""
        speech = [{"start": 0.0, "end": 10.0}]
        segments = [{"start": 5.0, "end": 8.0, "text": "hello", "speaker": "SPEAKER_00"}]
        words = [{"word": "hello", "start": 5.0, "end": 5.5, "confidence": 0.95, "speaker": "SPEAKER_00"}]

        r_segs, r_words = _remap_timestamps(segments, words, speech)
        assert r_segs[0]["text"] == "hello"
        assert r_segs[0]["speaker"] == "SPEAKER_00"
        assert r_words[0]["confidence"] == 0.95
        assert r_words[0]["speaker"] == "SPEAKER_00"

    def test_collapsed_segments_filtered(self):
        """Segments where start >= end after remapping are filtered out."""
        speech = [{"start": 0.0, "end": 10.0}]
        # This segment collapses to zero width after remap (edge case)
        segments = [{"start": 15.0, "end": 15.0, "text": "collapsed"}]
        words = []

        r_segs, _ = _remap_timestamps(segments, words, speech)
        assert len(r_segs) == 0


class TestApplyVADFilter:
    """Test suite for _apply_vad_filter wrapper."""

    def test_vad_disabled_returns_original(self):
        """When VAD is disabled, returns original audio unchanged."""
        from unittest.mock import patch
        mock_audio = b"\x00" * 1000

        with patch("src.workers.transcription.settings") as mock_settings:
            mock_settings.vad_use_silero = False
            mock_settings.vad_filter_before_stt = True
            result_audio, result_segments = _apply_vad_filter(mock_audio)

        assert result_audio == mock_audio
        assert result_segments == []

    def test_vad_filter_disabled_returns_original(self):
        """When vad_filter_before_stt is False, returns original audio."""
        from unittest.mock import patch
        mock_audio = b"\x00" * 1000

        with patch("src.workers.transcription.settings") as mock_settings:
            mock_settings.vad_use_silero = True
            mock_settings.vad_filter_before_stt = False
            result_audio, result_segments = _apply_vad_filter(mock_audio)

        assert result_audio == mock_audio
        assert result_segments == []

    def test_vad_import_failure_graceful_fallback(self):
        """When torch/torchaudio not installed, falls back to original audio."""
        from unittest.mock import patch
        mock_audio = b"\x00" * 1000

        with patch("src.workers.transcription.settings") as mock_settings:
            mock_settings.vad_use_silero = True
            mock_settings.vad_filter_before_stt = True
            with patch.dict("sys.modules", {"src.ai.vad": None}):
                result_audio, result_segments = _apply_vad_filter(mock_audio)

        assert result_audio == mock_audio
        assert result_segments == []
