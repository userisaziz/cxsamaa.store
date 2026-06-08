"""NVIDIA Parakeet STT wrapper — speech-to-text via NIM API."""
import io
import logging
from typing import Any

from src.ai.nvidia_client import NVIDIAAPIError, nvidia_client
from src.config import settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> list[dict[str, Any]]:
    """Transcribe audio using NVIDIA Parakeet model.

    Args:
        audio_bytes: Raw audio data (16kHz mono WAV)
        filename: Filename for the audio file

    Returns:
        List of transcript segments:
        [
            {"start": 0.0, "end": 5.2, "text": "Hello, welcome to our store."},
            {"start": 5.5, "end": 12.1, "text": "Hi, I'm looking for a new phone."},
            ...
        ]
    """
    logger.info(f"Sending audio to Parakeet STT ({len(audio_bytes)} bytes)")

    # NVIDIA NIM audio transcription endpoint
    # Uses OpenAI-compatible /audio/transcriptions endpoint
    files = {
        "file": (filename, io.BytesIO(audio_bytes), "audio/wav"),
    }
    data = {
        "model": settings.nvidia_stt_model,
        "response_format": "verbose_json",
        "timestamp_granularities[]": "segment",
    }

    response = nvidia_client.post_multipart(
        endpoint="/audio/transcriptions",
        files=files,
        data=data,
    )

    return _parse_stt_response(response)


def _parse_stt_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse NVIDIA NIM STT response into standardized segment format.

    The API returns OpenAI-compatible format:
    {
        "text": "full transcript",
        "segments": [
            {"start": 0.0, "end": 5.2, "text": "Hello"},
            ...
        ],
        "duration": 3600.0
    }
    """
    segments = []

    # Handle segment-level timestamps
    if "segments" in response:
        for seg in response["segments"]:
            segments.append({
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
                "text": seg.get("text", "").strip(),
            })
    elif "text" in response:
        # Fallback: if no segments, return the full text as one segment
        duration = float(response.get("duration", 0))
        segments.append({
            "start": 0.0,
            "end": duration,
            "text": response["text"].strip(),
        })

    # Filter out empty segments
    segments = [s for s in segments if s["text"]]

    logger.info(f"STT produced {len(segments)} segments, total duration: {segments[-1]['end']:.1f}s" if segments else "STT produced 0 segments")
    return segments
