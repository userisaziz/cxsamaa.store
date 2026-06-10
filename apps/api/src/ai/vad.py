"""Silero VAD (Voice Activity Detection) wrapper — detects speech regions in audio.

Uses Silero VAD v5 to identify speech-active segments and remove silence/dead air
before diarization and STT processing. Reduces processing costs and improves quality.
"""
import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

import torch
import torchaudio
from src.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded Silero VAD model (initialized on first use)
_silero_vad_model: Optional[tuple] = None
_silero_vad_utils: Optional[tuple] = None


def _get_silero_vad_model():
    """Get or initialize Silero VAD model (lazy loading)."""
    global _silero_vad_model, _silero_vad_utils

    if _silero_vad_model is not None:
        return _silero_vad_model, _silero_vad_utils

    if not settings.vad_use_silero:
        logger.info("Silero VAD disabled via config")
        return None, None

    try:
        # Load Silero VAD from torch hub
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )

        (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

        _silero_vad_model = model
        _silero_vad_utils = (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks)

        logger.info("Silero VAD model initialized successfully")
        return _silero_vad_model, _silero_vad_utils

    except Exception as e:
        logger.warning(f"Failed to initialize Silero VAD model: {e}. Falling back to full audio processing.")
        return None, None


def detect_speech_segments(audio_bytes: bytes) -> list[dict[str, float]]:
    """Detect speech-active regions in audio using Silero VAD.

    Args:
        audio_bytes: Raw audio data (16kHz mono PCM WAV)

    Returns:
        List of speech segments:
        [
            {"start": 0.0, "end": 12.5},
            {"start": 15.3, "end": 28.7},
            ...
        ]
        Returns empty list if VAD is disabled or fails.
    """
    model, utils = _get_silero_vad_model()
    if model is None or utils is None:
        logger.warning("Silero VAD not available — returning empty speech segments")
        return []

    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

    # Write audio bytes to temp file for VAD processing
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Load audio file
        wav, sr = torchaudio.load(tmp_path)

        # Verify sample rate (Silero expects 16kHz or 8kHz)
        if sr != 16000:
            logger.warning(f"Audio sample rate is {sr}Hz, expected 16000Hz. Resampling...")
            wav = torchaudio.functional.resample(wav, sr, 16000)
            sr = 16000

        # Convert to mono if stereo
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)

        # Detect speech timestamps
        speech_timestamps = get_speech_timestamps(
            wav,
            model,
            threshold=settings.vad_threshold,
            min_speech_duration_ms=settings.vad_min_speech_duration_ms,
            max_speech_duration_s=float("inf"),  # No max limit
            min_silence_duration_ms=settings.vad_min_silence_duration_ms,
            sampling_rate=sr,
        )

        # Convert to standardized format (milliseconds → seconds)
        segments = []
        for ts in speech_timestamps:
            segments.append({
                "start": round(ts["start"] / sr, 3),
                "end": round(ts["end"] / sr, 3),
            })

        logger.info(
            f"Silero VAD detected {len(segments)} speech segments "
            f"({segments[-1]['end']:.1f}s total duration)" if segments else "Silero VAD detected 0 speech segments"
        )

        return segments

    except Exception as e:
        logger.error(f"Silero VAD detection failed: {e}")
        return []
    finally:
        # Cleanup temp file
        Path(tmp_path).unlink(missing_ok=True)


def extract_speech_regions(audio_bytes: bytes, speech_segments: list[dict]) -> bytes:
    """Extract only speech-active regions from audio and concatenate them.

    Args:
        audio_bytes: Raw audio data (16kHz mono PCM WAV)
        speech_segments: List of speech segments from detect_speech_segments()

    Returns:
        Audio bytes containing only speech regions (silence removed)
    """
    if not speech_segments:
        logger.warning("No speech segments provided — returning original audio")
        return audio_bytes

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Load audio
        wav, sr = torchaudio.load(tmp_path)

        # Extract speech regions
        regions = []
        for seg in speech_segments:
            start_sample = int(seg["start"] * sr)
            end_sample = int(seg["end"] * sr)
            region = wav[:, start_sample:end_sample]
            regions.append(region)

        # Concatenate speech regions
        if regions:
            combined = torch.cat(regions, dim=1)

            # Save to bytes
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_tmp:
                torchaudio.save(out_tmp.name, combined, sr)
                with open(out_tmp.name, "rb") as f:
                    return f.read()
        else:
            return audio_bytes

    except Exception as e:
        logger.error(f"Failed to extract speech regions: {e}")
        return audio_bytes
    finally:
        Path(tmp_path).unlink(missing_ok=True)
