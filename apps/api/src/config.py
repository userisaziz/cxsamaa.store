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
    jwt_access_token_expire_minutes: int = 1440  # 24 hours for sharing
    jwt_refresh_token_expire_days: int = 30

    # Storage
    storage_backend: str = "local"  # "local" or "r2"
    local_upload_dir: str = "./uploads"

    # Cloudflare R2 (when STORAGE_BACKEND=r2)
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "samaa-audio"
    r2_public_url: str = ""  # Optional: public bucket URL for direct access

    # NVIDIA NIM
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_stt_model: str = "nvidia/parakeet-ctc-1.1b"
    nvidia_diarization_model: str = "nvidia/streusand-rnnt"
    nvidia_llm_model: str = "meta/llama-3.3-70b-instruct"
    nvidia_embedding_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
    nvidia_timeout: int = 300  # 5 minutes per API call

    # Groq STT (Whisper Large v3)
    stt_provider: str = "groq"  # "groq" or "riva"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_stt_model: str = "whisper-large-v3"
    groq_stt_language: str = ""  # Empty = auto-detect; or set e.g. "en", "hi", "ar"

    # DeepSeek LLM (V4)
    llm_provider: str = "deepseek"  # "deepseek" or "nvidia"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_llm_model: str = "deepseek-v4-flash"  # or "deepseek-v4-pro"
    deepseek_timeout: int = 120

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
    vad_filter_before_stt: bool = True  # Strip silence from chunks before sending to STT (saves 40-60% cost)
    vad_min_chunk_seconds: float = 3.0  # Skip VAD filtering for chunks shorter than this (not worth the overhead)

    # Audio Chunking for Long Recordings
    # Groq Whisper has a 25 MB file limit — keep chunks well under that.
    # 10 min of 16 kHz mono WAV ≈ 19.2 MB (safe for Groq)
    audio_chunk_duration_minutes: int = 10  # 10-minute chunks (safe for Groq 25 MB limit)
    audio_chunk_overlap_seconds: int = 30  # 30-second overlap between chunks
    max_audio_chunk_bytes: int = 25 * 1024 * 1024  # 25MB max per chunk (Groq limit)

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
    cors_origins: str = "http://localhost:3000,https://*.ngrok-free.dev"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
