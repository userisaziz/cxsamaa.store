"""Speaker role classification — identifies Salesperson vs Customer.

Uses a hybrid approach: LLM-based classification (primary) with heuristic
fallback for reliability. Analyzes conversation turns to determine speaker
roles based on greeting patterns, speaking time, and conversation dynamics.
"""
import json
import logging
import re
from typing import Any

from src.ai.nvidia_client import NVIDIAAPIError, nvidia_client

logger = logging.getLogger(__name__)

# Confidence threshold for LLM classification
LLM_CONFIDENCE_THRESHOLD = 0.7

# Heuristic patterns for role identification
GREETING_PATTERNS = [
    r"\b(welcome|hello|hi|good\s*(morning|afternoon|evening))\b",
    r"\b(how\s*can\s*i\s*help|what\s*can\s*i\s*do|how\s*may\s*i\s*assist)\b",
    r"\b(come\s*in|step\s*right\s*in|take\s*a\s*look)\b",
]

PRICE_MENTION_PATTERNS = [
    r"\b(price|cost|\$\d+|discount|offer|sale|deal)\b",
    r"\b(how\s*much|what.*price|bikam|كم\s*السعر)\b",
]

PRODUCT_MENTION_PATTERNS = [
    r"\b(we\s*have|we\s*carry|our\s*products|available|in\s*stock)\b",
    r"\b(this\s*model|this\s*one|let\s*me\s*show|recommend)\b",
]

# Pre-compiled patterns
_COMPILED_GREETINGS = [re.compile(p, re.IGNORECASE) for p in GREETING_PATTERNS]
_COMPILED_PRICES = [re.compile(p, re.IGNORECASE) for p in PRICE_MENTION_PATTERNS]
_COMPILED_PRODUCTS = [re.compile(p, re.IGNORECASE) for p in PRODUCT_MENTION_PATTERNS]


def classify_speaker_roles(
    conversation_turns: list[dict[str, Any]],
    use_llm: bool = True,
) -> dict[str, dict[str, Any]]:
    """Classify speakers as Salesperson or Customer.

    Uses LLM-based classification (primary) with heuristic fallback.

    Args:
        conversation_turns: List of conversation turn dicts with speaker and text.
            Example:
            [{"speaker": "Speaker_A", "text": "Hello welcome to our store"},
             {"speaker": "Speaker_B", "text": "Hi I'm looking for a phone"}]
        use_llm: Whether to try LLM classification first (default: True)

    Returns:
        Dict mapping speaker labels to role info:
        {
            "Speaker_A": {
                "role": "Salesperson",
                "method": "LLM",  # or "Heuristic"
                "confidence": 0.95
            },
            "Speaker_B": {
                "role": "Customer",
                "method": "LLM",
                "confidence": 0.92
            }
        }
    """
    if not conversation_turns:
        logger.warning("Empty conversation_turns — cannot classify roles")
        return {}

    # Identify unique speakers
    unique_speakers = list(set(turn["speaker"] for turn in conversation_turns))
    if len(unique_speakers) < 2:
        logger.info(f"Only {len(unique_speakers)} speaker(s) — cannot classify roles")
        return {
            speaker: {"role": "Unknown", "method": "None", "confidence": 0.0}
            for speaker in unique_speakers
        }

    # Try LLM classification first
    if use_llm:
        try:
            logger.info("Attempting LLM-based role classification")
            llm_result = _classify_with_llm(conversation_turns)
            if llm_result:
                logger.info("LLM classification successful")
                return llm_result
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}, falling back to heuristic")

    # Fallback to heuristic classification
    logger.info("Using heuristic role classification")
    heuristic_result = _classify_with_heuristic(conversation_turns)
    return heuristic_result


def _classify_with_llm(
    conversation_turns: list[dict[str, Any]],
) -> dict[str, dict[str, Any]] | None:
    """Use LLM to classify speaker roles.

    Args:
        conversation_turns: List of conversation turn dicts

    Returns:
        Classification result dict or None if classification fails
    """
    # Format conversation for prompt
    conversation_text = _format_conversation_for_llm(conversation_turns)

    # Unique speakers
    unique_speakers = list(set(turn["speaker"] for turn in conversation_turns))

    prompt = f"""You are an expert retail sales conversation analyst. Analyze this conversation and classify each speaker as either 'Salesperson' or 'Customer'.

Consider these signals:
- Who initiates greetings (typically Salesperson)
- Who asks vs answers product questions (Customer asks, Salesperson answers)
- Who mentions prices, features, or product availability (typically Salesperson)
- Speaking patterns (Salesperson usually speaks first and more frequently)
- Who makes objections or expresses purchase intent (typically Customer)

Conversation:
{conversation_text}

Speakers to classify: {', '.join(unique_speakers)}

Respond with valid JSON matching this exact schema:
{{
    "classifications": {{
        "Speaker_A": {{
            "role": "Salesperson",  // or "Customer"
            "confidence": 0.95,      // 0.0-1.0, your confidence in this classification
            "reasoning": "Brief explanation of why"
        }},
        "Speaker_B": {{
            "role": "Customer",
            "confidence": 0.92,
            "reasoning": "Brief explanation"
        }}
    }}
}}

Rules:
- Each speaker must be classified as exactly "Salesperson" or "Customer"
- Confidence should be between 0.0 and 1.0
- Reasoning should be 1-2 sentences max
- Respond ONLY with valid JSON, no additional text"""

    messages = [
        {"role": "system", "content": "You are an expert retail sales conversation analyst. You must respond with valid JSON only."},
        {"role": "user", "content": prompt},
    ]

    try:
        response_text = nvidia_client.chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        # Parse response
        result = _parse_llm_response(response_text, unique_speakers)
        return result

    except NVIDIAAPIError as e:
        logger.error(f"NVIDIA API error during role classification: {e}")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return None


def _parse_llm_response(
    response_text: str,
    expected_speakers: list[str],
) -> dict[str, dict[str, Any]] | None:
    """Parse and validate LLM classification response.

    Args:
        response_text: Raw LLM response (JSON string)
        expected_speakers: List of speaker labels that must be classified

    Returns:
        Validated classification dict or None if invalid
    """
    try:
        data = json.loads(response_text)
        classifications = data.get("classifications", {})

        # Validate all expected speakers are present
        for speaker in expected_speakers:
            if speaker not in classifications:
                logger.warning(f"LLM response missing classification for {speaker}")
                return None

            # Validate required fields
            classification = classifications[speaker]
            if "role" not in classification or "confidence" not in classification:
                logger.warning(f"LLM response missing required fields for {speaker}")
                return None

            # Validate role value
            if classification["role"] not in ["Salesperson", "Customer"]:
                logger.warning(f"Invalid role for {speaker}: {classification['role']}")
                return None

        # Build result with method annotation
        result = {}
        for speaker, classification in classifications.items():
            result[speaker] = {
                "role": classification["role"],
                "method": "LLM",
                "confidence": classification["confidence"],
            }

        return result

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return None


def _classify_with_heuristic(
    conversation_turns: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Rule-based heuristic classification (fallback when LLM unavailable).

    Uses these signals in priority order:
    1. First speaker to greet = Salesperson
    2. Speaker with most turns = Salesperson
    3. Speaker mentioning prices/products = Salesperson
    4. Speaking time ratio (Salesperson typically 60-70%)

    Args:
        conversation_turns: List of conversation turn dicts

    Returns:
        Classification result dict
    """
    if not conversation_turns:
        return {}

    unique_speakers = list(set(turn["speaker"] for turn in conversation_turns))

    if len(unique_speakers) == 1:
        return {
            unique_speakers[0]: {
                "role": "Unknown",
                "method": "Heuristic",
                "confidence": 0.0,
            }
        }

    # Calculate heuristic signals
    signals = {}
    for speaker in unique_speakers:
        signals[speaker] = {
            "first_turn": False,
            "first_greeting": False,
            "turn_count": 0,
            "price_mentions": 0,
            "product_mentions": 0,
        }

    # Analyze turns
    for i, turn in enumerate(conversation_turns):
        speaker = turn["speaker"]
        signals[speaker]["turn_count"] += 1

        # First turn speaker
        if i == 0:
            signals[speaker]["first_turn"] = True

        # Check for greeting in first 3 turns
        if i < 3 and _text_matches_patterns(turn["text"], _COMPILED_GREETINGS):
            signals[speaker]["first_greeting"] = True

        # Count price/product mentions
        signals[speaker]["price_mentions"] += _count_pattern_matches(
            turn["text"], _COMPILED_PRICES
        )
        signals[speaker]["product_mentions"] += _count_pattern_matches(
            turn["text"], _COMPILED_PRODUCTS
        )

    # Apply rules in priority order
    scores = {}
    for speaker in unique_speakers:
        score = 0.0

        # Rule 1: First greeting (strongest signal)
        if signals[speaker]["first_greeting"]:
            score += 3.0

        # Rule 2: First turn (moderate signal)
        if signals[speaker]["first_turn"]:
            score += 1.5

        # Rule 3: Turn count (salesperson typically drives conversation)
        max_turns = max(s["turn_count"] for s in signals.values())
        if signals[speaker]["turn_count"] == max_turns and max_turns > 0:
            score += 1.0

        # Rule 4: Price/product mentions (salesperson knowledge)
        if signals[speaker]["price_mentions"] > 0:
            score += 2.0
        if signals[speaker]["product_mentions"] > 0:
            score += 1.5

        scores[speaker] = score

    # Classify based on scores
    sorted_speakers = sorted(scores.keys(), key=lambda s: scores[s], reverse=True)
    salesperson = sorted_speakers[0]
    customer = sorted_speakers[1]

    # Calculate confidence based on score difference
    score_diff = abs(scores[salesperson] - scores[customer])
    confidence = min(score_diff / 5.0, 1.0)  # Normalize to 0-1

    result = {
        salesperson: {
            "role": "Salesperson",
            "method": "Heuristic",
            "confidence": round(confidence, 2),
        },
        customer: {
            "role": "Customer",
            "method": "Heuristic",
            "confidence": round(confidence, 2),
        },
    }

    # Handle additional speakers (if more than 2)
    for speaker in sorted_speakers[2:]:
        result[speaker] = {
            "role": "Customer",  # Default additional speakers to Customer
            "method": "Heuristic",
            "confidence": 0.3,  # Low confidence for extras
        }

    logger.info(f"Heuristic classification: {salesperson}=Salesperson (score={scores[salesperson]:.1f}), {customer}=Customer (score={scores[customer]:.1f})")

    return result


def _format_conversation_for_llm(turns: list[dict[str, Any]]) -> str:
    """Format conversation turns for LLM prompt.

    Args:
        turns: List of conversation turn dicts

    Returns:
        Formatted conversation string
    """
    lines = []
    for turn in turns:
        lines.append(f"{turn['speaker']}: {turn['text']}")
    return "\n".join(lines)


def _text_matches_patterns(text: str, patterns: list) -> bool:
    """Check if text matches any of the compiled regex patterns.

    Args:
        text: Text to check
        patterns: List of compiled regex patterns

    Returns:
        True if any pattern matches
    """
    return any(pattern.search(text) for pattern in patterns)


def _count_pattern_matches(text: str, patterns: list) -> int:
    """Count total pattern matches in text.

    Args:
        text: Text to check
        patterns: List of compiled regex patterns

    Returns:
        Total number of pattern matches
    """
    return sum(1 for pattern in patterns if pattern.search(text))
