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

SILENCE_GAP_THRESHOLD = 60.0  # seconds — gap > 60s = conversation boundary
MEDIUM_GAP_THRESHOLD = 20.0  # seconds — gap > 20s + farewell = likely end of conversation
MIN_CONVERSATION_DURATION = 10.0  # seconds — ignore segments shorter than 10s
MIN_SEGMENTS_PER_CONVERSATION = 2  # minimum transcript segments in a conversation

# ---------------------------------------------------------------------------
# Greeting patterns — multilingual (English, Arabic, Gulf, Hindi, Urdu,
#                    transliterated Arabic)
# ---------------------------------------------------------------------------
GREETING_PATTERNS = [
    # English
    r"\b(welcome|hello|hi|good\s*(morning|afternoon|evening)|hey|greetings)\b",
    r"\b(how\s*can\s*i\s*help|what\s*can\s*i\s*do|how\s*may\s*i\s*assist)\b",
    r"\b(come\s*in|step\s*right\s*in|take\s*a\s*look)\b",
    # Arabic (MSA) — مرحبا، أهلا، السلام عليكم، هلا، صباح الخير، مساء الخير
    r"(\u0645\u0631\u062d\u0628\u0627|\u0623\u0647\u0644\u0627|\u0627\u0644\u0633\u0644\u0627\u0645\s*\u0639\u0644\u064a\u0643|\u0647\u0644\u0627|\u0635\u0628\u0627\u062d\s*(\u0627\u0644\u062e\u064a\u0631|\u0627\u0644\u0646\u0648\u0631)|\u0645\u0633\u0627\u0621\s*(\u0627\u0644\u062e\u064a\u0631|\u0627\u0644\u0646\u0648\u0631))",
    # Arabic — how can I help (كيف أقدر أساعدك، شلون أقدر أساعدك)
    r"(\u0643\u064a\u0641\s*(\u0623\u0642\u062f\u0631|\u0627\u0642\u062f\u0631)\s*\u0623\u0633\u0627\u0639\u062f|\u0634\u0644\u0648\u0646\s*\u0623\u0642\u062f\u0631\s*\u0623\u0633\u0627\u0639\u062f|\u0628\u062d\u0627\u062c\u062a\u0643)",
    # Gulf dialect — هلا والله، يا هلا، تفضل
    r"(\u0647\u0644\u0627\s*\u0648\u0627\u0644\u0644\u0647|\u064a\u0627\s*\u0647\u0644\u0627|\u062a\u0641\u0636\u0644)",
    # Urdu — السلام علیکم، آداب
    r"(\u0627\u0644\u0633\u0644\u0627\u0645\s*\u0639\u0644\u06cc\u06a9\u0645|\u0622\u062f\u0627\u0628)",
    # Transliterated Arabic/Urdu greetings (STT often outputs Latin script)
    r"\b(marhaba|salam\s*alaikum|sabah\s*alkhair|sabah\s*al\s*khair|masa\s*alkhair|hala\s*wallah|hala)\b",
    # Hindi — नमस्ते, नमस्कार, स्वागत, आइए
    r"(\u0928\u092e\u0938\u094d\u0924\u0947|\u0928\u092e\u0938\u094d\u0915\u093e\u0930|\u0938\u094d\u0935\u093e\u0917\u0924|\u0906\u0907\u090f|\u0939\u0947\u0932\u094b|\u0915\u094d\u092f\u093e\s*\u0939\u093e\u0932\s*\u0939\u0948)",
    # Hindi — how can I help (मैं कैसे मदद करूं, बताइए)
    r"(\u092e\u0948\u0902\s*\u0915\u0948\u0938\u0947\s*\u092e\u0926\u0926|\u092c\u0924\u093e\u0907\u090f|\u0915\u094d\u092f\u093e\s*\u0938\u0947\u0935\u093e\s*\u0915\u0930\u0942\u0902)",
]

# ---------------------------------------------------------------------------
# Farewell patterns — multilingual
# ---------------------------------------------------------------------------
FAREWELL_PATTERNS = [
    # English
    r"\b(goodbye|bye|see\s*you|thanks?\s*(for|for\s*coming)|have\s*a\s*(good|nice|great))\b",
    r"\b(take\s*care|come\s*back|have\s*a\s*nice\s*day)\b",
    r"\b(that.s\s*all|all\s*set|we.re\s*done)\b",
    # Arabic (MSA) — مع السلامة، وداعا، إلى اللقاء، الله يعطيك العافية، تسلم، منورين
    r"(\u0645\u0639\s*\u0627\u0644\u0633\u0644\u0627\u0645\u0629|\u0648\u062f\u0627\u0639\u0627|\u0625\u0644\u0649\s*\u0627\u0644\u0644\u0642\u0627\u0621|\u0627\u0644\u0644\u0647\s*\u064a\u0639\u0637\u064a\u0643\s*\u0627\u0644\u0639\u0627\u0641\u064a\u0629|\u062a\u0633\u0644\u0645|\u0645\u0646\u0648\u0631\u064a\u0646)",
    # Gulf dialect — في أمان الله
    r"(\u0641\u064a\s*\u0623\u0645\u0627\u0646\s*\u0627\u0644\u0644\u0647)",
    # Urdu — خدا حافظ، اللہ حافظ، شکریہ
    r"(\u062e\u062f\u0627\s*\u062d\u0627\u0641\u0638|\u0627\u0644\u0644\u06c1\s*\u062d\u0627\u0641\u0638|\u0634\u06a9\u0631\u06cc\u06c1)",
    # Transliterated Arabic/Urdu farewells
    r"\b(ma\s*salama|shukran|shukriya)\b",
    # Hindi — अलविदा, धन्यवाद, शुक्रिया, फिर मिलेंगे
    r"(\u0905\u0932\u0935\u093f\u0926\u093e|\u0927\u0928\u094d\u092f\u0935\u093e\u0926|\u0936\u0941\u0915\u094d\u0930\u093f\u092f\u093e|\u092b\u093f\u0930\s*\u092e\u093f\u0932\u0947\u0902\u0917\u0947|\u0906\u092a\u0915\u093e\s*\u0926\u093f\u0928\s*\u0936\u0941\u092d\u0939)",
]

# ---------------------------------------------------------------------------
# Direct question patterns — signals new conversation even without greeting
# Used with medium silence gaps to detect "customer just starts asking"
# ---------------------------------------------------------------------------
DIRECT_QUESTION_PATTERNS = [
    # English — price/availability/direction questions
    r"\b(how\s*much|how\s*many|what\s*price|what.s\s*the\s*price|do\s*you\s*have|where\s*(is|are)\s*the|can\s*i\s*(get|see|try|find)|i['']?\s*(want|need|m\s+looking|am\s+looking|i\s+searching))\b",
    r"\b(what\s*kinds?\s*of|which\s*one|is\s*there\s*any|are\s*you\s*selling|do\s*you\s*carry)\b",
    # Arabic — بكم، كم السعر، عندك، وين، أبي، بغيت، هل في
    r"(\u0628\u0643\u0645|\u0643\u0645\s*\u0627\u0644\u0633\u0639\u0631|\u0639\u0646\u062f\u0643|\u0648\u064a\u0646|\u0623\u0628\u064a|\u0628\u063a\u064a\u062a|\u0647\u0644\s*\u0641\u064a|\u0623\u0646\u0627\s*\u0623\u0628\u062d\u062b|\u0639\u0646\u062f\u0643\u0645)",
    # Gulf dialect — وش عندك
    r"(\u0648\u0634\s*\u0639\u0646\u062f\u0643)",
    # Transliterated Arabic questions (STT Latin output)
    r"\b(bikam|ain\s)\b",
    # Hindi — कितना, क्या है, कहाँ, मुझे चाहिए, आपके पास
    r"(\u0915\u093f\u0924\u0928\u093e|\u0915\u093f\u0924\u0928\u093e|\u0915\u094d\u092f\u093e\s*\u0939\u0948|\u0915\u0939\u093e\u0901|\u092e\u0941\u091d\u0947\s*\u091a\u093e\u0939\u093f\u090f|\u0906\u092a\u0915\u0947\s*\u092a\u093e\u0938|\u092f\u0947\s*\u0915\u0939\u093e\u0901\s*\u0939\u0948|\u0915\u094d\u092f\u093e\s*\u0906\u092a\u0915\u0947)",
]

# ---------------------------------------------------------------------------
# Pre-compiled regex patterns for efficiency (avoid re-compilation per call)
# ---------------------------------------------------------------------------
_COMPILED_GREETING = [re.compile(p, re.IGNORECASE) for p in GREETING_PATTERNS]
_COMPILED_FAREWELL = [re.compile(p, re.IGNORECASE) for p in FAREWELL_PATTERNS]
_COMPILED_QUESTION = [re.compile(p, re.IGNORECASE) for p in DIRECT_QUESTION_PATTERNS]


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

    # Step 1b: Merge adjacent farewell+greeting boundaries.
    # When segment[i] has a farewell and segment[i+1] has a greeting,
    # both create boundaries at i and i+1. Keep only i+1 so the greeting
    # starts the new conversation (not ends the old one).
    boundaries = _merge_farewell_greeting_boundaries(
        transcript_segments, boundaries
    )

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
    1. There's a silence gap > 60s between them (customer left, long pause)
    2. segment[i] ends with farewell AND segment[i+1] starts with greeting (clear customer change)
    3. Medium gap (20-60s) + farewell = customer left after browsing
    """
    boundaries = []

    for i in range(len(segments) - 1):
        current = segments[i]
        next_seg = segments[i + 1]

        gap = next_seg["start"] - current["end"]
        is_boundary = False

        # Rule 1: Large silence gap (> 60s) — always a boundary
        if gap >= SILENCE_GAP_THRESHOLD:
            is_boundary = True
            logger.debug(f"  Boundary at segment {i}: long silence gap {gap:.1f}s")

        # Rule 2: Farewell + Greeting combo — clear customer transition
        # Only create boundary if CURRENT ends with farewell AND NEXT starts with greeting
        if (
            _text_matches_patterns(current.get("text", ""), FAREWELL_PATTERNS) and
            _text_matches_patterns(next_seg.get("text", ""), GREETING_PATTERNS)
        ):
            is_boundary = True
            logger.debug(f"  Boundary at segment {i}: farewell + greeting combo")

        # Rule 3: Medium gap (20-60s) + farewell — customer left after browsing/thinking
        if (
            not is_boundary
            and gap >= MEDIUM_GAP_THRESHOLD
            and _text_matches_patterns(current.get("text", ""), FAREWELL_PATTERNS)
        ):
            is_boundary = True
            logger.debug(
                f"  Boundary at segment {i}: medium gap {gap:.1f}s + farewell"
            )

        # Rule 6: Silence gap from preprocessing overlaps this position
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


def _merge_farewell_greeting_boundaries(
    segments: list[dict], boundaries: list[int]
) -> list[int]:
    """Merge adjacent farewell+greeting boundaries.

    When segment[i] ends with a farewell and segment[i+1] starts with a
    greeting, both create boundaries at i and i+1.  We keep only i+1 so
    the greeting opens the new conversation instead of closing the old one.
    """
    if len(boundaries) < 2:
        return boundaries

    merged: list[int] = []
    skip_next = False

    for idx, b in enumerate(boundaries):
        if skip_next:
            skip_next = False
            continue

        # Check if this boundary and the next are adjacent indices
        # AND current segment has farewell + next segment has greeting
        if idx + 1 < len(boundaries) and boundaries[idx + 1] == b + 1:
            current_text = segments[b].get("text", "")
            next_text = segments[b + 1].get("text", "")
            if _text_matches_patterns(current_text, FAREWELL_PATTERNS) and \
               _text_matches_patterns(next_text, GREETING_PATTERNS):
                # Skip this boundary; keep the next one (greeting)
                skip_next = True
                continue

        merged.append(b)

    return merged


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
    """Check if text matches any of the given regex patterns (case-insensitive).

    Uses pre-compiled patterns when available for efficiency.
    """
    text_lower = text.lower().strip()

    # Use compiled patterns for the three main pattern lists
    if patterns is GREETING_PATTERNS:
        compiled = _COMPILED_GREETING
    elif patterns is FAREWELL_PATTERNS:
        compiled = _COMPILED_FAREWELL
    elif patterns is DIRECT_QUESTION_PATTERNS:
        compiled = _COMPILED_QUESTION
    else:
        compiled = None

    if compiled is not None:
        return any(rx.search(text_lower) for rx in compiled)

    # Fallback for any custom pattern list
    return any(re.search(p, text_lower, re.IGNORECASE) for p in patterns)


def _is_customer_speaker(
    speaker: str,
    segments: list[dict],
    from_index: int,
) -> bool:
    """Heuristic: determine if a speaker is likely the customer (not salesperson).

    In retail, the salesperson typically speaks first and more often in short bursts.
    The customer tends to speak in shorter total segments but asks questions.
    For simplicity, we check if this speaker is NOT the most frequent speaker
    in the first few segments (salesperson usually initiates).
    """
    if not speaker:
        return False

    # Look at first 10 segments to identify the salesperson (most frequent speaker)
    sample = segments[: min(10, len(segments))]
    speaker_counts: dict[str, int] = {}
    for seg in sample:
        sp = seg.get("speaker", "")
        if sp:
            speaker_counts[sp] = speaker_counts.get(sp, 0) + 1

    if not speaker_counts:
        return False

    # The most frequent speaker in opening segments is likely the salesperson
    salesperson = max(speaker_counts, key=speaker_counts.get)  # type: ignore[arg-type]
    return speaker != salesperson
