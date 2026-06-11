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

# Maximum speakers expected in a typical retail conversation (2-party)
MAX_RETAIL_SPEAKERS = 3

# --- Multilingual Greeting & Service Patterns ---
# These patterns identify SALESPEAKER behavior: greetings, service offers,
# product knowledge, and price/feature mentions across Arabic/Hindi/Urdu/English.

GREETING_PATTERNS = [
    # English greetings
    r"\b(welcome|hello|hi|good\s*(morning|afternoon|evening))\b",
    r"\b(come\s*in|step\s*right\s*in|take\s*a\s*look)\b",
    # Arabic greetings (Gulf + MSA)
    r"(هلا|هلا\s*والله|مرحبا|أهلا|اهلا|السلام\s*عليكم|حياك|حياك\s*الله|تفضل|تفضلي)",
    r"(كيف\s*أقدر\s*أساعدك|كيف\s*اقدر\s*اساعدك|شلون\s*أخدمك|وش\s*تبي|وش\s*تبغى)",
    # Hindi greetings
    r"(नमस्ते|नमस्कार|आइए|पधारिए|स्वागत\s*है)",
    r"(बताइए|क्या\s*हाल\s*है|कैसे\s*हैं\s*आप|जी\s*आइए)",
    # Urdu greetings
    r"(السلام\s*عليكم|آداب|خوش\s*آمدید|جی\s*آئیں|فرمائیے|بتائیے)",
    # Transliterated common retail greetings
    r"\b(hala|yalla|tفضل|khali|namaste|aao|ji\s*aao)\b",
]

SERVICE_PHRASE_PATTERNS = [
    # English service phrases
    r"\b(how\s*can\s*i\s*help|what\s*can\s*i\s*do|how\s*may\s*i\s*assist)\b",
    r"\b(let\s*me\s*show|let\s*me\s*explain|i(?:'ll|\s*will)\s*help\s*you)\b",
    # Arabic service phrases
    r"(أقدر\s*أساعدك|أساعدك|أوريك|أشرح\s*لك|أوصي\s*لك|خلني\s*أوريك)",
    r"(عندنا|لدينا|متوفر|متاح|هذي|هذا\s*الموديل|هذا\s*النوع)",
    # Hindi service phrases
    r"(मैं\s*आपकी|आपको\s*मदद|दिखाता\s*हूँ|समझाता\s*हूँ|बताता\s*हूँ)",
    r"(हमारे\s*पास|यह\s*वाला|इसमें|इसका|ये\s*लीजिए)",
    # English product/availability
    r"\b(we\s*have|we\s*carry|our\s*products|available|in\s*stock)\b",
    r"\b(this\s*model|this\s*one|let\s*me\s*show|recommend)\b",
]

PRICE_MENTION_PATTERNS = [
    r"\b(price|cost|\$\d+|discount|offer|sale|deal)\b",
    r"\b(how\s*much|what.*price|bikam|كم\s*السعر)\b",
    # Arabic price phrases
    r"(سعره|بكم|ريال|درهم|دينار|تخفيض|خصم)",
    # Hindi price phrases
    r"(कीमत|कितने\s*का|रुपये|डिस्काउंट|ऑफर)",
]

# --- Customer Signal Patterns ---
# These patterns identify CUSTOMER behavior: objections, questions,
# purchase intent, and comparison language.

CUSTOMER_SIGNAL_PATTERNS = [
    # English objections / hesitation
    r"\b(too\s*expensive|that'?s\s*(a\s*lot|pricey)|i\s*(don'?t|cant|can'?t)\s*think|i\s*need\s*to\s*think)\b",
    r"\b(maybe\s*later|not\s*sure|let\s*me\s*think|i'?ll\s*come\s*back)\b",
    # English purchase intent
    r"\b(i(?:'ll|\s*will)\s*take|i\s*want|i(?:'d|\s*would)\s*like|can\s*i\s*get|give\s*me)\b",
    r"\b(do\s*you\s*have|is\s*this\s*available|how\s*much\s*(is|does))\b",
    # Arabic customer phrases
    r"(غالي|ما\s*عندي|بفكر|خلني\s*أفكر|بعدين|إن\s*شاء\s*الله|مو\s*متأكد)",
    r"(أبيه|أبي\s*هذا|أشتريه|وش\s*عندكم|تبيعون|عندكم|هل\s*فيه)",
    # Hindi customer phrases
    r"(महंगा|बहुत|सोचना\s*है|बाद\s*में|शायद|मुझे\s*चाहिए|ले\s*लूंगा|देना)",
    r"(कितने\s*का|है\s*क्या|मिलेगा|दिखाओ|दिखाइए)",
]

PRODUCT_MENTION_PATTERNS = [
    r"\b(we\s*have|we\s*carry|our\s*products|available|in\s*stock)\b",
    r"\b(this\s*model|this\s*one|let\s*me\s*show|recommend)\b",
]

# Pre-compiled patterns
_COMPILED_GREETINGS = [re.compile(p, re.IGNORECASE) for p in GREETING_PATTERNS]
_COMPILED_SERVICE = [re.compile(p, re.IGNORECASE) for p in SERVICE_PHRASE_PATTERNS]
_COMPILED_PRICES = [re.compile(p, re.IGNORECASE) for p in PRICE_MENTION_PATTERNS]
_COMPILED_PRODUCTS = [re.compile(p, re.IGNORECASE) for p in PRODUCT_MENTION_PATTERNS]
_COMPILED_CUSTOMER = [re.compile(p, re.IGNORECASE) for p in CUSTOMER_SIGNAL_PATTERNS]


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
    # Format conversation for prompt with speaker tokens and turn numbers
    conversation_text = _format_conversation_for_llm(conversation_turns)

    # Unique speakers
    unique_speakers = list(set(turn["speaker"] for turn in conversation_turns))
    speaker_count = len(unique_speakers)

    # Speaker count warning
    speaker_count_note = ""
    if speaker_count > MAX_RETAIL_SPEAKERS:
        speaker_count_note = (
            f"\n\nNOTE: {speaker_count} speakers detected in what appears to be a "
            f"2-party retail conversation. This may indicate diarization errors. "
            f"Classify the 2 most likely primary speakers and mark extras as 'Customer' "
            f"with low confidence."
        )

    prompt = f"""You are an expert retail sales conversation analyst specializing in multilingual Gulf retail environments (Arabic, Hindi, English, Urdu code-switching).

Analyze this conversation and classify each speaker as either 'Salesperson' or 'Customer'.

KEY SIGNALS TO LOOK FOR:
1. OPENING GREETING (strongest signal): The speaker who says the first greeting/service offer (e.g., "Welcome", "هلا", "नमस्ते", "how can I help") is almost certainly the Salesperson.
2. SERVICE LANGUAGE: Phrases like "let me show you", "أوريك", "दिखाता हूँ", "we have", "عندنا" indicate Salesperson.
3. PRODUCT KNOWLEDGE: Mentioning specific features, prices, availability, models = Salesperson.
4. CUSTOMER SIGNALS: Objections ("too expensive", "غالي"), questions ("how much", "بكم"), hesitation ("let me think", "بفكر"), purchase intent ("I'll take it", "أبيه") = Customer.
5. SPEAKING PATTERS: Salesperson typically initiates, asks open questions, and drives the conversation flow.

Conversation (speaker labels are [Speaker_X] tokens, turn numbers shown):
{conversation_text}

Speakers to classify: {', '.join(unique_speakers)}{speaker_count_note}

Respond with valid JSON matching this exact schema:
{{
    "classifications": {{
        "Speaker_A": {{
            "role": "Salesperson",
            "confidence": 0.95,
            "reasoning": "Brief explanation citing specific signals (e.g., 'opened with greeting in Arabic, mentioned prices')"
        }},
        "Speaker_B": {{
            "role": "Customer",
            "confidence": 0.92,
            "reasoning": "Brief explanation citing specific signals"
        }}
    }}
}}

Rules:
- Each speaker must be classified as exactly "Salesperson" or "Customer"
- Confidence should be between 0.0 and 1.0 — be honest about uncertainty
- If a speaker has very few turns, lower confidence accordingly
- Reasoning should cite specific signals from the conversation
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
    1. First speaker to greet / offer service = Salesperson (strongest)
    2. Service phrase mentions = Salesperson
    3. Price/product mentions = Salesperson
    4. Customer signal patterns = Customer (negative salesperson score)
    5. Turn count ratio (Salesperson typically drives conversation)

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

    # Speaker count validation
    if len(unique_speakers) > MAX_RETAIL_SPEAKERS:
        logger.warning(
            f"Detected {len(unique_speakers)} speakers in retail conversation "
            f"(max expected: {MAX_RETAIL_SPEAKERS}). Possible diarization error."
        )

    # Calculate heuristic signals
    signals = {}
    for speaker in unique_speakers:
        signals[speaker] = {
            "first_turn": False,
            "first_greeting": False,
            "first_service": False,
            "turn_count": 0,
            "price_mentions": 0,
            "product_mentions": 0,
            "service_mentions": 0,
            "customer_signals": 0,
        }

    # Analyze turns
    for i, turn in enumerate(conversation_turns):
        speaker = turn["speaker"]
        signals[speaker]["turn_count"] += 1

        # First turn speaker
        if i == 0:
            signals[speaker]["first_turn"] = True

        # Check for greeting in first 3 turns (strongest signal)
        if i < 3 and _text_matches_patterns(turn["text"], _COMPILED_GREETINGS):
            signals[speaker]["first_greeting"] = True

        # Check for service phrases in first 5 turns
        if i < 5 and _text_matches_patterns(turn["text"], _COMPILED_SERVICE):
            signals[speaker]["first_service"] = True

        # Count service phrase mentions (salesperson signal)
        signals[speaker]["service_mentions"] += _count_pattern_matches(
            turn["text"], _COMPILED_SERVICE
        )

        # Count price/product mentions (salesperson knowledge)
        signals[speaker]["price_mentions"] += _count_pattern_matches(
            turn["text"], _COMPILED_PRICES
        )
        signals[speaker]["product_mentions"] += _count_pattern_matches(
            turn["text"], _COMPILED_PRODUCTS
        )

        # Count customer signal patterns (objections, questions, hesitation)
        signals[speaker]["customer_signals"] += _count_pattern_matches(
            turn["text"], _COMPILED_CUSTOMER
        )

    # Apply rules in priority order
    scores = {}
    for speaker in unique_speakers:
        score = 0.0

        # Rule 1: First greeting (STRONGEST signal — nearly definitive)
        if signals[speaker]["first_greeting"]:
            score += 5.0

        # Rule 2: First service phrase (strong signal)
        if signals[speaker]["first_service"]:
            score += 3.5

        # Rule 3: First turn (moderate signal)
        if signals[speaker]["first_turn"]:
            score += 1.5

        # Rule 4: Turn count (salesperson typically drives conversation)
        max_turns = max(s["turn_count"] for s in signals.values())
        if signals[speaker]["turn_count"] == max_turns and max_turns > 0:
            score += 1.0

        # Rule 5: Service phrase mentions (salesperson behavior)
        if signals[speaker]["service_mentions"] > 0:
            score += min(signals[speaker]["service_mentions"] * 1.5, 4.0)

        # Rule 6: Price/product mentions (salesperson knowledge)
        if signals[speaker]["price_mentions"] > 0:
            score += 2.0
        if signals[speaker]["product_mentions"] > 0:
            score += 1.5

        # Rule 7: Customer signals (NEGATIVE for salesperson = customer indicator)
        if signals[speaker]["customer_signals"] > 0:
            score -= min(signals[speaker]["customer_signals"] * 1.0, 3.0)

        scores[speaker] = score

    # Classify based on scores
    sorted_speakers = sorted(scores.keys(), key=lambda s: scores[s], reverse=True)
    salesperson = sorted_speakers[0]
    customer = sorted_speakers[1]

    # Calculate confidence based on score difference
    score_diff = abs(scores[salesperson] - scores[customer])
    # Normalize: larger denominator since max possible score is higher now
    confidence = min(score_diff / 8.0, 1.0)
    # Floor confidence at 0.1 if there's any differentiation
    if score_diff > 0:
        confidence = max(confidence, 0.1)

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

    logger.info(
        f"Heuristic classification: {salesperson}=Salesperson "
        f"(score={scores[salesperson]:.1f}), {customer}=Customer "
        f"(score={scores[customer]:.1f}), diff={score_diff:.1f}"
    )

    return result


def _format_conversation_for_llm(turns: list[dict[str, Any]]) -> str:
    """Format conversation turns for LLM prompt with speaker tokens and turn numbers.

    Uses [Speaker_X] token format (token-based approach from Zolensky et al.)
    and includes turn numbering for temporal context.

    Args:
        turns: List of conversation turn dicts

    Returns:
        Formatted conversation string with turn numbers and speaker tokens
    """
    lines = []
    for i, turn in enumerate(turns, 1):
        lines.append(f"[{i}] [{turn['speaker']}]: {turn['text']}")
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
