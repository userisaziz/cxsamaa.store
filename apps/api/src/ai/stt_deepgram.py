"""Deepgram STT wrapper — speech-to-text via Deepgram API.

Used as fallback when NVIDIA Riva STT fails. Requires deepgram-sdk>=7.0.0.
"""
import logging
from typing import Any

from deepgram import DeepgramClient

from src.config import settings

logger = logging.getLogger(__name__)


class DeepgramSTTClient:
    """Client for Deepgram Nova STT model (SDK v7)."""

    def __init__(self):
        self.api_key = settings.deepgram_api_key
        self.model = settings.deepgram_model
        self.language = settings.deepgram_language
        self.timeout = settings.deepgram_timeout  # Configurable timeout (default: 300s)

        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is required")

        # Initialize Deepgram v7 client (no config object needed in v7)
        self.client = DeepgramClient(api_key=self.api_key)

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
        """Transcribe audio using Deepgram STT API (v7).

        Args:
            audio_bytes: Raw audio data (16kHz mono WAV recommended)
            filename: Filename hint for Deepgram (used for format detection)

        Returns:
            {
                "segments": [{"start": float, "end": float, "text": str}],
                "words": [{"word": str, "start": float, "end": float, "confidence": float}]
            }
        """
        logger.info(
            "Transcribing with Deepgram STT (model=%s, language=%s)",
            self.model,
            self.language,
        )

        try:
            # Deepgram v7 API: transcribe_file takes bytes directly + keyword args
            # Note: Deepgram SDK v7 doesn't support timeout parameter directly.
            # Timeout is handled at the HTTP client level via environment variables
            # or by wrapping the call with a timeout decorator.
            response = self.client.listen.v1.media.transcribe_file(
                request=audio_bytes,
                model=self.model,
                language=self.language,
                smart_format=True,
                utterances=True,
                punctuate=True,
                diarize=True,
            )
            return self._parse_deepgram_response(response)
        except Exception as e:
            logger.error("Deepgram STT failed: %s", e)
            raise

    def _parse_deepgram_response(self, response) -> dict[str, Any]:
        """Parse Deepgram response into standardized segment and word format.

        Deepgram returns results with utterances and word-level timestamps.
        When diarize=True, each utterance/word carries a speaker integer (0, 1, …)
        which we map to "SPEAKER_0", "SPEAKER_1", etc.

        Returns:
            {
                "segments": [{start, end, text, speaker}],
                "words": [{word, start, end, confidence, speaker}]
            }
        """
        segments = []
        all_words = []

        if not response.results or not response.results.channels:
            logger.warning("Deepgram returned empty results")
            return {"segments": [], "words": []}

        channel = response.results.channels[0]

        if not channel.alternatives:
            logger.warning("Deepgram returned no alternatives")
            return {"segments": [], "words": []}

        alternative = channel.alternatives[0]

        # Extract word-level timestamps first (needed for fallback segment boundaries)
        if hasattr(alternative, "words") and alternative.words:
            for word in alternative.words:
                speaker_int = getattr(word, "speaker", None)
                all_words.append({
                    "word": word.word,
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                    "confidence": round(word.confidence, 3),
                    "speaker": f"SPEAKER_{speaker_int}" if speaker_int is not None else "UNKNOWN",
                })

        # ✅ FIX: utterances live at response.results.utterances, not alternative.utterances
        utterances = getattr(response.results, "utterances", None)
        if utterances:
            for utterance in utterances:
                if not utterance.transcript.strip():
                    continue
                speaker_int = getattr(utterance, "speaker", None)
                segments.append({
                    "start": round(utterance.start, 3),
                    "end": round(utterance.end, 3),
                    "text": utterance.transcript.strip(),
                    "speaker": f"SPEAKER_{speaker_int}" if speaker_int is not None else "UNKNOWN",
                })

        # Fallback: no utterances — build segments from words by grouping with silence gaps
        if not segments and all_words:
            # Group words into segments by silence gaps > 1.5s
            current_group = [all_words[0]]
            for word in all_words[1:]:
                if word["start"] - current_group[-1]["end"] > 1.5:
                    # Determine speaker by majority vote in the group
                    group_speaker = _majority_speaker(current_group)
                    segments.append({
                        "start": current_group[0]["start"],
                        "end": current_group[-1]["end"],
                        "text": " ".join(w["word"] for w in current_group),
                        "speaker": group_speaker,
                    })
                    current_group = [word]
                else:
                    current_group.append(word)
            if current_group:
                group_speaker = _majority_speaker(current_group)
                segments.append({
                    "start": current_group[0]["start"],
                    "end": current_group[-1]["end"],
                    "text": " ".join(w["word"] for w in current_group),
                    "speaker": group_speaker,
                })

        # Last-resort fallback: transcript string only, no word timestamps
        if not segments and hasattr(alternative, "transcript") and alternative.transcript.strip():
            segments.append({
                "start": 0.0,
                "end": 1.0,
                "text": alternative.transcript.strip(),
            })

        # Filter out empty segments
        segments = [s for s in segments if s["text"].strip()]

        if segments:
            logger.info(
                "Deepgram STT produced %d segments, %d words, total duration: %.1fs",
                len(segments),
                len(all_words),
                segments[-1]["end"],
            )
        else:
            logger.info("Deepgram STT produced 0 segments")

        return {
            "segments": segments,
            "words": all_words,
        }


# Singleton instance (lazy initialization)
_deepgram_client: DeepgramSTTClient | None = None


def _majority_speaker(words: list[dict]) -> str:
    """Return the most frequent speaker label from a group of diarized words."""
    from collections import Counter
    speakers = [w.get("speaker", "UNKNOWN") for w in words]
    return Counter(speakers).most_common(1)[0][0]


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