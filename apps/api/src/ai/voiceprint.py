"""Voiceprint enrollment and speaker verification using open-source embeddings.

Supports two free engines (zero paid dependencies):
- pyannote/embedding — speaker embeddings from the pyannote.audio project (already in project)
- resemblyzer — open-source speaker encoder (pip install resemblyzer, fallback)

Speaker embeddings are stored as vectors in the speaker_voiceprints table,
enabling cross-conversation speaker tracking and automatic salesperson identification.
"""
from __future__ import annotations

import logging
import threading
import tempfile
from pathlib import Path
from typing import Protocol

import numpy as np
import torch
from sqlalchemy import select, update, func
from sqlalchemy.exc import NoResultFound

from src.config import settings
from src.database import async_session_factory
from src.models.transcript import SpeakerVoiceprint

logger = logging.getLogger(__name__)

# Minimum cosine similarity to consider two voiceprints as the same speaker
SIMILARITY_THRESHOLD = 0.80

# Embedding dimensions per engine
ENGINE_DIMENSIONS = {
    "pyannote": 512,
    "resemblyzer": 256,
}

# Thread-safe engine initialization
_pyannote_model = None
_pyannote_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────
# Pyannote Embedding Engine (primary, free, already in project)
# ──────────────────────────────────────────────────────────────

def _get_pyannote_embedding_model():
    """Lazy-load pyannote/embedding model (thread-safe).

    This is the same embedding backbone used inside the pyannote 3.1
    diarization pipeline, exposed directly for speaker verification.
    """
    global _pyannote_model

    if _pyannote_model is not None:
        return _pyannote_model

    with _pyannote_lock:
        if _pyannote_model is None:
            try:
                from pyannote.audio import Model

                hf_token = settings.pyannote_hf_token or None
                model = Model.from_pretrained(
                    "pyannote/embedding",
                    token=hf_token,
                )

                # Move to device
                if torch.cuda.is_available():
                    device = torch.device("cuda")
                elif torch.backends.mps.is_available():
                    device = torch.device("mps")
                else:
                    device = torch.device("cpu")
                model.to(device)
                model.eval()

                _pyannote_model = model
                logger.info("Pyannote embedding model loaded on %s", device)
            except Exception as e:
                logger.error("Failed to load pyannote embedding model: %s", e)
                return None

    return _pyannote_model


def extract_embedding_pyannote(audio_bytes: bytes, sample_rate: int = 16000) -> np.ndarray | None:
    """Extract a speaker embedding vector from audio using pyannote.

    Args:
        audio_bytes: Raw 16kHz mono WAV audio bytes
        sample_rate: Audio sample rate (default 16kHz)

    Returns:
        512-dim numpy embedding vector, or None on failure
    """
    model = _get_pyannote_embedding_model()
    if model is None:
        return None

    try:
        from pyannote.audio import Inference
        from pyannote.audio.core.io import Audio
        import torchaudio
        import io

        # Load audio from bytes
        waveform, sr = torchaudio.load(io.BytesIO(audio_bytes))
        if sr != 16000:
            resampler = torchaudio.transforms.Resample(sr, 16000)
            waveform = resampler(waveform)
            sr = 16000

        # Ensure mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Extract embedding using pyannote Inference
        inference = Inference(model, window="whole")
        embedding = inference({"waveform": waveform, "sample_rate": sr})

        # Convert to numpy and normalize
        vec = embedding.cpu().numpy().flatten()
        vec = vec / (np.linalg.norm(vec) + 1e-8)

        logger.info("Extracted pyannote embedding: shape=%s", vec.shape)
        return vec

    except Exception as e:
        logger.error("Pyannote embedding extraction failed: %s", e)
        return None


# ──────────────────────────────────────────────────────────────
# Resemblyzer Engine (fallback, free, pip install resemblyzer)
# ──────────────────────────────────────────────────────────────

def extract_embedding_resemblyzer(audio_bytes: bytes, sample_rate: int = 16000) -> np.ndarray | None:
    """Extract a speaker embedding using Resemblyzer (open source).

    Args:
        audio_bytes: Raw 16kHz mono WAV audio bytes
        sample_rate: Audio sample rate

    Returns:
        256-dim numpy embedding vector, or None on failure
    """
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav
        import io

        # Load and preprocess audio
        wav = preprocess_wav(io.BytesIO(audio_bytes))

        # Encode
        encoder = VoiceEncoder()
        embedding = encoder.embed_utterance(wav)

        # Normalize
        vec = embedding / (np.linalg.norm(embedding) + 1e-8)

        logger.info("Extracted resemblyzer embedding: shape=%s", vec.shape)
        return vec

    except ImportError:
        logger.warning("Resemblyzer not installed. pip install resemblyzer")
        return None
    except Exception as e:
        logger.error("Resemblyzer embedding extraction failed: %s", e)
        return None


# ──────────────────────────────────────────────────────────────
# Unified Engine Interface
# ──────────────────────────────────────────────────────────────

def extract_embedding(
    audio_bytes: bytes,
    engine: str = "pyannote",
    sample_rate: int = 16000,
) -> np.ndarray | None:
    """Extract a speaker embedding using the specified engine.

    Tries the requested engine first, falls back to the other.

    Args:
        audio_bytes: Raw 16kHz mono WAV audio bytes
        engine: "pyannote" (default) or "resemblyzer"
        sample_rate: Audio sample rate

    Returns:
        Normalized embedding vector, or None if all engines fail
    """
    if engine == "pyannote":
        vec = extract_embedding_pyannote(audio_bytes, sample_rate)
        if vec is not None:
            return vec
        logger.info("Pyannote failed, falling back to resemblyzer")
        return extract_embedding_resemblyzer(audio_bytes, sample_rate)
    else:
        vec = extract_embedding_resemblyzer(audio_bytes, sample_rate)
        if vec is not None:
            return vec
        logger.info("Resemblyzer failed, falling back to pyannote")
        return extract_embedding_pyannote(audio_bytes, sample_rate)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two embedding vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ──────────────────────────────────────────────────────────────
# Voiceprint Protocol & DB Operations
# ──────────────────────────────────────────────────────────────

class VoiceprintEngine(Protocol):
    """Protocol for voiceprint engine implementations."""

    def enroll(self, audio_bytes: bytes) -> bytes: ...
    def verify(self, audio_bytes: bytes, voiceprint_bytes: bytes) -> float: ...


async def create_voiceprint_record(
    salesperson_id: str,
    recording_id: str | None = None,
    engine: str = "pyannote",
    notes: str | None = None,
) -> SpeakerVoiceprint:
    """Create a pending voiceprint enrollment record."""
    async with async_session_factory() as db:
        voiceprint = SpeakerVoiceprint(
            salesperson_id=salesperson_id,
            recording_id=recording_id,
            engine=engine,
            status="pending",
            sample_count=0,
            notes=notes,
        )
        db.add(voiceprint)
        await db.commit()
        await db.refresh(voiceprint)
        logger.info("Created voiceprint enrollment: %s (engine=%s)", salesperson_id, engine)
        return voiceprint


async def get_enrolled_voiceprints(store_id: str) -> list[dict]:
    """Get all enrolled voiceprints for a store's salespeople."""
    from sqlalchemy import text

    async with async_session_factory() as db:
        result = await db.execute(
            text("""
                SELECT vp.id, vp.salesperson_id, vp.engine, vp.voiceprint_bytes,
                       s.name as salesperson_name
                FROM speaker_voiceprints vp
                JOIN salespeople s ON s.id = vp.salesperson_id
                WHERE s.store_id = :store_id AND vp.status = 'enrolled'
            """),
            {"store_id": store_id},
        )

        voiceprints = []
        for row in result:
            voiceprints.append({
                "voiceprint_id": str(row[0]),
                "salesperson_id": str(row[1]),
                "engine": row[2],
                "voiceprint_data": row[3],
                "salesperson_name": row[4],
            })

        return voiceprints


async def complete_enrollment(
    voiceprint_id: str,
    voiceprint_data: bytes,
    engine: str = "pyannote",
    sample_duration_seconds: float | None = None,
) -> bool:
    """Complete voiceprint enrollment with actual voiceprint data."""
    async with async_session_factory() as db:
        result = await db.execute(
            update(SpeakerVoiceprint)
            .where(SpeakerVoiceprint.id == voiceprint_id)
            .values(
                engine=engine,
                voiceprint_bytes=voiceprint_data,
                status="enrolled",
                sample_duration_seconds=sample_duration_seconds,
                sample_count=1,
            )
        )
        await db.commit()
        logger.info("Completed voiceprint enrollment: %s", voiceprint_id)
        return result.rowcount > 0


async def match_speaker(
    audio_bytes: bytes,
    store_id: str,
    engine: str = "pyannote",
) -> dict | None:
    """Match an audio sample against enrolled voiceprints for a store.

    Returns:
        {"salesperson_id": ..., "salesperson_name": ..., "confidence": ...}
        or None if no match found above threshold
    """
    # Extract embedding from the sample
    sample_embedding = extract_embedding(audio_bytes, engine=engine)
    if sample_embedding is None:
        logger.warning("Could not extract embedding for speaker matching")
        return None

    # Get enrolled voiceprints for this store
    enrolled = await get_enrolled_voiceprints(store_id)
    if not enrolled:
        logger.info("No enrolled voiceprints for store %s", store_id)
        return None

    # Compare against each enrolled voiceprint
    best_match = None
    best_similarity = 0.0

    for vp in enrolled:
        if vp["voiceprint_data"] is None:
            continue

        try:
            enrolled_embedding = np.frombuffer(vp["voiceprint_data"], dtype=np.float32)
            sim = cosine_similarity(sample_embedding, enrolled_embedding)

            if sim > best_similarity:
                best_similarity = sim
                best_match = vp
        except Exception as e:
            logger.warning("Failed to compare voiceprint %s: %s", vp["voiceprint_id"], e)

    if best_match and best_similarity >= SIMILARITY_THRESHOLD:
        logger.info(
            "Speaker matched: %s (confidence=%.2f)",
            best_match["salesperson_name"],
            best_similarity,
        )
        return {
            "salesperson_id": best_match["salesperson_id"],
            "salesperson_name": best_match["salesperson_name"],
            "confidence": round(best_similarity, 3),
        }

    logger.info("No speaker match above threshold (%.2f < %.2f)", best_similarity, SIMILARITY_THRESHOLD)
    return None
