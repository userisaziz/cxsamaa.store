"""Speaker diarization worker — assigns speaker labels to transcript segments."""
import logging
import uuid
from collections import Counter

from celery import chord, group
from celery.exceptions import Ignore
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.ai.diarizer import assign_speaker_labels, diarize_audio as diarize_audio_api
from src.ai.speaker_reconciliation import apply_speaker_mapping, reconcile_speakers_across_chunks
from src.config import settings
from src.models.recording import RecordingStatus
from src.models.transcript import TranscriptSegment, WordTranscript
from src.storage.local import get_storage
from src.workers.celery_app import celery_app
from src.workers.pipeline_control import PipelineHalted, fail_and_halt
from src.workers.preprocessing import (
    _get_recording_sync,
    _update_recording_status_sync,
    load_manifest,
)

logger = logging.getLogger(__name__)

# Module-level engine — reused across task invocations in the same worker process.
# Celery workers are long-lived processes, so creating an engine per DB call
# wastes connections and adds latency.
_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine)


def _get_transcript_segments_sync(recording_id: str) -> list[dict]:
    """Load transcript segments from DB using sync session."""
    with _SessionLocal() as session:
        rows = (
            session.query(TranscriptSegment)
            .filter(TranscriptSegment.recording_id == uuid.UUID(recording_id))
            .order_by(TranscriptSegment.start_time)
            .all()
        )
        return [
            {"start": row.start_time, "end": row.end_time, "text": row.text}
            for row in rows
        ]


def _update_word_speaker_labels_sync(recording_id: str, labeled_segments: list[dict]) -> None:
    """Propagate segment speaker labels to word-level transcripts by time containment.

    Assigns each word the speaker label of the segment containing its midpoint.
    Uses an O(W + S) sweep since both words and segments are time-ordered.
    """
    segs = sorted(labeled_segments, key=lambda s: s["start"])
    with _SessionLocal() as session:
        words = (
            session.query(WordTranscript)
            .filter(WordTranscript.recording_id == uuid.UUID(recording_id))
            .order_by(WordTranscript.start_time)
            .all()
        )
        si = 0
        for word in words:
            mid = (word.start_time + word.end_time) / 2.0
            # Advance segment pointer
            while si < len(segs) - 1 and segs[si]["end"] < mid:
                si += 1
            word.speaker_label = (
                segs[si]["speaker"]
                if segs[si]["start"] <= mid <= segs[si]["end"]
                else "UNKNOWN"
            )
        session.commit()
    logger.info(
        "[%s] Updated speaker labels for %d words", recording_id, len(words)
    )


def _update_speaker_labels_sync(recording_id: str, labeled_segments: list[dict]) -> None:
    """Write speaker labels back to transcript_segments table."""
    with _SessionLocal() as session:
        for seg in labeled_segments:
            session.query(TranscriptSegment).filter(
                TranscriptSegment.recording_id == uuid.UUID(recording_id),
                TranscriptSegment.start_time == seg["start"],
                TranscriptSegment.end_time == seg["end"],
            ).update({"speaker_label": seg["speaker"]})
        session.commit()
    logger.info(
        "[%s] Updated speaker labels for %d segments",
        recording_id,
        len(labeled_segments),
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, name="diarize_audio")
def diarize_audio(self, recording_id: str) -> str:
    """Diarize speakers using pyannote.audio (primary) or NVIDIA NeMo (fallback).

    Pyannote.audio provides superior accuracy for multilingual retail sales audio:
    - Better handling of overlapping speech
    - Improved robustness with background noise
    - Optimized for Hindi/English/Arabic code-switching scenarios
    - Handles accent diversity across Middle East and South Asia

    Falls back to NVIDIA NIM if pyannote is disabled or fails.

    Returns:
        recording_id for the next pipeline stage.
    """
    logger.info("[%s] Starting speaker diarization", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.DIARIZING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()

        preprocessed_key = f"preprocessed/{recording_id}/audio.wav"
        logger.info("[%s] Downloading preprocessed audio for diarization", recording_id)
        audio_data = storage.download_sync(preprocessed_key)

        logger.info("[%s] Running diarization (pyannote.audio primary)", recording_id)
        speaker_segments = diarize_audio_api(audio_data)
        logger.info(
            "[%s] Diarization produced %d speaker segments",
            recording_id,
            len(speaker_segments),
        )

        transcript_segments = _get_transcript_segments_sync(recording_id)
        if not transcript_segments:
            fail_and_halt(recording_id, "No transcript segments found after transcription")

        labeled_segments = assign_speaker_labels(transcript_segments, speaker_segments)
        _update_speaker_labels_sync(recording_id, labeled_segments)
        _update_word_speaker_labels_sync(recording_id, labeled_segments)

        speaker_counts = Counter(seg["speaker"] for seg in labeled_segments)
        logger.info("[%s] Speaker distribution: %s", recording_id, dict(speaker_counts))

        return recording_id

    except PipelineHalted:
        raise Ignore()
    except Exception as exc:
        logger.error("[%s] Diarization failed: %s", recording_id, exc, exc_info=True)

        # FIX 3: only retry while attempts remain; on the final failure
        # update status to FAILED and re-raise the original exception so
        # callers see the real error, not MaxRetriesExceededError.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise


# ---------------------------------------------------------------------------
# Parallel chunk tasks (dispatched via chord)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="dispatch_diarization")
def dispatch_diarization(self, recording_id: str):
    """Dispatch parallel diarization chunk tasks or take fast path.

    Reads the chunk manifest produced by preprocessing. If the recording
    is short enough, delegates to the existing single-task fast path.
    Otherwise replaces itself with a chord of parallel chunk tasks.

    Since chunks are split at silence-gap boundaries (conversation
    boundaries), cross-chunk speaker reconciliation is applied after
    merging to unify speaker labels across chunks using Agglomerative
    Clustering on speaker embeddings.
    """
    logger.info("[%s] Dispatching diarization", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.DIARIZING)

    manifest = load_manifest(recording_id)

    if not manifest["needs_chunking"]:
        # Fast path: short recording, use existing task directly
        try:
            return diarize_audio(recording_id)
        except PipelineHalted:
            raise Ignore()

    # Build parallel chunk group
    header = group(
        diarize_chunk.s(
            recording_id,
            chunk["index"],
            chunk["file"],
        )
        for chunk in manifest["chunks"]
    )

    logger.info(
        "[%s] Dispatching %d parallel diarization chunks",
        recording_id, len(manifest["chunks"]),
    )

    # Replace self with chord: header runs in parallel, callback merges
    raise self.replace(
        chord(header, merge_diarization_results.s(recording_id))
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120,
                 soft_time_limit=1800, time_limit=2400,
                 name="diarize_chunk")
def diarize_chunk(self, recording_id: str, chunk_index: int, chunk_file: str):
    """Diarize a single audio chunk. Idempotent with acks_late.

    Downloads only its own chunk file from storage.
    Returns a dict with speaker segments — never raises past max_retries,
    returns a failure sentinel instead to prevent chord errors.
    """
    logger.info(
        "[%s] Diarizing chunk %d (%s)", recording_id, chunk_index, chunk_file,
    )
    try:
        storage = get_storage()
        chunk_key = f"preprocessed/{recording_id}/chunks/{chunk_file}"
        chunk_data = storage.download_sync(chunk_key)

        speaker_segments = diarize_audio_api(chunk_data, return_embeddings=True)

        logger.info(
            "[%s] Chunk %d: %d speaker segments (with embeddings)",
            recording_id, chunk_index, len(speaker_segments),
        )

        return {
            "chunk_index": chunk_index,
            "speaker_segments": speaker_segments,
            "failed": False,
        }
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        # Return sentinel instead of raising — prevents chord error
        logger.error(
            "[%s] Diarization chunk %d failed permanently: %s",
            recording_id, chunk_index, exc,
        )
        return {
            "chunk_index": chunk_index,
            "speaker_segments": [],
            "failed": True,
            "error": str(exc),
        }


@celery_app.task(bind=True, name="merge_diarization_results")
def merge_diarization_results(self, chunk_results: list, recording_id: str):
    """Merge diarization results from all chunks and assign speaker labels.

    Chord callback that receives a list of chunk result dicts.
    Applies cross-chunk speaker reconciliation via Agglomerative
    Clustering on speaker embeddings to unify labels across chunks.

    Assigns speaker labels to both TranscriptSegment and WordTranscript.

    Returns recording_id for the next pipeline stage.
    """
    logger.info("[%s] Merging %d diarization chunk results", recording_id, len(chunk_results))

    manifest = load_manifest(recording_id)
    chunk_offsets = {c["index"]: c["start_ms"] / 1000.0 for c in manifest["chunks"]}

    # -----------------------------------------------------------------------
    # Cross-chunk speaker reconciliation
    # -----------------------------------------------------------------------
    # If we have per-chunk speaker segments with embeddings, run reconciliation
    # to unify labels across chunks. Otherwise fall back to the old behaviour.
    _update_recording_status_sync(recording_id, RecordingStatus.RECONCILING)

    chunk_speaker_segments_by_index: dict[int, list[dict]] = {}
    for result in chunk_results:
        if result.get("failed"):
            continue
        chunk_speaker_segments_by_index[result["chunk_index"]] = result["speaker_segments"]

    has_embeddings = any(
        seg.get("embedding") is not None
        for segs in chunk_speaker_segments_by_index.values()
        for seg in segs
    )

    if has_embeddings and len(chunk_speaker_segments_by_index) >= 2:
        # Build ordered lists aligned with chunk_offsets
        sorted_indices = sorted(chunk_speaker_segments_by_index.keys())
        ordered_segments = [chunk_speaker_segments_by_index[i] for i in sorted_indices]
        ordered_offsets = [chunk_offsets.get(i, 0.0) for i in sorted_indices]

        speaker_mapping = reconcile_speakers_across_chunks(
            ordered_segments, ordered_offsets,
        )
        all_speaker_segments = apply_speaker_mapping(
            ordered_segments, speaker_mapping, ordered_offsets,
        )
        logger.info(
            "[%s] Cross-chunk reconciliation: %d segments with unified labels",
            recording_id, len(all_speaker_segments),
        )
    else:
        # Fallback: collect segments with adjusted timestamps (original behavior)
        logger.info(
            "[%s] Skipping cross-chunk reconciliation (no embeddings or single chunk)",
            recording_id,
        )
        all_speaker_segments = []
        for result in chunk_results:
            if result.get("failed"):
                continue
            offset = chunk_offsets.get(result["chunk_index"], 0.0)
            for seg in result["speaker_segments"]:
                seg["start"] = seg["start"] + offset
                seg["end"] = seg["end"] + offset
                all_speaker_segments.append(seg)
        all_speaker_segments.sort(key=lambda s: s["start"])

    failed_count = sum(1 for r in chunk_results if r.get("failed"))
    logger.info(
        "[%s] Collected %d speaker segments from %d/%d chunks",
        recording_id, len(all_speaker_segments),
        len(chunk_results) - failed_count, len(chunk_results),
    )

    # Assign speaker labels to transcript segments
    transcript_segments = _get_transcript_segments_sync(recording_id)
    if not transcript_segments:
        fail_and_halt(recording_id, "No transcript segments found after transcription")

    labeled_segments = assign_speaker_labels(transcript_segments, all_speaker_segments)
    _update_speaker_labels_sync(recording_id, labeled_segments)

    # CRITICAL: Also update WordTranscript speaker labels so turn_builder works
    _update_word_speaker_labels_sync(recording_id, labeled_segments)

    speaker_counts = Counter(seg["speaker"] for seg in labeled_segments)
    logger.info(
        "[%s] Speaker distribution: %s (from %d chunks, %d failed)",
        recording_id, dict(speaker_counts),
        len(chunk_results), failed_count,
    )

    return recording_id