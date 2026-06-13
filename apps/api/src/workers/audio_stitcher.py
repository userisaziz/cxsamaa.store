"""Audio stitcher worker — Stage 6.5 of the pipeline.

After segmentation identifies conversation boundaries, this task extracts
each conversation's audio from the preprocessed full WAV and uploads it as
a standalone file. This eliminates on-the-fly ffmpeg cuts at API request
time and enables clean per-conversation audio playback.

Pipeline position:
    segment_conversations → stitch_conversation_audio → analyze_conversations

The stitcher:
    1. Loads the preprocessed 16kHz mono WAV (or falls back to the original file).
    2. For each conversation, slices the audio between start_time and end_time.
    3. Exports the slice as a WAV and uploads to storage.
    4. Updates the conversation.audio_url field with the storage key.

If the preprocessed WAV is unavailable (e.g., already cleaned up for storage),
the task falls back to ffmpeg-based extraction from the original upload.
"""
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from pydub import AudioSegment

from src.config import settings
from src.models.conversation import Conversation
from src.models.recording import Recording, RecordingStatus
from src.workers.celery_app import celery_app
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


def _load_preprocessed_audio(recording_id: str) -> tuple[AudioSegment | None, str | None]:
    """Try to load the preprocessed WAV from storage.

    Returns:
        (audio_segment, source_path) or (None, None) if unavailable.
    """
    from src.storage.local import get_storage
    storage = get_storage()
    is_local = hasattr(storage, "base_dir")

    preprocessed_key = f"preprocessed/{recording_id}/audio.wav"

    if is_local:
        base_dir = Path(settings.local_upload_dir)
        preprocessed_path = base_dir / preprocessed_key

        if preprocessed_path.exists():
            try:
                audio = AudioSegment.from_wav(str(preprocessed_path))
                logger.info(
                    "[%s] Loaded preprocessed WAV: %s (%ds)",
                    recording_id, preprocessed_path, len(audio) // 1000,
                )
                return audio, str(preprocessed_path)
            except Exception as e:
                logger.warning("[%s] Failed to load preprocessed WAV: %s", recording_id, e)
    else:
        # Cloud storage — download to temp file
        try:
            audio_bytes = storage.download_sync(preprocessed_key)
            import io
            audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
            logger.info(
                "[%s] Downloaded preprocessed WAV from cloud (%ds)",
                recording_id, len(audio) // 1000,
            )
            # Return a temp path for ffmpeg fallback if needed
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(audio_bytes)
            tmp.close()
            return audio, tmp.name
        except Exception as e:
            logger.warning("[%s] Failed to download preprocessed WAV from cloud: %s", recording_id, e)

    return None, None


def _extract_with_ffmpeg(
    source_path: str,
    start_sec: float,
    duration_sec: float,
    output_path: str,
) -> bool:
    """Extract audio segment using ffmpeg subprocess. Fallback for non-WAV sources."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-i", source_path,
                "-t", str(duration_sec),
                "-ac", "1",
                "-ar", "16000",
                "-f", "wav",
                output_path,
            ],
            capture_output=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.error("ffmpeg extraction failed: %s", e)
        return False


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=600,
    time_limit=900,
    name="stitch_conversation_audio",
)
def stitch_conversation_audio(self, recording_id: str) -> str:
    """Extract and store per-conversation audio files.

    For each conversation identified by segmentation, slices the audio
    from the preprocessed WAV and uploads it as a standalone file.
    Updates conversation.audio_url with the storage key.

    Returns:
        recording_id for the next pipeline stage.
    """
    logger.info("[%s] Starting conversation audio stitching", recording_id)
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
            "[%s] Stitching audio for %d conversations", recording_id, len(conversations),
        )

        # Try to load the preprocessed WAV for fast pydub slicing
        audio, preprocessed_path = _load_preprocessed_audio(recording_id)

        # Fallback source for ffmpeg extraction
        fallback_source = None
        if audio is None:
            base_dir = Path(settings.local_upload_dir)
            original_path = base_dir / recording["file_url"]
            if original_path.exists():
                fallback_source = str(original_path)
            else:
                logger.warning(
                    "[%s] Neither preprocessed WAV nor original file available — "
                    "audio stitching skipped",
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

            # For local storage, write to disk directly; for cloud, use temp file
            if is_local:
                output_path = str(Path(settings.local_upload_dir) / storage_key)
            else:
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp.close()
                output_path = tmp.name

            success = False

            if audio is not None:
                # Fast path: pydub slice from in-memory audio
                try:
                    start_ms = int(start_sec * 1000)
                    end_ms = int(end_sec * 1000)
                    # Clamp to audio length
                    end_ms = min(end_ms, len(audio))
                    conv_audio = audio[start_ms:end_ms]

                    conv_audio.export(
                        output_path,
                        format="wav",
                        parameters=["-ar", "16000", "-ac", "1"],
                    )
                    success = True
                except Exception as e:
                    logger.warning(
                        "[%s] pydub slice failed for conversation %s: %s — trying ffmpeg",
                        recording_id, conv_id, e,
                    )

            if not success and fallback_source:
                # Slow path: ffmpeg extraction from original file
                success = _extract_with_ffmpeg(
                    fallback_source, start_sec, duration_sec, output_path,
                )

            if not success:
                logger.warning(
                    "[%s] Could not extract audio for conversation %s",
                    recording_id, conv_id,
                )
                if not is_local:
                    os.unlink(output_path)
                continue

            # Read the file and upload to storage
            with open(output_path, "rb") as f:
                audio_data = f.read()

            # Upload to storage (local or cloud)
            storage.upload_sync(audio_data, storage_key)

            # Clean up temp file for cloud storage
            if not is_local:
                os.unlink(output_path)

            # Update the conversation record
            _update_conversation_audio_url_sync(conv_id, storage_key)
            stitched_count += 1

            logger.info(
                "[%s] Stitched conversation %s: %.1fs-%.1fs (%d bytes)",
                recording_id, conv_id, start_sec, end_sec, len(audio_data),
            )

            # Clean up local file (storage has the copy)
            try:
                os.unlink(output_path)
            except OSError:
                pass

        logger.info(
            "[%s] Audio stitching complete: %d/%d conversations stitched",
            recording_id, stitched_count, len(conversations),
        )

        return recording_id

    except Exception as exc:
        logger.error(
            "[%s] Audio stitching failed: %s", recording_id, exc, exc_info=True,
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        # Don't fail the pipeline for stitching errors — log and continue
        logger.warning(
            "[%s] Audio stitching failed after max retries — continuing pipeline",
            recording_id,
        )
        return recording_id
