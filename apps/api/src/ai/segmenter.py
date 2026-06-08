"""Conversation segmentation — splits a recording into discrete customer conversations.

Uses silence gaps, greeting detection, and speaker patterns to identify
conversation boundaries per the PRD (AI-05).
"""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SILENCE_GAP_THRESHOLD = 30.0  # seconds — gap > 30s = conversation boundary
MIN_CONVERSATION_DURATION = 10.0  # seconds — ignore segments shorter than 10s
MIN_SEGMENTS_PER_CONVERSATION = 2  # minimum transcript segments in a conversation

# Greeting / farewell patterns for detection
GREETING_PATTERNS = [
    r"\b(welcome|hello|hi|good\s*(morning|afternoon|evening)|hey|greetings)\b",
    r"\b(how\s*can\s*i\s*help|what\s*can\s*i\s*do|how\s*may\s*i\s*assist)\b",
    r"\b(come\s*in|step\s*right\s*in|take\s*a\s*look)\b",
]

FAREWELL_PATTERNS = [
    r"\b(goodbye|bye|see\s*you|thanks?\s*(for|for\s*coming)|have\s*a\s*(good|nice|great))\b",
    r"\b(take\s*care|come\s*back|have\s*a\s*nice\s*day)\b",
    r"\b(that.s\s*all|all\s*set|we.re\s*done)\b",
]


def segment_conversations(
    transcript_segments: list[dict[str, Any]],
    silence_gaps: list[tuple[float, float]] | None = None,
) -> list[dict[str, Any]]:
    """Segment a flat list of transcript segments into discrete conversations.

    Args:
        transcript_segments: List of {start, end, text, speaker} dicts
        silence_gaps: Optional list of (start, end) silence gap tuples from preprocessing

    Returns:
        List of conversation dicts:
        [
            {
                "start_time": 0.0,
                "end_time": 145.3,
                "segments": [{start, end, text, speaker}, ...],
                "segment_count": 12,
            },
            ...
        ]
    """
    if not transcript_segments:
        return []

    logger.info(f"Segmenting {len(transcript_segments)} transcript segments into conversations")

    # Step 1: Find conversation boundaries
    boundaries = _find_boundaries(transcript_segments, silence_gaps or [])

    # Step 2: Split segments into conversations based on boundaries
    conversations = _split_into_conversations(transcript_segments, boundaries)

    # Step 3: Filter out too-short / trivial conversations
    conversations = _filter_conversations(conversations)

    logger.info(f"Produced {len(conversations)} conversations from {len(transcript_segments)} segments")
    for i, conv in enumerate(conversations):
        logger.debug(
            f"  Conv {i+1}: {conv['start_time']:.1f}s - {conv['end_time']:.1f}s "
            f"({conv['segment_count']} segments)"
        )

    return conversations


def _find_boundaries(
    segments: list[dict],
    silence_gaps: list[tuple[float, float]],
) -> list[int]:
    """Find indices where conversation boundaries occur.

    A boundary exists between segment[i] and segment[i+1] when:
    1. There's a silence gap > 30s between them
    2. segment[i+1] starts with a greeting phrase
    3. segment[i] ends with a farewell phrase
    """
    boundaries = []

    for i in range(len(segments) - 1):
        current = segments[i]
        next_seg = segments[i + 1]

        gap = next_seg["start"] - current["end"]
        is_boundary = False

        # Rule 1: Large silence gap
        if gap >= SILENCE_GAP_THRESHOLD:
            is_boundary = True
            logger.debug(f"  Boundary at segment {i}: silence gap {gap:.1f}s")

        # Rule 2: Next segment starts with a greeting
        if _text_matches_patterns(next_seg.get("text", ""), GREETING_PATTERNS):
            is_boundary = True
            logger.debug(f"  Boundary at segment {i}: greeting detected")

        # Rule 3: Current segment ends with a farewell
        if _text_matches_patterns(current.get("text", ""), FAREWELL_PATTERNS):
            is_boundary = True
            logger.debug(f"  Boundary at segment {i}: farewell detected")

        # Rule 4: Silence gap from preprocessing overlaps this position
        for gap_start, gap_end in silence_gaps:
            if current["end"] >= gap_start and next_seg["start"] <= gap_end:
                gap_duration = gap_end - gap_start
                if gap_duration >= SILENCE_GAP_THRESHOLD:
                    is_boundary = True
                    logger.debug(f"  Boundary at segment {i}: preprocessing silence gap {gap_duration:.1f}s")
                    break

        if is_boundary:
            boundaries.append(i)

    return boundaries


def _split_into_conversations(
    segments: list[dict], boundaries: list[int]
) -> list[dict[str, Any]]:
    """Split segments into conversations based on boundary indices."""
    if not boundaries:
        # Single conversation — entire recording is one conversation
        return [_make_conversation(segments)]

    conversations = []
    prev_boundary = 0

    for boundary in boundaries:
        conv_segments = segments[prev_boundary : boundary + 1]
        if conv_segments:
            conversations.append(_make_conversation(conv_segments))
        prev_boundary = boundary + 1

    # Remaining segments after last boundary
    remaining = segments[prev_boundary:]
    if remaining:
        conversations.append(_make_conversation(remaining))

    return conversations


def _make_conversation(segments: list[dict]) -> dict[str, Any]:
    """Create a conversation dict from its segments."""
    return {
        "start_time": segments[0]["start"],
        "end_time": segments[-1]["end"],
        "segments": segments,
        "segment_count": len(segments),
    }


def _filter_conversations(conversations: list[dict]) -> list[dict]:
    """Remove conversations that are too short or have too few segments."""
    filtered = []
    for conv in conversations:
        duration = conv["end_time"] - conv["start_time"]
        if duration < MIN_CONVERSATION_DURATION:
            logger.debug(
                f"  Filtering out short conversation: {duration:.1f}s, "
                f"{conv['segment_count']} segments"
            )
            continue
        if conv["segment_count"] < MIN_SEGMENTS_PER_CONVERSATION:
            logger.debug(
                f"  Filtering out single-segment conversation: "
                f"{conv['segment_count']} segments"
            )
            continue
        filtered.append(conv)
    return filtered


def _text_matches_patterns(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the given regex patterns (case-insensitive)."""
    text_lower = text.lower().strip()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False
