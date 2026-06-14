"""STT provider dispatcher — routes transcription to NVIDIA Riva Parakeet.

STT Provider is configured via the STT_PROVIDER env var (default: "riva").
"""
import logging
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
    """Transcribe audio using NVIDIA Riva Parakeet (gRPC).

    Returns:
    {
        "segments": [{"start": float, "end": float, "text": str}],
        "words":    [{"word": str, "start": float, "end": float, "confidence": float}]
    }

    Args:
        audio_bytes: Raw audio data (16 kHz mono WAV recommended)
        filename: Unused (kept for API compatibility)

    Returns:
        Dict with segments and words
    """
    logger.info("STT provider: riva")

    from src.ai.stt_riva import transcribe_audio_riva
    return transcribe_audio_riva(audio_bytes)
