"""Shared utilities for AI pipeline modules."""


def format_transcript(segments: list[dict]) -> str:
    """Format transcript segments into readable conversation text.
    
    Shared utility used by both conversation analyzer and salesperson scorer.
    
    Args:
        segments: List of {start, end, text, speaker} dicts
        
    Returns:
        Formatted transcript with [MM:SS] timestamps and speaker labels
    """
    lines = []
    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "").strip()
        start = seg.get("start", 0)
        minutes = int(start // 60)
        seconds = int(start % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")
    return "\n".join(lines)
