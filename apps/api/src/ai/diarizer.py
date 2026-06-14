"""Speaker Diarization — pyannote.audio (primary) + NVIDIA NIM (fallback)."""
import io
import logging
import threading
from typing import Any, Optional

from src.ai.nvidia_client import NVIDIAAPIError, nvidia_client
from src.ai.pyannote_diarizer import PyannoteDiarizer
from src.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded pyannote diarizer (initialized on first use)
_pyannote_diarizer: Optional[PyannoteDiarizer] = None
_pyannote_lock = threading.Lock()  # Thread-safe initialization


def _get_pyannote_diarizer() -> Optional[PyannoteDiarizer]:
    """Get or initialize pyannote diarizer (lazy loading, thread-safe)."""
    global _pyannote_diarizer
    
    if _pyannote_diarizer is not None:
        return _pyannote_diarizer
    
    # Check if pyannote is enabled and available
    if not settings.diarization_use_pyannote:
        logger.info("Pyannote diarization disabled via config")
        return None
    
    # Double-checked locking for thread safety
    with _pyannote_lock:
        if _pyannote_diarizer is None:
            try:
                _pyannote_diarizer = PyannoteDiarizer(
                    model_name=settings.pyannote_model_name,
                    device=settings.pyannote_device if settings.pyannote_device else None,
                )
                logger.info("Pyannote diarizer initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize pyannote diarizer: {e}. Falling back to NVIDIA.")
                return None
    
    return _pyannote_diarizer


def diarize_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    return_embeddings: bool = False,
) -> list[dict[str, Any]]:
    """Diarize speakers using pyannote.audio (primary) or NVIDIA NeMo (fallback).

    Pyannote.audio provides superior accuracy for multilingual retail sales audio:
    - Better handling of overlapping speech
    - Improved robustness with background noise
    - Optimized for Hindi/English/Arabic code-switching scenarios
    - Handles accent diversity across Middle East and South Asia

    Falls back to NVIDIA NIM if pyannote is disabled or fails.

    Args:
        audio_bytes: Raw audio data (16kHz mono WAV)
        filename: Filename for the audio file
        return_embeddings: If True, each segment dict will include an
            ``embedding`` key with a float32 vector (used by cross-chunk
            speaker reconciliation).

    Returns:
        List of speaker segments:
        [
            {"start": 0.0, "end": 5.2, "speaker": "Speaker_0"},
            {"start": 5.5, "end": 12.1, "speaker": "Speaker_1"},
            ...
        ]
    """
    # Try pyannote.audio (if enabled and available)
    if settings.diarization_use_pyannote:
        try:
            diarizer = _get_pyannote_diarizer()
            if diarizer:
                logger.info(f"Using pyannote diarization ({len(audio_bytes)} bytes)")
                segments = diarizer.diarize(audio_bytes, return_embeddings=return_embeddings)
                if segments:
                    logger.info(f"Pyannote diarization successful: {len(segments)} segments")
                    return segments
                logger.warning("Pyannote returned no segments")
        except Exception as e:
            logger.warning(f"Pyannote diarization failed: {e}")
    
    # No cloud fallback available (NVIDIA deprecated their diarization API)
    # Return empty list — worker layer will use rule-based speaker assignment from STT metadata
    logger.info("No diarization engine available, worker will use rule-based assignment")
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
        # Preserve UNKNOWN label — don't map it to a named speaker
        if raw_speaker == "UNKNOWN":
            seg["speaker"] = "UNKNOWN"
            continue
        if raw_speaker not in speaker_map:
            if counter < 26:
                label = f"Speaker_{chr(65 + counter)}"
            else:
                label = f"Speaker_{counter + 1}"
            speaker_map[raw_speaker] = label
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
