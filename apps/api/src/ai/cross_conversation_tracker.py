"""Cross-conversation speaker tracking using segment embeddings.

Identifies the same speaker across multiple recordings by comparing
768-dim text embeddings stored on TranscriptSegment. While these are
text (not speaker) embeddings, they capture enough speaker-characteristic
patterns (vocabulary, speaking style, code-switching patterns) to enable
speaker clustering across conversations in a retail environment.

For true speaker biometrics, use the voiceprint module (pyannote embeddings).
This module is complementary — it works without any enrollment.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transcript import TranscriptSegment, SpeakerRole

logger = logging.getLogger(__name__)

# Cosine similarity threshold to consider two speakers as the same person
SIMILARITY_THRESHOLD = 0.85

# Minimum segments required to build a reliable speaker profile
MIN_SEGMENTS_FOR_PROFILE = 3


@dataclass
class SpeakerProfile:
    """Aggregated embedding profile for a speaker within one recording."""

    recording_id: str
    speaker_label: str
    role_label: str | None
    embedding_mean: np.ndarray  # Mean of all segment embeddings
    segment_count: int
    segment_ids: list[str] = field(default_factory=list)


@dataclass
class SpeakerCluster:
    """Cluster of speaker profiles identified as the same person."""

    cluster_id: str
    profiles: list[SpeakerProfile]
    centroid: np.ndarray
    role_label: str | None = None

    @property
    def recording_count(self) -> int:
        return len(set(p.recording_id for p in self.profiles))

    @property
    def total_segments(self) -> int:
        return sum(p.segment_count for p in self.profiles)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


async def get_speaker_profiles_for_recording(
    db: AsyncSession,
    recording_id: str,
) -> list[SpeakerProfile]:
    """Build speaker profiles from segment embeddings for one recording.

    Groups TranscriptSegments by speaker_label and computes the mean
    embedding per speaker. Only speakers with enough segments with
    embeddings are included.

    Args:
        db: Database session
        recording_id: Recording UUID

    Returns:
        List of SpeakerProfile objects (one per speaker)
    """
    # Fetch segments with embeddings
    result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.recording_id == recording_id)
        .where(TranscriptSegment.embedding.isnot(None))
        .order_by(TranscriptSegment.start_time)
    )
    segments = result.scalars().all()

    if not segments:
        logger.info("No segments with embeddings for recording %s", recording_id)
        return []

    # Fetch speaker roles for this recording
    role_result = await db.execute(
        select(SpeakerRole).where(SpeakerRole.recording_id == recording_id)
    )
    roles = {sr.speaker_label: sr.role_label for sr in role_result.scalars().all()}

    # Group by speaker
    speaker_embeddings: dict[str, list[np.ndarray]] = {}
    speaker_segment_ids: dict[str, list[str]] = {}

    for seg in segments:
        if seg.embedding is None:
            continue
        label = seg.speaker_label
        if label not in speaker_embeddings:
            speaker_embeddings[label] = []
            speaker_segment_ids[label] = []
        speaker_embeddings[label].append(np.array(seg.embedding))
        speaker_segment_ids[label].append(str(seg.id))

    # Build profiles
    profiles = []
    for speaker_label, embeddings in speaker_embeddings.items():
        if len(embeddings) < MIN_SEGMENTS_FOR_PROFILE:
            logger.debug(
                "Speaker %s has only %d segments (need %d), skipping",
                speaker_label,
                len(embeddings),
                MIN_SEGMENTS_FOR_PROFILE,
            )
            continue

        embedding_matrix = np.stack(embeddings)
        mean_embedding = embedding_matrix.mean(axis=0)
        # L2 normalize
        norm = np.linalg.norm(mean_embedding)
        if norm > 1e-8:
            mean_embedding = mean_embedding / norm

        profiles.append(
            SpeakerProfile(
                recording_id=recording_id,
                speaker_label=speaker_label,
                role_label=roles.get(speaker_label),
                embedding_mean=mean_embedding,
                segment_count=len(embeddings),
                segment_ids=speaker_segment_ids[speaker_label],
            )
        )

    logger.info(
        "Built %d speaker profiles for recording %s",
        len(profiles),
        recording_id,
    )
    return profiles


def cluster_speakers(
    profiles: list[SpeakerProfile],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[SpeakerCluster]:
    """Cluster speaker profiles across recordings using agglomerative clustering.

    Uses average-linkage agglomerative clustering with cosine similarity.
    Profiles above the threshold are merged into the same cluster.

    Args:
        profiles: Speaker profiles from multiple recordings
        threshold: Cosine similarity threshold for merging

    Returns:
        List of SpeakerCluster objects
    """
    if not profiles:
        return []

    n = len(profiles)

    # Start with each profile as its own cluster
    clusters: list[list[int]] = [[i] for i in range(n)]
    centroids = [p.embedding_mean.copy() for p in profiles]

    # Agglomerative merge loop
    while len(clusters) > 1:
        best_sim = -1.0
        best_i = -1
        best_j = -1

        # Find most similar pair of clusters
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                sim = cosine_similarity(centroids[i], centroids[j])
                if sim > best_sim:
                    best_sim = sim
                    best_i = i
                    best_j = j

        # Stop if best similarity is below threshold
        if best_sim < threshold:
            break

        # Merge cluster j into cluster i
        clusters[best_i].extend(clusters[best_j])
        # Recompute centroid as mean of all member profiles
        merged_embeddings = np.stack(
            [profiles[idx].embedding_mean for idx in clusters[best_i]]
        )
        centroids[best_i] = merged_embeddings.mean(axis=0)
        norm = np.linalg.norm(centroids[best_i])
        if norm > 1e-8:
            centroids[best_i] = centroids[best_i] / norm

        # Remove cluster j
        clusters.pop(best_j)
        centroids.pop(best_j)

    # Build SpeakerCluster objects
    result = []
    for idx, cluster_indices in enumerate(clusters):
        member_profiles = [profiles[i] for i in cluster_indices]
        # Use most common role label in cluster
        role_counts: dict[str, int] = {}
        for p in member_profiles:
            if p.role_label:
                role_counts[p.role_label] = role_counts.get(p.role_label, 0) + 1
        most_common_role = max(role_counts, key=role_counts.get) if role_counts else None

        result.append(
            SpeakerCluster(
                cluster_id=f"cluster_{idx}",
                profiles=member_profiles,
                centroid=centroids[idx],
                role_label=most_common_role,
            )
        )

    logger.info(
        "Clustered %d profiles into %d speaker clusters",
        len(profiles),
        len(result),
    )
    return result


async def find_cross_conversation_speakers(
    db: AsyncSession,
    recording_ids: list[str],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[SpeakerCluster]:
    """End-to-end: find same speakers across multiple recordings.

    Builds speaker profiles for each recording, then clusters them
    to identify who appears in multiple conversations.

    Args:
        db: Database session
        recording_ids: List of recording UUIDs to analyze
        threshold: Cosine similarity threshold

    Returns:
        List of SpeakerCluster objects. Clusters with recording_count > 1
        indicate the same person appears in multiple recordings.
    """
    all_profiles = []
    for recording_id in recording_ids:
        profiles = await get_speaker_profiles_for_recording(db, recording_id)
        all_profiles.extend(profiles)

    if not all_profiles:
        logger.info("No speaker profiles found across %d recordings", len(recording_ids))
        return []

    clusters = cluster_speakers(all_profiles, threshold=threshold)

    # Sort by number of recordings (most cross-conversation speakers first)
    clusters.sort(key=lambda c: c.recording_count, reverse=True)

    cross_conversation = [c for c in clusters if c.recording_count > 1]
    logger.info(
        "Found %d cross-conversation speakers across %d recordings",
        len(cross_conversation),
        len(recording_ids),
    )

    return clusters
