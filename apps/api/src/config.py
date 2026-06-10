from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://samaa:samaa_dev_password@localhost:5432/samaa"
    database_url_sync: str = "postgresql://samaa:samaa_dev_password@localhost:5432/samaa"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-to-a-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Storage
    storage_backend: str = "local"
    local_upload_dir: str = "./uploads"

    # NVIDIA NIM
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_stt_model: str = "nvidia/parakeet-ctc-1.1b"
    nvidia_diarization_model: str = "nvidia/streusand-rnnt"
    nvidia_llm_model: str = "meta/llama-3.3-70b-instruct"
    nvidia_embedding_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
    nvidia_timeout: int = 300  # 5 minutes per API call

    # Pyannote.audio (Local Diarization)
    diarization_use_pyannote: bool = True  # Enable pyannote as primary diarizer
    pyannote_hf_token: str = ""  # HuggingFace token for gated pyannote models
    pyannote_model_name: str = "pyannote/speaker-diarization-3.1"
    pyannote_device: str = ""  # 'cpu', 'cuda', 'mps' (empty = auto-detect)

    # Silero VAD (Voice Activity Detection)
    vad_use_silero: bool = True  # Enable Silero VAD for speech region detection
    vad_threshold: float = 0.5  # Speech probability threshold (0.0-1.0)
    vad_min_speech_duration_ms: int = 250  # Minimum speech segment duration
    vad_min_silence_duration_ms: int = 500  # Minimum silence to mark boundary

    # Audio Chunking for Long Recordings
    audio_chunk_duration_minutes: int = 15  # Process long audio in 15-min chunks
    audio_chunk_overlap_seconds: int = 30  # 30-second overlap between chunks
    max_audio_chunk_bytes: int = 50 * 1024 * 1024  # 50MB max per chunk

    # Sortformer Diarization (Future - NVIDIA)
    diarization_use_sortformer: bool = False  # Enable when NVIDIA provides endpoint
    sortformer_endpoint: str = ""
    sortformer_model: str = "nvidia/sortformer-diarization-1.0"

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
