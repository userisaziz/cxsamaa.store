"""Pipeline chain orchestration for audio processing."""
from celery import chain

from src.workers.preprocessing import preprocess_audio
from src.workers.transcription import dispatch_transcription
from src.workers.diarization import dispatch_diarization
from src.workers.turn_builder import build_conversation_turns_task
from src.workers.role_classification import classify_speaker_roles_task
from src.workers.segmentation import segment_conversations
from src.workers.audio_stitcher import stitch_conversation_audio
from src.workers.analysis import analyze_conversations
from src.workers.scoring import score_salesperson


def start_processing_pipeline(recording_id: str):
    """Start the full audio processing pipeline for a recording.

    Uses dispatcher tasks that self.replace into chords for parallel chunk
    processing. Chunk count is determined at runtime after preprocessing
    computes the manifest.

    Pipeline stages:
    1. preprocess_audio → normalize, resample, detect silence, split into chunks
    2. dispatch_transcription → parallel chunk STT or fast-path single task
    3. dispatch_diarization → parallel chunk diarization + cross-chunk speaker reconciliation
    4. build_conversation_turns → merge words into speaker turns
    5. classify_speaker_roles → identify Salesperson vs Customer
    6. segment_conversations → split into discrete conversations
    7. stitch_conversation_audio → extract per-conversation audio files
    8. analyze_conversations → Llama 3.3 analysis
    9. score_salesperson → performance scoring

    Returns:
        Celery AsyncResult for the pipeline
    """
    processing_chain = chain(
        preprocess_audio.s(recording_id),
        dispatch_transcription.s(),
        dispatch_diarization.s(),
        build_conversation_turns_task.s(),
        classify_speaker_roles_task.s(),
        segment_conversations.s(),
        stitch_conversation_audio.s(),
        analyze_conversations.s(),
        score_salesperson.s(),
    )
    return processing_chain.apply_async()
