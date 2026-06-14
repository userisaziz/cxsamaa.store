"""STT provider dispatcher — routes transcription to NVIDIA Riva Parakeet with Deepgram fallback.

STT Provider is configured via the STT_PROVIDER env var (default: "riva").
Fallback provider is configured via STT_FALLBACK_PROVIDER env var (default: "deepgram").
"""
import logging
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
    """Transcribe audio using configured STT provider with automatic fallback.

    Primary: NVIDIA Riva Parakeet (gRPC)
    Fallback: Deepgram (when Riva fails)

    Returns:
    {
        "segments": [{"start": float, "end": float, "text": str}],
        "words":    [{"word": str, "start": float, "end": float, "confidence": float}]
    }

    Args:
        audio_bytes: Raw audio data (16 kHz mono WAV recommended)
        filename: Filename hint for format detection

    Returns:
        Dict with segments and words
    """
    logger.info("STT provider: %s (fallback: %s)", settings.stt_provider, settings.stt_fallback_provider)

    # Try primary provider (NVIDIA Riva)
    try:
        from src.ai.stt_riva import transcribe_audio_riva
        logger.info("Attempting transcription with NVIDIA Riva")
        result = transcribe_audio_riva(audio_bytes, filename)
        logger.info("NVIDIA Riva transcription successful")
        return result
    except Exception as e:
        logger.warning(
            "NVIDIA Riva STT failed: %s. Attempting fallback to %s...",
            e, settings.stt_fallback_provider
        )
        
        # Try fallback provider
        return _try_fallback(audio_bytes, filename, e)


def _try_fallback(audio_bytes: bytes, filename: str, primary_error: Exception) -> dict[str, Any]:
    """Attempt transcription with fallback provider.
    
    Args:
        audio_bytes: Raw audio data
        filename: Filename hint
        primary_error: The exception from the primary provider
        
    Returns:
        Dict with segments and words from fallback provider
        
    Raises:
        Exception: If fallback also fails, raises combined error
    """
    fallback_provider = settings.stt_fallback_provider
    
    if fallback_provider == "deepgram":
        try:
            from src.ai.stt_deepgram import transcribe_audio_deepgram
            logger.info("Attempting fallback transcription with Deepgram")
            result = transcribe_audio_deepgram(audio_bytes, filename)
            logger.info("Deepgram fallback transcription successful")
            return result
        except Exception as fallback_error:
            logger.error(
                "Deepgram fallback also failed: %s. Primary error: %s",
                fallback_error, primary_error
            )
            raise RuntimeError(
                f"All STT providers failed. Primary (Riva): {primary_error}. "
                f"Fallback (Deepgram): {fallback_error}"
            ) from fallback_error
    else:
        # No valid fallback configured, re-raise primary error
        logger.error("No valid fallback STT provider configured: %s", fallback_provider)
        raise primary_error
