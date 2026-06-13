"""STT provider dispatcher — routes transcription to Groq Whisper or NVIDIA Riva.

Configure via STT_PROVIDER env var:
  - "groq" (default): Groq Whisper Large v3 — fast, REST, no local deps
  - "riva":            NVIDIA Riva Parakeet — gRPC, requires riva-client
"""
import logging
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
    """Transcribe audio using the configured STT provider.

    Dispatches to either:
    - Groq Whisper Large v3 (REST, OpenAI-compatible)
    - NVIDIA Riva Parakeet (gRPC)

    Both return the same shape:
    {
        "segments": [{"start": float, "end": float, "text": str}],
        "words":    [{"word": str, "start": float, "end": float, "confidence": float}]
    }

    Args:
        audio_bytes: Raw audio data (16 kHz mono WAV recommended)
        filename: Filename for multipart upload (used by Groq; ignored by Riva)

    Returns:
        Dict with segments and words
    """
    provider = settings.stt_provider.lower()
    logger.info(f"STT provider: {provider}")

    if provider == "groq":
        from src.ai.groq_client import transcribe_audio_groq
        return transcribe_audio_groq(audio_bytes, filename=filename)

    elif provider == "riva":
        # Lazy import — riva-client is only needed when using NVIDIA Riva
        from src.ai.stt_riva import transcribe_audio_riva
        return transcribe_audio_riva(audio_bytes)

    else:
        raise ValueError(
            f"Unknown STT_PROVIDER '{provider}'. "
            "Set STT_PROVIDER to 'groq' or 'riva' in your .env file."
        )
