"""Conversation analysis using Llama 3.3 70B via NVIDIA NIM API.

Analyzes a single conversation transcript and extracts structured business
intelligence: intent, products, budget, objections, competitors, outcome,
closing attempts, and confidence score.
"""
import json
import logging
import re
from typing import Any

from src.ai.nvidia_client import NVIDIAAPIError, nvidia_client

logger = logging.getLogger(__name__)

# Minimum confidence threshold for publishing results (PRD AI-06)
MIN_CONFIDENCE_THRESHOLD = 50

SYSTEM_PROMPT = """You are an expert retail sales analyst. You analyze customer-salesperson conversations and extract structured business intelligence.

You MUST respond with valid JSON matching this exact schema:
{
    "intent": "Primary customer purchase intent or inquiry (one concise sentence)",
    "customer_expectation": "What the customer expects or wants from the product/service (e.g. durability, warranty, features, style). One concise sentence or null if not clear",
    "products": ["product1", "product2"],
    "budget": "Budget range if mentioned (e.g. '$200-$500'), or null if not mentioned",
    "objections": [
        {
            "category": "Price|Features|Timing|Trust|Competitor|Other",
            "issue": "The specific customer concern or objection",
            "response": "How the salesperson addressed or responded to this objection"
        }
    ],
    "competitors": ["competitor1", "competitor2"],
    "closing_attempt": true,
    "outcome": "SALE_MADE" | "LOST" | "FOLLOW_UP_NEEDED",
    "loss_reason": "If outcome is LOST, a concise explanation of why the sale was lost based on the conversation. null if outcome is not LOST",
    "confidence": 0-100,
    "summary": "One paragraph summary of the conversation",
    "coaching_notes": "Specific coaching feedback for the salesperson based on their performance. Reference actual conversation moments and suggest SOP-compliant alternatives where applicable."
}

Rules:
- "outcome" must be exactly one of: SALE_MADE, LOST, FOLLOW_UP_NEEDED
- "confidence" is your confidence (0-100) in the accuracy of this analysis
- "products" should list specific products discussed or requested
- "objections" must be an array of objects with category, issue, and response. If no objections, use empty array []
- "category" must be one of: Price, Features, Timing, Trust, Competitor, Other
- "competitors" should list competitor brands mentioned
- "closing_attempt" is true if the salesperson attempted to close the sale
- "loss_reason" should only be filled when outcome is LOST, otherwise null
- "customer_expectation" captures what the customer is looking for or expects from the purchase
- "coaching_notes" should be constructive and specific, referencing actual conversation moments and suggesting best-practice SOP responses
- If the conversation is too short or unclear, set confidence below 85
- Respond ONLY with valid JSON, no additional text"""


def analyze_conversation(
    conversation_segments: list[dict[str, Any]],
    max_retries: int = 2,
) -> dict[str, Any] | None:
    """Analyze a single conversation using Llama 3.3 70B.

    Args:
        conversation_segments: List of {start, end, text, speaker} dicts
        max_retries: Number of retries for malformed responses

    Returns:
        Analysis dict matching the schema, or None if analysis fails
    """
    if not conversation_segments:
        logger.warning("Empty conversation segments — skipping analysis")
        return None

    # Format conversation for the prompt
    transcript_text = _format_transcript(conversation_segments)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze this retail conversation:\n\n{transcript_text}"},
    ]

    for attempt in range(max_retries + 1):
        try:
            response_text = nvidia_client.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            analysis = _parse_analysis_response(response_text)
            if analysis is None:
                logger.warning(f"Failed to parse analysis response (attempt {attempt + 1})")
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": "Your response was not valid JSON matching the required schema. Please try again with valid JSON only.",
                    })
                    continue
                return None

            # Validate required fields
            if not _validate_analysis(analysis):
                logger.warning(f"Analysis validation failed (attempt {attempt + 1}): {analysis}")
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": "Your response was missing required fields or had invalid values. Please ensure 'outcome' is one of SALE_MADE/LOST/FOLLOW_UP_NEEDED and 'confidence' is 0-100. Try again.",
                    })
                    continue
                return None

            return analysis

        except NVIDIAAPIError as exc:
            logger.error(f"NVIDIA API error during analysis: {exc}")
            if attempt < max_retries:
                continue
            return None
        except Exception as exc:
            logger.error(f"Unexpected error during analysis: {exc}")
            return None

    return None


def _format_transcript(segments: list[dict]) -> str:
    """Format transcript segments into readable conversation text."""
    lines = []
    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "").strip()
        start = seg.get("start", 0)
        minutes = int(start // 60)
        seconds = int(start % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")
    return "\n".join(lines)


def _parse_analysis_response(response_text: str) -> dict[str, Any] | None:
    """Parse the LLM response into a structured analysis dict."""
    # Try direct JSON parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object in the response
    brace_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.error(f"Could not parse JSON from LLM response: {response_text[:200]}...")
    return None


def _validate_analysis(analysis: dict[str, Any]) -> bool:
    """Validate that the analysis has all required fields with valid values."""
    valid_outcomes = {"SALE_MADE", "LOST", "FOLLOW_UP_NEEDED"}

    # Required fields
    if "outcome" not in analysis or analysis["outcome"] not in valid_outcomes:
        logger.warning(f"Invalid outcome: {analysis.get('outcome')}")
        return False

    if "confidence" not in analysis:
        analysis["confidence"] = 50  # Default if missing

    # Clamp confidence to 0-100
    confidence = analysis.get("confidence", 50)
    if not isinstance(confidence, (int, float)):
        analysis["confidence"] = 50
    else:
        analysis["confidence"] = max(0, min(100, int(confidence)))

    # Ensure list fields are lists
    for field in ("products", "competitors"):
        if field not in analysis or analysis[field] is None:
            analysis[field] = []
        elif isinstance(analysis[field], str):
            analysis[field] = [analysis[field]]

    # Handle objections: support both new structured objects and legacy strings
    if "objections" not in analysis or analysis["objections"] is None:
        analysis["objections"] = []
    elif isinstance(analysis["objections"], str):
        analysis["objections"] = [{"category": "Other", "issue": analysis["objections"], "response": ""}]
    elif isinstance(analysis["objections"], list):
        normalised = []
        for obj in analysis["objections"]:
            if isinstance(obj, str):
                normalised.append({"category": "Other", "issue": obj, "response": ""})
            elif isinstance(obj, dict):
                normalised.append({
                    "category": obj.get("category", "Other"),
                    "issue": obj.get("issue", str(obj)),
                    "response": obj.get("response", ""),
                })
            else:
                normalised.append({"category": "Other", "issue": str(obj), "response": ""})
        analysis["objections"] = normalised

    # Ensure boolean
    if "closing_attempt" not in analysis:
        analysis["closing_attempt"] = False
    else:
        analysis["closing_attempt"] = bool(analysis["closing_attempt"])

    # Ensure string fields
    for field in ("intent", "budget", "summary", "coaching_notes"):
        if field not in analysis or analysis[field] is None:
            analysis[field] = None if field in ("budget",) else ""

    # New nullable string fields
    for field in ("customer_expectation", "loss_reason"):
        if field not in analysis or analysis[field] is None:
            analysis[field] = None

    return True
