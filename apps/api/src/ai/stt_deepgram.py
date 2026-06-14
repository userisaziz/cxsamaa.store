"""Deepgram STT wrapper — speech-to-text via Deepgram API.

Used as fallback when NVIDIA Riva STT fails. Requires deepgram-sdk to be installed.
"""
import logging
import tempfile
from typing import Any

from deepgram import DeepgramClient, PrerecordedOptions

from src.config import settings

logger = logging.getLogger(__name__)


class DeepgramSTTClient:
    """Client for Deepgram Nova STT model."""

    def __init__(self):
        self.api_key = settings.deepgram_api_key
        self.model = settings.deepgram_model
        self.language = settings.deepgram_language
        
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is required")
        
        # Initialize Deepgram client
        self.client = DeepgramClient(self.api_key)

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
        """Transcribe audio using Deepgram STT API.

        Args:
            audio_bytes: Raw audio data (16kHz mono WAV recommended)
            filename: Filename hint for Deepgram (used for format detection)

        Returns:
            {
                "segments": [{"start": float, "end": float, "text": str}],
                "words": [{"word": str, "start": float, "end": float, "confidence": float}]
            }
        """
        logger.info("Transcribing with Deepgram STT (model=%s, language=%s)", self.model, self.language)

        try:
            # Build transcript options
            options = PrerecordedOptions(
                model=self.model,
                language=self.language,
                smart_format=True,
                utterances=True,  # Split into utterances (segments)
                word_timing=True,  # Get word-level timestamps
                punctuate=True,
                diarize=False,  # We handle diarization separately
            )

            # Make API call
            response = self.client.listen.rest.v("1").transcribe_file(
                {"buffer": audio_bytes},
                options,
                timeout=settings.deepgram_timeout,
            )

            return self._parse_deepgram_response(response)

        except Exception as e:
            logger.error(f"Deepgram STT failed: {e}")
            raise

    def _parse_deepgram_response(self, response) -> dict[str, Any]:
        """Parse Deepgram response into standardized segment and word format.

        Deepgram returns results with utterances and word-level timestamps.
        We extract both segment-level and word-level data for speaker attribution.

        Returns:
            {
                "segments": [{start, end, text}],
                "words": [{word, start, end, confidence}]
            }
        """
        segments = []
        all_words = []

        # Check if we have results
        if not response.results or not response.results.channels:
            logger.warning("Deepgram returned empty results")
            return {"segments": [], "words": []}

        channel = response.results.channels[0]

        # Extract utterances (segments)
        if channel.alternatives:
            alternative = channel.alternatives[0]
            
            # Process utterances if available
            if hasattr(alternative, 'utterances') and alternative.utterances:
                for utterance in alternative.utterances:
                    if not utterance.transcript.strip():
                        continue

                    segments.append({
                        "start": round(utterance.start, 3),
                        "end": round(utterance.end, 3),
                        "text": utterance.transcript.strip(),
                    })

            # Extract word-level timestamps
            if hasattr(alternative, 'words') and alternative.words:
                for word in alternative.words:
                    all_words.append({
                        "word": word.word,
                        "start": round(word.start, 3),
                        "end": round(word.end, 3),
                        "confidence": round(word.confidence, 3),
                    })

            # Fallback: if no utterances but we have a transcript, create one segment
            if not segments and alternative.transcript.strip():
                # Estimate segment boundaries from words
                if all_words:
                    segments.append({
                        "start": all_words[0]["start"],
                        "end": all_words[-1]["end"],
                        "text": alternative.transcript.strip(),
                    })
                else:
                    # No word timing available, estimate from audio duration
                    segments.append({
                        "start": 0.0,
                        "end": 1.0,  # Placeholder
                        "text": alternative.transcript.strip(),
                    })

        # Filter out empty segments
        segments = [s for s in segments if s["text"].strip()]

        logger.info(
            f"Deepgram STT produced {len(segments)} segments, {len(all_words)} words, "
            f"total duration: {segments[-1]['end']:.1f}s" if segments else "Deepgram STT produced 0 segments"
        )

        return {
            "segments": segments,
            "words": all_words,
        }


# Singleton instance (lazy initialization)
_deepgram_client = None


def get_deepgram_client() -> DeepgramSTTClient:
    """Get or create Deepgram client singleton."""
    global _deepgram_client
    if _deepgram_client is None:
        _deepgram_client = DeepgramSTTClient()
    return _deepgram_client


def transcribe_audio_deepgram(audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
    """Transcribe audio using Deepgram STT.

    Args:
        audio_bytes: Raw audio data (16kHz mono WAV)
        filename: Filename hint for Deepgram (used for format detection)

    Returns:
        Dict with segments and words
    """
    client = get_deepgram_client()
    return client.transcribe_audio(audio_bytes, filename)
