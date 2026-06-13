"""Groq Whisper Large v3 STT client — OpenAI-compatible speech-to-text via Groq API.

Replaces NVIDIA Riva gRPC STT for production deployments. Groq hosts Whisper Large v3
with near-instant transcription speed and word-level timestamps.

API docs: https://console.groq.com/docs/speech-to-text
"""
import io
import logging
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class GroqAPIError(Exception):
    """Base exception for Groq API errors."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class GroqSTTClient:
    """HTTP client for Groq Whisper Large v3 speech-to-text."""

    def __init__(self):
        self.base_url = settings.groq_base_url
        self.api_key = settings.groq_api_key
        self.model = settings.groq_stt_model
        self.language = settings.groq_stt_language or None
        self.timeout = 120  # 2 minutes per transcription

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
        """Transcribe audio using Groq Whisper Large v3.

        Args:
            audio_bytes: Raw audio data (WAV, MP3, etc. — 16 kHz mono WAV recommended)
            filename: Filename for the multipart upload (helps Groq detect format)

        Returns:
            Dict with segments and words:
            {
                "segments": [{"start": float, "end": float, "text": str}],
                "words": [{"word": str, "start": float, "end": float, "confidence": float}]
            }

        Raises:
            GroqAPIError: If the Groq API returns an error
        """
        if not self.api_key:
            raise GroqAPIError("GROQ_API_KEY is not configured")

        logger.info(f"Sending audio to Groq Whisper ({len(audio_bytes)} bytes, model={self.model})")

        url = f"{self.base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        # Build multipart form data
        # Groq requires: file, model, response_format=verbose_json, timestamp_granularities[]=word
        files = {
            "file": (filename, io.BytesIO(audio_bytes), "audio/wav"),
        }
        data = {
            "model": self.model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word",
        }
        if self.language:
            data["language"] = self.language

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, files=files, data=data, headers=headers)

            if response.status_code != 200:
                logger.error(f"Groq STT error ({response.status_code}): {response.text}")
                raise GroqAPIError(
                    f"Groq API error ({response.status_code}): {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            result = response.json()
            return self._parse_response(result)

        except httpx.TimeoutException as exc:
            raise GroqAPIError(f"Groq STT request timed out: {exc}")
        except httpx.ConnectError as exc:
            raise GroqAPIError(f"Groq STT connection failed: {exc}")

    def _parse_response(self, result: dict[str, Any]) -> dict[str, Any]:
        """Parse Groq verbose_json response into standardized segment and word format.

        Groq response shape (verbose_json with word timestamps):
        {
            "task": "transcribe",
            "language": "english",
            "duration": 20.0,
            "text": "...",
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 4.0,
                    "text": "Hello world",
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 1.2},
                        {"word": "world", "start": 1.3, "end": 2.0}
                    ]
                }
            ]
        }

        Returns:
            {"segments": [...], "words": [...]}
        """
        segments = []
        all_words = []

        groq_segments = result.get("segments", [])
        for seg in groq_segments:
            seg_start = float(seg.get("start", 0.0))
            seg_end = float(seg.get("end", 0.0))
            seg_text = (seg.get("text") or "").strip()

            if not seg_text:
                continue

            segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": seg_text,
            })

            # Extract word-level timestamps if available
            words = seg.get("words", [])
            for w in words:
                word_text = (w.get("word") or "").strip()
                if not word_text:
                    continue
                all_words.append({
                    "word": word_text,
                    "start": round(float(w.get("start", 0.0)), 3),
                    "end": round(float(w.get("end", 0.0)), 3),
                    "confidence": round(float(w.get("confidence", 0.85)), 3),
                })

        language = result.get("language", "unknown")
        duration = result.get("duration", 0.0)
        logger.info(
            f"Groq STT: {len(segments)} segments, {len(all_words)} words, "
            f"language={language}, duration={duration:.1f}s"
        )

        return {
            "segments": segments,
            "words": all_words,
        }


# Singleton instance
groq_stt_client = GroqSTTClient()


def transcribe_audio_groq(audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
    """Transcribe audio using Groq Whisper Large v3.

    Args:
        audio_bytes: Raw audio data (16 kHz mono WAV recommended)
        filename: Filename for multipart upload

    Returns:
        Dict with segments and words
    """
    return groq_stt_client.transcribe_audio(audio_bytes, filename=filename)
