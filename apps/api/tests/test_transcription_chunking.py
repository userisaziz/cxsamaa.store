"""Unit tests for transcription chunking and word deduplication."""
import pytest
from src.workers.transcription import _deduplicate_words


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
