"""Cross-chunk speaker reconciliation via Agglomerative Clustering.

When audio is processed in parallel chunks, the same physical speaker gets
different labels in each chunk (e.g., "Speaker_A" in chunk 0 might be the
same person as "Speaker_B" in chunk 3). This module uses speaker embedding
vectors to unify labels across all chunks.

Architecture:
    1. Collect per-speaker mean embeddings from each chunk.
    2. Build a distance matrix from cosine similarities.
    3. Run Agglomerative Clustering with a distance threshold tuned for
       retail environments (2-4 speakers, accent diversity).
    4. Output a unified speaker mapping that the merge step uses to
       rewrite per-chunk speaker labels into global labels.

Falls back to identity mapping (no reconciliation) if:
    - Embeddings are unavailable (NVIDIA fallback diarization).
    - Only one chunk was processed (no cross-chunk problem).
    - Fewer than 2 unique speakers exist.
"""
import logging
from collections import defaultdict
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_distances

logger = logging.getLogger(__name__)

# Clustering distance threshold. Two speaker embeddings closer than this are
# considered the same speaker. Tuned for pyannote/embedding 512-d vectors
# on multilingual retail audio (Hindi/English/Arabic).
# Lower = more conservative (fewer merges, more speakers detected)
# Higher = more aggressive (more merges, may collapse distinct speakers)
RECONCILIATION_THRESHOLD = 0.55


def _cosine_distance_matrix(embeddings: np.ndarray) -> np.ndarray:
    """Compute pairwise cosine distance matrix for a set of embeddings."""
    return cosine_distances(embeddings)


def reconcile_speakers_across_chunks(
    chunk_speaker_segments: list[list[dict[str, Any]]],
    chunk_offsets: list[float],
    threshold: float = RECONCILIATION_THRESHOLD,
) -> dict[str, str]:
    """Unify speaker labels across multiple diarization chunks.

    Args:
        chunk_speaker_segments: List of per-chunk speaker segment lists.
            Each segment dict should have: start, end, speaker, and
            optionally ``embedding`` (float32 vector).
        chunk_offsets: List of time offsets (seconds) for each chunk,
            corresponding to the chunk's start position in the full audio.
        threshold: Agglomerative clustering distance threshold.

    Returns:
        Mapping from ``"{chunk_index}:{original_speaker}"`` to a unified
        global speaker label like ``"Speaker_A"``.

        Example:
            {
                "0:Speaker_0": "Speaker_A",   # chunk 0's Speaker_0 → global A
                "0:Speaker_1": "Speaker_B",
                "1:Speaker_0": "Speaker_A",   # chunk 1's Speaker_0 is same person!
                "1:Speaker_1": "Speaker_B",
            }

        If reconciliation is not possible (missing embeddings, single chunk),
        returns identity mapping preserving original labels.
    """
    if not chunk_speaker_segments or len(chunk_speaker_segments) < 2:
        logger.info("Speaker reconciliation skipped: fewer than 2 chunks")
        return _build_identity_mapping(chunk_speaker_segments)

    # -----------------------------------------------------------------------
    # 1. Collect per-speaker mean embeddings from each chunk
    # -----------------------------------------------------------------------
    # Key: "chunk_idx:speaker_label", Value: mean embedding vector
    speaker_embeddings: dict[str, np.ndarray] = {}
    speaker_segment_counts: dict[str, int] = {}

    for chunk_idx, segments in enumerate(chunk_speaker_segments):
        # Group embeddings by speaker within this chunk
        per_speaker: dict[str, list[np.ndarray]] = defaultdict(list)

        for seg in segments:
            emb = seg.get("embedding")
            if emb is None:
                continue
            vec = np.array(emb, dtype=np.float32)
            if vec.size == 0:
                continue
            per_speaker[seg["speaker"]].append(vec)

        if not per_speaker:
            # This chunk has no embeddings — fall back to identity for it
            for seg in segments:
                key = f"{chunk_idx}:{seg['speaker']}"
                if key not in speaker_embeddings:
                    speaker_embeddings[key] = None  # type: ignore[assignment]
            continue

        for speaker, vecs in per_speaker.items():
            key = f"{chunk_idx}:{speaker}"
            # Average all embeddings for this speaker in this chunk
            speaker_embeddings[key] = np.mean(vecs, axis=0)
            speaker_segment_counts[key] = len(vecs)

    # -----------------------------------------------------------------------
    # 2. Check if reconciliation is feasible
    # -----------------------------------------------------------------------
    valid_keys = [k for k, v in speaker_embeddings.items() if v is not None]

    if len(valid_keys) < 2:
        logger.info(
            "Speaker reconciliation skipped: only %d speakers with embeddings",
            len(valid_keys),
        )
        return _build_identity_mapping(chunk_speaker_segments)

    # Check if ANY chunk is missing embeddings — if so, we can't reliably
    # reconcile across all chunks. Fall back to identity.
    missing_chunks = set()
    for chunk_idx, segments in enumerate(chunk_speaker_segments):
        chunk_speakers = set(seg["speaker"] for seg in segments if seg.get("speaker") != "UNKNOWN")
        chunk_has_emb = any(f"{chunk_idx}:{s}" in valid_keys for s in chunk_speakers)
        if chunk_speakers and not chunk_has_emb:
            missing_chunks.add(chunk_idx)

    if missing_chunks:
        logger.warning(
            "Speaker reconciliation skipped: chunks %s have no embeddings. "
            "Falling back to identity mapping.",
            sorted(missing_chunks),
        )
        return _build_identity_mapping(chunk_speaker_segments)

    # -----------------------------------------------------------------------
    # 3. Run Agglomerative Clustering on mean embeddings
    # -----------------------------------------------------------------------
    embedding_matrix = np.array([speaker_embeddings[k] for k in valid_keys])
    distance_matrix = _cosine_distance_matrix(embedding_matrix)

    # AgglomerativeClustering with precomputed distances and a distance threshold
    # n_clusters=None lets the algorithm decide based on the threshold
    clustering = AgglomerativeClustering(
        n_clusters=None,
        metric="precomputed",
        linkage="average",
        distance_threshold=threshold,
    )
    labels = clustering.fit_predict(distance_matrix)

    unique_clusters = len(set(labels))
    logger.info(
        "Speaker reconciliation: %d speakers across chunks → %d global speakers",
        len(valid_keys),
        unique_clusters,
    )

    # -----------------------------------------------------------------------
    # 4. Build the unified mapping
    # -----------------------------------------------------------------------
    # Map cluster IDs to friendly labels (Speaker_A, Speaker_B, ...)
    cluster_to_label: dict[int, str] = {}
    for cluster_id in sorted(set(labels)):
        if cluster_id < 26:
            cluster_to_label[cluster_id] = f"Speaker_{chr(65 + cluster_id)}"
        else:
            cluster_to_label[cluster_id] = f"Speaker_{cluster_id + 1}"

    # Build the final mapping: "chunk_idx:original_speaker" → "Speaker_X"
    speaker_mapping: dict[str, str] = {}
    for i, key in enumerate(valid_keys):
        speaker_mapping[key] = cluster_to_label[labels[i]]

    # Add entries for speakers without embeddings (pass through as UNKNOWN or keep original)
    for key in speaker_embeddings:
        if key not in valid_keys:
            speaker_mapping[key] = "UNKNOWN"

    logger.info("Speaker reconciliation mapping: %s", speaker_mapping)
    return speaker_mapping


def apply_speaker_mapping(
    chunk_speaker_segments: list[list[dict[str, Any]]],
    speaker_mapping: dict[str, str],
    chunk_offsets: list[float],
) -> list[dict[str, Any]]:
    """Apply the reconciliation mapping and produce unified speaker segments.

    Args:
        chunk_speaker_segments: Per-chunk speaker segments.
        speaker_mapping: Output of reconcile_speakers_across_chunks().
        chunk_offsets: Per-chunk time offsets (seconds).

    Returns:
        Flat list of speaker segments with global labels and adjusted timestamps.
    """
    all_segments = []

    for chunk_idx, segments in enumerate(chunk_speaker_segments):
        offset = chunk_offsets[chunk_idx] if chunk_idx < len(chunk_offsets) else 0.0

        for seg in segments:
            key = f"{chunk_idx}:{seg['speaker']}"
            global_speaker = speaker_mapping.get(key, seg.get("speaker", "UNKNOWN"))

            all_segments.append({
                "start": seg["start"] + offset,
                "end": seg["end"] + offset,
                "speaker": global_speaker,
            })

    # Sort by start time
    all_segments.sort(key=lambda s: s["start"])

    # Merge adjacent segments from the same speaker (bridges chunk boundaries)
    merged = _merge_adjacent_same_speaker(all_segments, max_gap=2.0)

    logger.info(
        "Speaker reconciliation: %d raw segments → %d merged segments",
        len(all_segments),
        len(merged),
    )

    return merged


def _merge_adjacent_same_speaker(
    segments: list[dict[str, Any]],
    max_gap: float = 2.0,
) -> list[dict[str, Any]]:
    """Merge adjacent segments from the same speaker if gap <= max_gap."""
    if not segments:
        return []

    merged = [dict(segments[0])]

    for seg in segments[1:]:
        prev = merged[-1]
        gap = seg["start"] - prev["end"]

        if seg["speaker"] == prev["speaker"] and gap <= max_gap:
            prev["end"] = max(prev["end"], seg["end"])
        else:
            merged.append(dict(seg))

    return merged


def _build_identity_mapping(
    chunk_speaker_segments: list[list[dict[str, Any]]],
) -> dict[str, str]:
    """Build an identity mapping that preserves original speaker labels."""
    mapping: dict[str, str] = {}
    for chunk_idx, segments in enumerate(chunk_speaker_segments):
        for seg in segments:
            key = f"{chunk_idx}:{seg['speaker']}"
            mapping[key] = seg.get("speaker", "UNKNOWN")
    return mapping
