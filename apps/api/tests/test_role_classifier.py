"""Unit tests for speaker role classifier."""
import pytest
from unittest.mock import patch, MagicMock
from src.ai.role_classifier import classify_speaker_roles, _classify_with_heuristic


class TestRoleClassification:
    """Test suite for speaker role classification."""

    def test_empty_turns(self):
        """Test with empty conversation_turns returns empty dict."""
        result = classify_speaker_roles([])
        assert result == {}

    def test_single_speaker(self):
        """Test with single speaker cannot classify roles."""
        turns = [
            {"speaker": "Speaker_A", "text": "Hello world", "start_time": 0.0, "end_time": 1.0},
        ]
        result = classify_speaker_roles(turns, use_llm=False)
        assert len(result) == 1
        assert result["Speaker_A"]["role"] == "Unknown"
        assert result["Speaker_A"]["method"] == "None"

    def test_heuristic_classification_clear_pattern(self):
        """Test heuristic classification with clear salesperson/customer patterns."""
        turns = [
            {"speaker": "Speaker_A", "text": "Hello welcome to our store today", "start_time": 0.0, "end_time": 2.0},
            {"speaker": "Speaker_B", "text": "Hi I'm looking for a new phone", "start_time": 3.0, "end_time": 5.0},
            {"speaker": "Speaker_A", "text": "Sure we have the latest models. Let me show you our price range", "start_time": 6.0, "end_time": 10.0},
            {"speaker": "Speaker_B", "text": "How much does this one cost?", "start_time": 11.0, "end_time": 13.0},
        ]

        result = classify_speaker_roles(turns, use_llm=False)

        assert "Speaker_A" in result
        assert "Speaker_B" in result
        assert result["Speaker_A"]["role"] == "Salesperson"
        assert result["Speaker_B"]["role"] == "Customer"
        assert result["Speaker_A"]["method"] == "Heuristic"
        assert result["Speaker_B"]["method"] == "Heuristic"
        assert 0.0 <= result["Speaker_A"]["confidence"] <= 1.0

    def test_heuristic_first_greeting_signal(self):
        """Test that first greeting strongly indicates salesperson."""
        turns = [
            {"speaker": "Speaker_X", "text": "Good morning how can I help you", "start_time": 0.0, "end_time": 2.0},
            {"speaker": "Speaker_Y", "text": "I need a laptop", "start_time": 3.0, "end_time": 5.0},
        ]

        result = classify_speaker_roles(turns, use_llm=False)
        assert result["Speaker_X"]["role"] == "Salesperson"
        assert result["Speaker_Y"]["role"] == "Customer"

    def test_heuristic_turn_count_signal(self):
        """Test that speaker with most turns is classified as salesperson."""
        turns = [
            {"speaker": "Speaker_A", "text": "Hello", "start_time": 0.0, "end_time": 0.5},
            {"speaker": "Speaker_B", "text": "Hi", "start_time": 1.0, "end_time": 1.5},
            {"speaker": "Speaker_A", "text": "Welcome", "start_time": 2.0, "end_time": 2.5},
            {"speaker": "Speaker_A", "text": "How can I help", "start_time": 3.0, "end_time": 3.5},
            {"speaker": "Speaker_B", "text": "Looking for shoes", "start_time": 4.0, "end_time": 5.0},
        ]

        result = classify_speaker_roles(turns, use_llm=False)
        # Speaker_A has 3 turns, Speaker_B has 2 turns
        assert result["Speaker_A"]["role"] == "Salesperson"

    def test_heuristic_price_mention_signal(self):
        """Test that price mentions indicate salesperson."""
        turns = [
            {"speaker": "Speaker_A", "text": "The price is $50 with a 20% discount", "start_time": 0.0, "end_time": 3.0},
            {"speaker": "Speaker_B", "text": "That's expensive", "start_time": 4.0, "end_time": 5.0},
        ]

        result = classify_speaker_roles(turns, use_llm=False)
        assert result["Speaker_A"]["role"] == "Salesperson"

    def test_llm_classification_mocked(self):
        """Test LLM-based classification with mocked API response."""
        turns = [
            {"speaker": "Speaker_A", "text": "Hello welcome to our store", "start_time": 0.0, "end_time": 2.0},
            {"speaker": "Speaker_B", "text": "Hi I'm looking for help", "start_time": 3.0, "end_time": 5.0},
        ]

        # Mock NVIDIA API response
        mock_response = """
        {
            "classifications": {
                "Speaker_A": {
                    "role": "Salesperson",
                    "confidence": 0.95,
                    "reasoning": "Initiates greeting and welcoming language"
                },
                "Speaker_B": {
                    "role": "Customer",
                    "confidence": 0.92,
                    "reasoning": "Expresses need for assistance"
                }
            }
        }
        """

        with patch("src.ai.role_classifier.nvidia_client.chat_completion", return_value=mock_response):
            result = classify_speaker_roles(turns, use_llm=True)

        assert result["Speaker_A"]["role"] == "Salesperson"
        assert result["Speaker_B"]["role"] == "Customer"
        assert result["Speaker_A"]["method"] == "LLM"
        assert result["Speaker_A"]["confidence"] == 0.95

    def test_llm_failure_falls_back_to_heuristic(self):
        """Test that LLM failure triggers heuristic fallback."""
        turns = [
            {"speaker": "Speaker_A", "text": "Hello welcome", "start_time": 0.0, "end_time": 1.0},
            {"speaker": "Speaker_B", "text": "Hi there", "start_time": 2.0, "end_time": 3.0},
        ]

        # Mock LLM to raise exception
        with patch("src.ai.role_classifier.nvidia_client.chat_completion", side_effect=Exception("API Error")):
            result = classify_speaker_roles(turns, use_llm=True)

        # Should fall back to heuristic
        assert result["Speaker_A"]["method"] == "Heuristic"
        assert result["Speaker_B"]["method"] == "Heuristic"

    def test_llm_invalid_response_falls_back(self):
        """Test that invalid LLM response triggers heuristic fallback."""
        turns = [
            {"speaker": "Speaker_A", "text": "Hello", "start_time": 0.0, "end_time": 1.0},
            {"speaker": "Speaker_B", "text": "Hi", "start_time": 2.0, "end_time": 3.0},
        ]

        # Mock LLM to return invalid JSON
        with patch("src.ai.role_classifier.nvidia_client.chat_completion", return_value="not valid json"):
            result = classify_speaker_roles(turns, use_llm=True)

        # Should fall back to heuristic
        assert result["Speaker_A"]["method"] == "Heuristic"

    def test_three_speaker_scenario(self):
        """Test classification with 3 speakers (salesperson + 2 customers)."""
        turns = [
            {"speaker": "Speaker_A", "text": "Hello welcome to the store", "start_time": 0.0, "end_time": 2.0},
            {"speaker": "Speaker_B", "text": "Hi I need a phone", "start_time": 3.0, "end_time": 5.0},
            {"speaker": "Speaker_C", "text": "I'm looking for a laptop", "start_time": 6.0, "end_time": 8.0},
            {"speaker": "Speaker_A", "text": "Sure let me help you both", "start_time": 9.0, "end_time": 11.0},
        ]

        result = classify_speaker_roles(turns, use_llm=False)

        assert result["Speaker_A"]["role"] == "Salesperson"
        # Additional speakers default to Customer
        assert result["Speaker_B"]["role"] == "Customer"
        assert result["Speaker_C"]["role"] == "Customer"

    def test_confidence_calculation(self):
        """Test that confidence reflects classification certainty."""
        # Clear pattern should have high confidence
        clear_turns = [
            {"speaker": "Speaker_A", "text": "Hello welcome price is $50", "start_time": 0.0, "end_time": 2.0},
            {"speaker": "Speaker_B", "text": "Too expensive", "start_time": 3.0, "end_time": 4.0},
        ]

        clear_result = classify_speaker_roles(clear_turns, use_llm=False)
        assert clear_result["Speaker_A"]["confidence"] > 0.5
