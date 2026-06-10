"""Pipeline chain orchestration for audio processing."""
from celery import chain

from src.workers.preprocessing import preprocess_audio
from src.workers.transcription import transcribe_audio_task
from src.workers.diarization import diarize_audio
from src.workers.turn_builder import build_conversation_turns_task
from src.workers.role_classification import classify_speaker_roles_task
from src.workers.segmentation import segment_conversations
from src.workers.analysis import analyze_conversations
from src.workers.scoring import score_salesperson


def start_processing_pipeline(recording_id: str):
    """Start the full audio processing pipeline for a recording.

    Pipeline stages:
    1. preprocess_audio → normalize, resample, detect silence
    2. transcribe_audio_task → NVIDIA Parakeet STT (word-level)
    3. diarize_audio → Pyannote speaker diarization
    4. build_conversation_turns → merge words into speaker turns
    5. classify_speaker_roles → identify Salesperson vs Customer
    6. segment_conversations → split into discrete conversations
    7. analyze_conversations → Llama 3.3 analysis
    8. score_salesperson → performance scoring

    Returns:
        Celery AsyncResult for the pipeline
    """
    processing_chain = chain(
        preprocess_audio.s(recording_id),
        transcribe_audio_task.s(),
        diarize_audio.s(),
        build_conversation_turns_task.s(),
        classify_speaker_roles_task.s(),
        segment_conversations.s(),
        analyze_conversations.s(),
        score_salesperson.s(),
    )
    return processing_chain.apply_async()
