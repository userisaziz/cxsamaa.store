"""Salesperson performance scoring using Llama 3.3 70B via NVIDIA NIM API.

Scores a salesperson across 5 dimensions per the PRD (AI-07):
1. Greeting Score — warmth, professionalism, speed of initial greeting
2. Discovery Score — quality and depth of needs-finding questions
3. Product Knowledge — accuracy and depth of product explanations
4. Objection Handling — effectiveness at addressing and resolving objections
5. Closing Score — number and quality of closing attempts
"""
import json
import logging
import re
from typing import Any

from src.ai.nvidia_client import NVIDIAAPIError, nvidia_client
from src.ai.utils import format_transcript

logger = logging.getLogger(__name__)

SCORING_SYSTEM_PROMPT = """You are an expert retail sales coach. You evaluate salesperson performance across 5 dimensions.

You MUST respond with valid JSON matching this exact schema:
{
    "greeting_score": 0-100,
    "discovery_score": 0-100,
    "product_knowledge_score": 0-100,
    "objection_handling_score": 0-100,
    "closing_score": 0-100
}

Scoring criteria:

Greeting Score (0-100):
- 90-100: Warm, professional, immediate acknowledgment, uses welcoming language
- 70-89: Friendly greeting but could be more personalized
- 50-69: Basic greeting, lacks warmth or professionalism
- 0-49: No greeting or rude/abrupt start

Discovery Score (0-100):
- 90-100: Asks open-ended questions, uncovers needs, budget, timeline, preferences
- 70-89: Asks some qualifying questions but misses key areas
- 50-69: Minimal questioning, mostly reactive
- 0-49: No discovery attempts

Product Knowledge Score (0-100):
- 90-100: Detailed, accurate product info, features, benefits, comparisons
- 70-89: Good product knowledge but misses some details
- 50-69: Basic product info, lacks depth
- 0-49: Incorrect information or unable to answer questions

Objection Handling Score (0-100):
- 90-100: Acknowledges concerns, provides solutions, offers alternatives, empathetic
- 70-89: Addresses objections but could be more persuasive
- 50-69: Minimal response to objections, dismissive
- 0-49: Ignores objections or argues with customer
- Set to null/50 if no objections were raised

Closing Score (0-100):
- 90-100: Multiple natural closing attempts, creates urgency, offers next steps
- 70-89: At least one clear closing attempt
- 50-69: Weak or indirect closing attempt
- 0-49: No closing attempt at all

Respond ONLY with valid JSON, no additional text."""


def score_salesperson_performance(
    conversation_segments: list[dict[str, Any]],
    max_retries: int = 2,
) -> dict[str, int | None] | None:
    """Score a salesperson's performance in a conversation.

    Args:
        conversation_segments: List of {start, end, text, speaker} dicts
        max_retries: Number of retries for malformed responses

    Returns:
        Dict with 5 dimension scores (0-100), or None if scoring fails
    """
    if not conversation_segments:
        return None

    transcript_text = format_transcript(conversation_segments)

    messages = [
        {"role": "system", "content": SCORING_SYSTEM_PROMPT},
        {"role": "user", "content": f"Score this salesperson's performance:\n\n{transcript_text}"},
    ]

    for attempt in range(max_retries + 1):
        try:
            response_text = nvidia_client.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
            )

            scores = _parse_scores_response(response_text)
            if scores is None:
                logger.warning(f"Failed to parse scores (attempt {attempt + 1})")
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": "Your response was not valid JSON. Please respond with only the JSON scores object.",
                    })
                    continue
                return None

            return scores

        except NVIDIAAPIError as exc:
            logger.error(f"NVIDIA API error during scoring: {exc}")
            if attempt < max_retries:
                continue
            return None
        except Exception as exc:
            logger.error(f"Unexpected error during scoring: {exc}")
            return None

    return None


def _parse_scores_response(response_text: str) -> dict[str, int | None] | None:
    """Parse the LLM response into a scores dict."""
    # Try direct JSON parse
    try:
        data = json.loads(response_text)
        return _normalize_scores(data)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            return _normalize_scores(data)
        except json.JSONDecodeError:
            pass

    # Log the actual response for debugging (truncate to 500 chars)
    preview = repr(response_text[:500]) if response_text else "<empty response>"
    logger.error(f"Could not parse scores from response: {preview}")
    return None


def _normalize_scores(data: dict) -> dict[str, int | None]:
    """Normalize score values to 0-100 integers."""
    score_fields = [
        "greeting_score",
        "discovery_score",
        "product_knowledge_score",
        "objection_handling_score",
        "closing_score",
    ]

    result = {}
    for field in score_fields:
        value = data.get(field)
        if value is None:
            result[field] = None
        elif isinstance(value, (int, float)):
            result[field] = max(0, min(100, int(value)))
        else:
            result[field] = None

    return result


def compute_average_scores(score_records: list[dict]) -> dict[str, float | None]:
    """Compute average scores across multiple conversations.

    Args:
        score_records: List of score dicts from score_salesperson_performance

    Returns:
        Dict with averaged dimension scores
    """
    if not score_records:
        return {
            "avg_greeting_score": None,
            "avg_discovery_score": None,
            "avg_product_knowledge_score": None,
            "avg_objection_handling_score": None,
            "avg_closing_score": None,
        }

    dimensions = [
        "greeting_score",
        "discovery_score",
        "product_knowledge_score",
        "objection_handling_score",
        "closing_score",
    ]

    averages = {}
    for dim in dimensions:
        values = [r[dim] for r in score_records if r.get(dim) is not None]
        if values:
            averages[f"avg_{dim}"] = round(sum(values) / len(values), 1)
        else:
            averages[f"avg_{dim}"] = None

    return averages
