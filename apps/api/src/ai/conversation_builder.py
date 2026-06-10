"""Conversation turn builder — merges word-level transcripts into speaker turns.

Takes word-level transcripts with speaker labels and groups them into
conversation turns based on speaker continuity and gap detection. A turn
ends when the speaker changes or there's a gap > threshold seconds.
"""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Default gap threshold in seconds — if gap between words exceeds this,
# start a new turn even if same speaker
DEFAULT_GAP_THRESHOLD = 1.0


def build_conversation_turns(
    word_transcripts: list[dict[str, Any]],
    gap_threshold: float = DEFAULT_GAP_THRESHOLD,
) -> list[dict[str, Any]]:
    """Merge word-level transcripts into speaker turns.

    A turn is a continuous sequence of words spoken by the same speaker
    with gaps less than the threshold. A new turn starts when:
    1. The speaker changes, OR
    2. The gap between consecutive words exceeds the threshold

    Args:
        word_transcripts: Sorted list of word-level transcripts from DB.
            Each dict must have: word, start_time, end_time, speaker_label
            Example:
            [{"word": "Hello", "start_time": 0.1, "end_time": 0.5,
              "confidence": 0.98, "speaker_label": "Speaker_A"}, ...]
        gap_threshold: Maximum seconds between words to continue turn.
            Default: 1.0 second

    Returns:
        List of conversation turn dicts:
        [{"speaker": "Speaker_A", "start_time": 0.1, "end_time": 5.3,
          "text": "Hello welcome to our store today", "word_count": 12}, ...]
    """
    if not word_transcripts:
        logger.info("Empty word_transcripts — no turns to build")
        return []

    # Sort by start_time to ensure chronological order
    sorted_words = sorted(word_transcripts, key=lambda w: w["start_time"])

    logger.info(f"Building conversation turns from {len(sorted_words)} words")

    turns = []
    current_turn_words = [sorted_words[0]]

    for i in range(1, len(sorted_words)):
        prev_word = current_turn_words[-1]
        curr_word = sorted_words[i]

        # Calculate gap between previous word end and current word start
        gap = curr_word["start_time"] - prev_word["end_time"]

        # Check if we should start a new turn
        speaker_changed = curr_word["speaker_label"] != prev_word["speaker_label"]
        gap_exceeded = gap > gap_threshold

        if speaker_changed or gap_exceeded:
            # Finalize current turn
            turns.append(_build_turn(current_turn_words))

            if speaker_changed:
                logger.debug(
                    f"  New turn at word {i}: speaker change "
                    f"({prev_word['speaker_label']} → {curr_word['speaker_label']})"
                )
            else:
                logger.debug(
                    f"  New turn at word {i}: gap exceeded ({gap:.2f}s > {gap_threshold}s)"
                )

            # Start new turn
            current_turn_words = [curr_word]
        else:
            # Continue current turn
            current_turn_words.append(curr_word)

    # Don't forget the last turn
    if current_turn_words:
        turns.append(_build_turn(current_turn_words))

    logger.info(f"Built {len(turns)} conversation turns from {len(sorted_words)} words")

    # Log turn statistics
    for i, turn in enumerate(turns):
        logger.debug(
            f"  Turn {i+1}: {turn['speaker']} ({turn['word_count']} words, "
            f"{turn['end_time'] - turn['start_time']:.1f}s)"
        )

    return turns


def _build_turn(words: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a conversation turn dict from a list of words.

    Args:
        words: List of word dicts belonging to the same turn

    Returns:
        Turn dict with speaker, timestamps, concatenated text, and word count
    """
    speaker = words[0]["speaker_label"]
    start_time = words[0]["start_time"]
    end_time = words[-1]["end_time"]

    # Concatenate words into text (space-separated)
    text = " ".join(w["word"] for w in words)

    # Clean up spacing around punctuation (common STT issue)
    text = _clean_text_spacing(text)

    return {
        "speaker": speaker,
        "start_time": round(start_time, 3),
        "end_time": round(end_time, 3),
        "text": text,
        "word_count": len(words),
    }


def _clean_text_spacing(text: str) -> str:
    """Clean up spacing issues in concatenated text.

    Handles common STT artifacts:
    - Remove spaces before punctuation
    - Ensure single space after punctuation

    Args:
        text: Raw concatenated text from words

    Returns:
        Cleaned text with proper spacing
    """
    # Remove space before punctuation (e.g., "hello , world" → "hello, world")
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)

    # Ensure single space after punctuation (e.g., "hello,world" → "hello, world")
    text = re.sub(r'([,.!?;:])(?=[^\s])', r'\1 ', text)

    # Remove any double spaces
    text = re.sub(r'\s{2,}', ' ', text)

    return text.strip()
