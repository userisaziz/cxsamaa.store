"""STT provider dispatcher — routes transcription to NVIDIA Riva Parakeet with Deepgram fallback.

STT Provider is configured via the STT_PROVIDER env var (default: "riva").
Fallback provider is configured via STT_FALLBACK_PROVIDER env var (default: "deepgram").
"""
import importlib
import logging
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)

# Registry of all supported STT providers.
# To add a new provider, add one line here — no other changes needed.
PROVIDERS: dict[str, tuple[str, str, str]] = {
    "riva":     ("src.ai.stt_riva",     "transcribe_audio_riva",     "NVIDIA Riva"),
    "deepgram": ("src.ai.stt_deepgram", "transcribe_audio_deepgram", "Deepgram"),
    "groq":     ("src.ai.stt_groq",     "transcribe_audio_groq",     "Groq Whisper"),
}


def _call_provider(key: str, audio_bytes: bytes, filename: str) -> tuple[dict[str, Any], str]:
    """Dynamically load and call the transcription function for the given provider key.

    Args:
        key: Provider key (must exist in PROVIDERS)
        audio_bytes: Raw audio data
        filename: Filename hint for format detection

    Returns:
        Tuple of (transcription result dict, provider display name)

    Raises:
        KeyError: If key is not in PROVIDERS
        Exception: Any exception raised by the provider's transcription function
    """
    module_path, func_name, display_name = PROVIDERS[key]
    module = importlib.import_module(module_path)
    transcribe_fn = getattr(module, func_name)
    result = transcribe_fn(audio_bytes, filename)
    return result, display_name


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
    """Transcribe audio using configured STT provider with automatic fallback.

    Primary: NVIDIA Riva Parakeet (gRPC)
    Fallback: Deepgram or Groq Whisper (when Riva fails)

    Args:
        audio_bytes: Raw audio data (16 kHz mono WAV recommended)
        filename: Filename hint for format detection

    Returns:
        {
            "segments": [{"start": float, "end": float, "text": str}],
            "words":    [{"word": str, "start": float, "end": float, "confidence": float}]
        }

    Raises:
        ValueError: If the configured primary provider is unknown
        RuntimeError: If both primary and fallback providers fail
    """
    primary = settings.stt_provider
    fallback = settings.stt_fallback_provider

    logger.info("STT provider: %s (fallback: %s)", primary, fallback)

    if primary not in PROVIDERS:
        raise ValueError(
            f"Unknown STT provider: '{primary}'. Valid options: {list(PROVIDERS)}"
        )

    # --- Try primary provider ---
    primary_error: Exception | None = None
    try:
        result, primary_name = _call_provider(primary, audio_bytes, filename)
        logger.info("%s transcription successful", primary_name)
        return result
    except Exception as e:
        _, _, primary_name = PROVIDERS[primary]
        logger.warning(
            "%s STT failed: %s. Attempting fallback: %s",
            primary_name, e, fallback,
        )
        primary_error = e

    # --- Validate fallback ---
    if not fallback:
        logger.error("No fallback STT provider configured.")
        raise primary_error

    if fallback not in PROVIDERS:
        logger.error("Unknown fallback STT provider: '%s'. Raising primary error.", fallback)
        raise primary_error

    if fallback == primary:
        logger.warning(
            "Fallback provider '%s' is the same as primary — skipping to avoid retry loop.",
            fallback,
        )
        # ✅ FIX: Re-raise immediately so _transcribe_with_retry can handle retries
        # Don't try alternative providers here — let the retry wrapper decide
        raise primary_error

    # --- Try fallback provider ---
    try:
        result, fallback_name = _call_provider(fallback, audio_bytes, filename)
        logger.info("%s fallback transcription successful", fallback_name)
        return result
    except Exception as fallback_error:
        _, _, primary_name = PROVIDERS[primary]
        _, _, fallback_name = PROVIDERS[fallback]
        logger.error(
            "Fallback %s also failed: %s. Primary error (%s): %s",
            fallback_name, fallback_error, primary_name, primary_error,
        )
        raise RuntimeError(
            f"All STT providers failed. "
            f"Primary ({primary_name}): {primary_error}. "
            f"Fallback ({fallback_name}): {fallback_error}"
        ) from fallback_error