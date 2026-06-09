"""Audio preprocessing worker — converts raw audio to standardized format."""
import logging
import os
import tempfile
import uuid

from pydub import AudioSegment, silence

from src.config import settings
from src.models.recording import Recording, RecordingStatus
from src.storage.local import get_storage
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Preprocessing constants
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
SILENCE_THRESHOLD_DB = -40
SILENCE_GAP_MS = 30000  # 30 seconds in milliseconds
TARGET_FORMAT = "wav"


# ---------------------------------------------------------------------------
# Sync DB helpers (Celery workers run in sync context)
# ---------------------------------------------------------------------------

def _get_sync_session():
    """Create a sync DB engine + session factory."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    engine = create_engine(settings.database_url_sync)
    return sessionmaker(bind=engine), engine


def _update_recording_status_sync(recording_id: str, status: RecordingStatus, error: str | None = None):
    """Update recording status using sync DB session."""
    SessionLocal, engine = _get_sync_session()
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording:
            recording.status = status
            if error:
                recording.error_message = error
        session.commit()
    engine.dispose()


def _get_recording_sync(recording_id: str) -> dict | None:
    """Get recording data using sync DB session."""
    SessionLocal, engine = _get_sync_session()
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording:
            return {
                "id": str(recording.id),
                "file_url": recording.file_url,
                "format": recording.format,
            }
    engine.dispose()
    return None


def _update_recording_duration_sync(recording_id: str, duration_seconds: int):
    """Update recording duration using sync DB session."""
    SessionLocal, engine = _get_sync_session()
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording:
            recording.duration_seconds = duration_seconds
        session.commit()
    engine.dispose()


def _store_silence_gaps_sync(recording_id: str, silence_gaps: list[tuple[float, float]]):
    """Store silence gaps in recording.silence_gaps JSONB field."""
    SessionLocal, engine = _get_sync_session()
    with SessionLocal() as session:
        recording = session.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
        if recording:
            # Convert to list of dicts for JSONB storage
            recording.silence_gaps = [{"start": s / 1000.0, "end": e / 1000.0} for s, e in silence_gaps]
        session.commit()
    engine.dispose()


# ---------------------------------------------------------------------------
# Storage helpers (sync)
# ---------------------------------------------------------------------------

def _download_audio_sync(storage, file_url: str) -> bytes:
    """Download audio from storage using sync method."""
    return storage.download_sync(file_url)


def _upload_audio_sync(storage, data: bytes, key: str) -> str:
    """Upload audio to storage using sync method."""
    return storage.upload_sync(data, key)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="preprocess_audio")
def preprocess_audio(self, recording_id: str) -> str:
    """Preprocess raw audio: convert to mono, normalize, resample to 16kHz.

    Returns the recording_id for the next pipeline stage.
    """
    logger.info(f"[{recording_id}] Starting audio preprocessing")
    _update_recording_status_sync(recording_id, RecordingStatus.PREPROCESSING)

    try:
        # Get recording info
        recording = _get_recording_sync(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        storage = get_storage()

        # Download original audio
        file_url = recording["file_url"]
        logger.info(f"[{recording_id}] Downloading audio from {file_url}")
        audio_data = _download_audio_sync(storage, file_url)

        # Process audio in a temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Preserve original extension so ffmpeg can detect format
            ext = os.path.splitext(file_url)[1] or ".mp3"
            input_path = os.path.join(tmpdir, f"input{ext}")
            output_path = os.path.join(tmpdir, "preprocessed.wav")

            # Write downloaded audio to temp file
            with open(input_path, "wb") as f:
                f.write(audio_data)

            # Convert to WAV via ffmpeg subprocess (avoids pydub subprocess hang in Celery)
            logger.info(f"[{recording_id}] Converting audio to WAV via ffmpeg")
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, "-ac", "1", "-ar", str(TARGET_SAMPLE_RATE), "-f", "wav", output_path],
                capture_output=True,
                timeout=300,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")

            # Load preprocessed WAV
            logger.info(f"[{recording_id}] Loading preprocessed WAV")
            audio = AudioSegment.from_wav(output_path)

            # Convert to mono
            logger.info(f"[{recording_id}] Converting to mono (channels: {audio.channels})")
            if audio.channels > 1:
                audio = audio.set_channels(TARGET_CHANNELS)

            # Resample to 16kHz
            if audio.frame_rate != TARGET_SAMPLE_RATE:
                logger.info(f"[{recording_id}] Resampling {audio.frame_rate}Hz → {TARGET_SAMPLE_RATE}Hz")
                audio = audio.set_frame_rate(TARGET_SAMPLE_RATE)

            # Normalize volume (target -20 dBFS)
            logger.info(f"[{recording_id}] Normalizing volume (current: {audio.dBFS:.1f} dBFS)")
            change_in_dbfs = -20.0 - audio.dBFS
            audio = audio.apply_gain(change_in_dbfs)

            # Export preprocessed audio
            logger.info(f"[{recording_id}] Exporting preprocessed audio")
            audio.export(output_path, format=TARGET_FORMAT, parameters=["-ar", str(TARGET_SAMPLE_RATE)])

            # Read preprocessed audio
            with open(output_path, "rb") as f:
                preprocessed_data = f.read()

            # Upload preprocessed audio
            preprocessed_key = f"preprocessed/{recording_id}/audio.wav"
            _upload_audio_sync(storage, preprocessed_data, preprocessed_key)

            # Update duration
            duration_seconds = len(audio) // 1000
            _update_recording_duration_sync(recording_id, duration_seconds)

            logger.info(
                f"[{recording_id}] Preprocessing complete. "
                f"Duration: {duration_seconds}s, Size: {len(preprocessed_data)} bytes"
            )

        return recording_id

    except Exception as exc:
        logger.error(f"[{recording_id}] Preprocessing failed: {exc}")
        if self.request.retries >= self.max_retries:
            _update_recording_status_sync(recording_id, RecordingStatus.FAILED, str(exc))
        raise self.retry(exc=exc)
