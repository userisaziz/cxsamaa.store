"""NVIDIA NeMo Speaker Diarization wrapper via NIM API."""
import io
import logging
from typing import Any

from src.ai.nvidia_client import NVIDIAAPIError, nvidia_client
from src.config import settings

logger = logging.getLogger(__name__)


def diarize_audio(audio_bytes: bytes, filename: str = "audio.wav") -> list[dict[str, Any]]:
    """Diarize speakers in audio using NVIDIA NeMo.

    Args:
        audio_bytes: Raw audio data (16kHz mono WAV)
        filename: Filename for the audio file

    Returns:
        List of speaker segments:
        [
            {"start": 0.0, "end": 5.2, "speaker": "Speaker_0"},
            {"start": 5.5, "end": 12.1, "speaker": "Speaker_1"},
            ...
        ]
    """
    logger.info(f"Sending audio to NeMo diarization ({len(audio_bytes)} bytes)")

    files = {
        "file": (filename, io.BytesIO(audio_bytes), "audio/wav"),
    }
    data = {
        "model": settings.nvidia_diarization_model,
    }

    try:
        response = nvidia_client.post_multipart(
            endpoint="/audio/transcriptions",
            files=files,
            data=data,
        )
        return _parse_diarization_response(response)
    except NVIDIAAPIError as e:
        logger.warning(f"Diarization API failed: {e}. Using fallback diarization.")
        return []


def _parse_diarization_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse NVIDIA NIM diarization response.

    Expected format varies by model. Common formats:
    - {"segments": [{"start": 0, "end": 5, "speaker": "SPEAKER_00"}]}
    - {"words": [{"start": 0, "end": 0.5, "speaker": "SPEAKER_00", "word": "hello"}]}
    """
    segments = []

    if "segments" in response:
        for seg in response["segments"]:
            segments.append({
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
                "speaker": seg.get("speaker", "UNKNOWN"),
            })
    elif "words" in response:
        # Word-level diarization — aggregate into speaker segments
        segments = _aggregate_word_segments(response["words"])

    logger.info(f"Diarization produced {len(segments)} speaker segments")
    return segments


def _aggregate_word_segments(words: list[dict]) -> list[dict]:
    """Aggregate word-level speaker labels into contiguous speaker segments."""
    if not words:
        return []

    segments = []
    current_speaker = words[0].get("speaker", "UNKNOWN")
    current_start = float(words[0].get("start", 0))
    current_end = float(words[0].get("end", 0))

    for word in words[1:]:
        speaker = word.get("speaker", "UNKNOWN")
        end = float(word.get("end", 0))

        if speaker == current_speaker:
            current_end = end
        else:
            segments.append({
                "start": current_start,
                "end": current_end,
                "speaker": current_speaker,
            })
            current_speaker = speaker
            current_start = float(word.get("start", 0))
            current_end = end

    # Add last segment
    segments.append({
        "start": current_start,
        "end": current_end,
        "speaker": current_speaker,
    })

    return segments


def assign_speaker_labels(
    transcript_segments: list[dict],
    speaker_segments: list[dict],
) -> list[dict]:
    """Merge speaker labels from diarization into transcript segments.

    Uses temporal overlap to determine which speaker is speaking during
    each transcript segment.

    Args:
        transcript_segments: STT output [{start, end, text}]
        speaker_segments: Diarization output [{start, end, speaker}]

    Returns:
        Transcript segments with speaker labels assigned
    """
    if not speaker_segments:
        # Fallback: alternate speakers based on gaps
        return _fallback_speaker_assignment(transcript_segments)

    result = []
    for tseg in transcript_segments:
        t_start = tseg["start"]
        t_end = tseg["end"]

        # Find the speaker with most overlap in this time range
        speaker_overlap: dict[str, float] = {}
        for sseg in speaker_segments:
            # Calculate overlap
            overlap_start = max(t_start, sseg["start"])
            overlap_end = min(t_end, sseg["end"])
            overlap = max(0, overlap_end - overlap_start)

            if overlap > 0:
                speaker = sseg["speaker"]
                speaker_overlap[speaker] = speaker_overlap.get(speaker, 0) + overlap

        if speaker_overlap:
            assigned_speaker = max(speaker_overlap, key=speaker_overlap.get)
        else:
            assigned_speaker = "UNKNOWN"

        result.append({
            **tseg,
            "speaker": assigned_speaker,
        })

    # Normalize speaker labels to Speaker_A, Speaker_B, etc.
    return _normalize_speaker_labels(result)


def _normalize_speaker_labels(segments: list[dict]) -> list[dict]:
    """Normalize speaker labels to friendly names (Speaker_A, Speaker_B, etc.)."""
    speaker_map: dict[str, str] = {}
    counter = 0

    for seg in segments:
        raw_speaker = seg["speaker"]
        if raw_speaker not in speaker_map:
            speaker_map[raw_speaker] = f"Speaker_{chr(65 + counter)}"  # A, B, C...
            counter += 1
        seg["speaker"] = speaker_map[raw_speaker]

    return segments


def _fallback_speaker_assignment(segments: list[dict]) -> list[dict]:
    """Fallback: assign speakers based on gap detection.

    Assumes that segments separated by large gaps are different speakers.
    Alternates between Speaker_A and Speaker_B.
    """
    if not segments:
        return []

    result = []
    current_speaker = "Speaker_A"
    prev_end = 0.0
    gap_threshold = 2.0  # 2 second gap suggests speaker change

    for seg in segments:
        gap = seg["start"] - prev_end
        if gap > gap_threshold and prev_end > 0:
            # Switch speaker on large gap
            current_speaker = "Speaker_B" if current_speaker == "Speaker_A" else "Speaker_A"

        result.append({**seg, "speaker": current_speaker})
        prev_end = seg["end"]

    return result
