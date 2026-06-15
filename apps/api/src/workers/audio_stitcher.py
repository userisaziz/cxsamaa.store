"""Audio stitcher worker — Stage 6.5 of the pipeline.

After segmentation identifies conversation boundaries, this task extracts
each conversation's audio from the ORIGINAL R2 master file using FFmpeg
streaming (seek+cut). This eliminates on-the-fly ffmpeg cuts at API request
time and enables clean per-conversation audio playback.

Pipeline position:
    segment_conversations → stitch_conversation_audio → analyze_conversations

The stitcher:
    1. Generates pre-signed URL for the original R2 master file.
    2. For each conversation, uses FFmpeg to seek+cut from the remote URL.
    3. Exports the slice as a WAV and uploads to R2.
    4. Updates the conversation.audio_url field with the storage key.

CRITICAL: Never downloads or re-creates the master file. Uses streaming
extraction to keep memory at ~50MB regardless of recording length.
"""
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from src.config import settings
from src.models.conversation import Conversation
from src.models.recording import Recording, RecordingStatus
from src.workers.preprocessing import (
    _get_recording_sync,
    _update_recording_status_sync,
)

logger = logging.getLogger(__name__)

# Module-level engine — reused across task invocations in the same worker process.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine)


def _get_conversations_sync(recording_id: str) -> list[dict]:
    """Load conversation records for this recording."""
    with _SessionLocal() as session:
        rows = (
            session.query(Conversation)
            .filter(Conversation.recording_id == uuid.UUID(recording_id))
            .order_by(Conversation.start_time)
            .all()
        )
        return [
            {
                "id": str(row.id),
                "start_time": row.start_time,
                "end_time": row.end_time,
            }
            for row in rows
        ]


def _update_conversation_audio_url_sync(conversation_id: str, audio_url: str) -> None:
    """Set the audio_url on a conversation record."""
    with _SessionLocal() as session:
        session.query(Conversation).filter(
            Conversation.id == uuid.UUID(conversation_id)
        ).update({"audio_url": audio_url})
        session.commit()


def _get_master_file_source(recording_id: str, recording: dict) -> str | None:
    """Get streaming source for the original master file.
    
    For R2 storage: generates pre-signed URL for HTTP streaming
    For local storage: returns local file path
    
    Returns:
        URL or file path for FFmpeg input, or None if unavailable
    """
    from src.storage.local import get_storage
    storage = get_storage()
    is_local = hasattr(storage, "base_dir")
    
    if is_local:
        # Local storage: use direct file path
        base_dir = Path(settings.local_upload_dir)
        original_path = base_dir / recording["file_url"]
        if original_path.exists():
            logger.info("[%s] Using local master file: %s", recording_id, original_path)
            return str(original_path)
        else:
            logger.warning("[%s] Local master file not found: %s", recording_id, original_path)
            return None
    else:
        # R2 storage: generate pre-signed URL for HTTP streaming
        try:
            file_key = recording["file_url"]
            signed_url = storage.get_signed_url_sync(file_key, expires_in=3600)
            logger.info(
                "[%s] Generated pre-signed URL for R2 master: %s",
                recording_id, file_key,
            )
            return signed_url
        except Exception as e:
            logger.error(
                "[%s] Failed to generate pre-signed URL for %s: %s",
                recording_id, recording["file_url"], e,
            )
            return None


def _extract_with_ffmpeg(
    source_path: str,
    start_sec: float,
    duration_sec: float,
    output_path: str,
) -> bool:
    """Extract audio segment using FFmpeg streaming from remote URL or local file.
    
    For R2 pre-signed URLs: uses HTTP streaming with -ss before -i for fast seek
    For local files: direct file access
    
    Never downloads the full source file — only extracts the needed segment.
    """
    try:
        # Place -ss BEFORE -i for fast seek (avoids decoding from start)
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(start_sec),  # Fast seek before input
                "-i", source_path,
                "-t", str(duration_sec),
                "-ac", "1",
                "-ar", "16000",
                "-f", "wav",
                output_path,
            ],
            capture_output=True,
            timeout=300,  # 5 minutes per conversation
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
        
        if result.returncode != 0:
            logger.error(
                "FFmpeg extraction failed:\nstdout: %s\nstderr: %s",
                result.stdout.decode()[:500],
                result.stderr.decode()[:1000],
            )
            return False
        
        return True
        
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.error("FFmpeg extraction failed: %s", e)
        return False


from src.workers.retry import pipeline_retry


@pipeline_retry
def extract_conversation_audio(recording_id: str) -> str:
    """Extract per-conversation audio files using FFmpeg streaming from R2.

    For each conversation identified by segmentation, extracts audio
    directly from the ORIGINAL R2 master file using FFmpeg seek+cut.
    Never downloads or re-creates the master file.
    
    Updates conversation.audio_url with the R2 storage key.
    
    NOTE: Speaker reconciliation (metadata stitching) already happened
    in the diarization stage. This is purely audio extraction for UI playback.

    Returns:
        recording_id for the next pipeline stage.
    """
    logger.info("[%s] Starting conversation audio extraction", recording_id)
    _update_recording_status_sync(recording_id, RecordingStatus.STITCHING)

    try:
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        conversations = _get_conversations_sync(recording_id)
        if not conversations:
            logger.info("[%s] No conversations to stitch — skipping", recording_id)
            return recording_id

        logger.info(
            "[%s] Extracting audio for %d conversations", recording_id, len(conversations),
        )

        # Get streaming source for the original master file
        master_source = _get_master_file_source(recording_id, recording)
        if not master_source:
            logger.error(
                "[%s] Cannot extract audio — master file unavailable",
                recording_id,
            )
            return recording_id

        from src.storage.local import get_storage
        storage = get_storage()
        is_local = hasattr(storage, "base_dir")

        # For local storage, ensure output directory exists
        if is_local:
            output_dir = Path(settings.local_upload_dir) / f"preprocessed/{recording_id}/conversations"
            output_dir.mkdir(parents=True, exist_ok=True)

        stitched_count = 0
        for conv in conversations:
            conv_id = conv["id"]
            start_sec = conv["start_time"]
            end_sec = conv["end_time"]
            duration_sec = end_sec - start_sec

            if duration_sec <= 0:
                logger.warning(
                    "[%s] Conversation %s has zero/negative duration — skipping",
                    recording_id, conv_id,
                )
                continue

            output_filename = f"{conv_id}.wav"
            storage_key = f"preprocessed/{recording_id}/conversations/{output_filename}"

            # Use temp file for R2, direct path for local
            if is_local:
                output_path = str(Path(settings.local_upload_dir) / storage_key)
            else:
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp.close()
                output_path = tmp.name

            # Extract using FFmpeg streaming (never downloads full file)
            logger.info(
                "[%s] Extracting conversation %s: %.1fs-%.1fs (%.1fs)",
                recording_id, conv_id, start_sec, end_sec, duration_sec,
            )
            
            success = _extract_with_ffmpeg(
                master_source, start_sec, duration_sec, output_path,
            )

            if not success:
                logger.warning(
                    "[%s] Could not extract audio for conversation %s",
                    recording_id, conv_id,
                )
                if not is_local:
                    os.unlink(output_path)
                continue

            # Read the extracted file and upload to storage
            with open(output_path, "rb") as f:
                audio_data = f.read()

            # Upload to storage (local or R2)
            storage.upload_sync(audio_data, storage_key)

            # Clean up temp file for R2
            if not is_local:
                os.unlink(output_path)

            # Update the conversation record
            _update_conversation_audio_url_sync(conv_id, storage_key)
            stitched_count += 1

            logger.info(
                "[%s] Extracted conversation %s: %.1fs-%.1fs (%d bytes)",
                recording_id, conv_id, start_sec, end_sec, len(audio_data),
            )

        logger.info(
            "[%s] Audio extraction complete: %d/%d conversations",
            recording_id, stitched_count, len(conversations),
        )
        
        # Mark stage complete in pipeline_state
        from src.services.pipeline_state import mark_stage_complete_sync
        mark_stage_complete_sync(recording_id, "stitch")

        return recording_id

    except Exception as exc:
        logger.error(
            "[%s] Audio extraction failed: %s", recording_id, exc, exc_info=True,
        )
        # Don't fail the pipeline for extraction errors — log and continue
        logger.warning(
            "[%s] Audio extraction failed — continuing pipeline",
            recording_id,
        )
        
        # Still mark as complete (extraction is non-critical)
        from src.services.pipeline_state import mark_stage_complete_sync
        mark_stage_complete_sync(recording_id, "stitch")
        
        return recording_id
