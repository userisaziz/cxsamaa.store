"""Word-level speaker attribution engine.

Assigns speaker labels to individual words using temporal overlap with diarization segments.
This replaces the coarse segment-level speaker assignment with fine-grained word-level attribution.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def assign_speaker_to_word(
    words: list[dict[str, Any]],
    diarization_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Assign speaker labels to individual words using diarization segments.

    Uses temporal overlap to determine which speaker is speaking each word.

    Args:
        words: Word-level transcripts [{word, start, end, confidence}]
        diarization_segments: Diarization output [{start, end, speaker}]

    Returns:
        Words with speaker labels: [{word, start, end, confidence, speaker}]
    """
    if not diarization_segments:
        # Fallback: assign UNKNOWN speaker to all words
        logger.warning("No diarization segments available — assigning UNKNOWN speaker to all words")
        return [{**word, "speaker": "UNKNOWN"} for word in words]

    result = []
    for word in words:
        word_start = word["start"]
        word_end = word["end"]
        word_midpoint = (word_start + word_end) / 2.0

        # Find the speaker segment that contains this word's midpoint
        assigned_speaker = _find_speaker_for_timestamp(
            word_midpoint, diarization_segments
        )

        result.append({
            **word,
            "speaker": assigned_speaker,
        })

    # Normalize speaker labels to Speaker_A, Speaker_B, etc.
    return _normalize_speaker_labels(result)


def _find_speaker_for_timestamp(
    timestamp: float,
    diarization_segments: list[dict[str, Any]],
) -> str:
    """Find the speaker for a given timestamp.

    Strategy:
    1. Find segment where start <= timestamp < end
    2. If no exact match, find nearest segment (by distance)
    3. If multiple overlapping segments, use segment with highest overlap

    Args:
        timestamp: Time in seconds
        diarization_segments: List of {start, end, speaker}

    Returns:
        Speaker label string
    """
    # First pass: find exact match
    for segment in diarization_segments:
        if segment["start"] <= timestamp < segment["end"]:
            return segment["speaker"]

    # Second pass: find nearest segment
    nearest_segment = None
    min_distance = float("inf")

    for segment in diarization_segments:
        # Distance to segment
        if timestamp < segment["start"]:
            distance = segment["start"] - timestamp
        elif timestamp >= segment["end"]:
            distance = timestamp - segment["end"]
        else:
            distance = 0  # Should not happen (caught by first pass)

        if distance < min_distance:
            min_distance = distance
            nearest_segment = segment

    if nearest_segment:
        logger.debug(
            f"Timestamp {timestamp:.3f}s not in any segment, "
            f"using nearest: {nearest_segment['speaker']} (distance: {min_distance:.3f}s)"
        )
        return nearest_segment["speaker"]

    return "UNKNOWN"


def _normalize_speaker_labels(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize speaker labels to Speaker_A, Speaker_B, etc.

    Maps arbitrary speaker labels (SPEAKER_00, SPEAKER_01, etc.) to
    consistent Speaker_A, Speaker_B naming.
    """
    speaker_mapping: dict[str, str] = {}
    speaker_counter = 0

    result = []
    for word in words:
        original_speaker = word.get("speaker", "UNKNOWN")

        # Preserve UNKNOWN label — don't map it to a named speaker
        if original_speaker == "UNKNOWN":
            result.append({
                **word,
                "speaker": "UNKNOWN",
            })
            continue

        if original_speaker not in speaker_mapping:
            speaker_mapping[original_speaker] = f"Speaker_{chr(65 + speaker_counter)}"
            speaker_counter += 1

        result.append({
            **word,
            "speaker": speaker_mapping[original_speaker],
        })

    logger.info(f"Normalized speaker labels: {speaker_mapping}")
    return result
