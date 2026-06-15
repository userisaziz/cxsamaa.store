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
    upstash_redis_rest_url: str = ""  # Optional: Upstash REST API URL
    upstash_redis_rest_token: str = ""  # Optional: Upstash REST API token

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

    # STT Provider (NVIDIA Riva with Deepgram fallback)
    stt_provider: str = "riva"  # STT provider (default: "riva")
    stt_fallback_provider: str = "deepgram"  # Fallback STT when primary fails (default: "deepgram")

    # Deepgram STT (fallback provider)
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-3"  # Deepgram STT model (nova-3, nova-2, etc.)
    deepgram_language: str = "en"  # Language code (en, hi, ar, etc.)
    deepgram_timeout: int = 300  # 5 minutes per API call

    # DeepSeek LLM (V4) with NVIDIA fallback
    llm_provider: str = "deepseek"  # Primary LLM provider: "deepseek" or "nvidia"
    llm_fallback_provider: str = "nvidia"  # Fallback LLM when primary fails (default: "nvidia")
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
    # 10 min of 16 kHz mono WAV ≈ 19.2 MB (well under typical API limits)
    audio_chunk_duration_minutes: int = 10  # 10-minute chunks
    audio_chunk_overlap_seconds: int = 30  # 30-second overlap between chunks
    max_audio_chunk_bytes: int = 25 * 1024 * 1024  # 25MB max per chunk

    # GCP Cloud Run & Cloud Tasks
    gcp_project: str = ""  # Set to your GCP project ID
    gcp_region: str = "us-central1"  # Cloud Run region
    worker_url: str = ""  # Set to https://samaa-worker-xxxxx-uc.a.run.app
    gcp_worker_sa_email: str = ""  # Service account email for worker
    pipeline_version: str = "v1"  # Pipeline version for message tracking
    cloud_tasks_queue: str = "pipeline-queue"  # Cloud Tasks queue name
    
    # Celery (Local Development Only)
    celery_broker_url: str = "redis://localhost:6379/0"  # Redis broker for Celery
    celery_result_backend: str = "redis://localhost:6379/1"  # Redis backend for results

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

    @property
    def is_managed_redis(self) -> bool:
        """Check if using managed Redis (Upstash) vs local Docker."""
        return "upstash.io" in self.redis_url or bool(self.upstash_redis_rest_url)

    @property
    def is_managed_database(self) -> bool:
        """Check if using managed database (Neon/Supabase) vs local Docker."""
        return "neon.tech" in self.database_url or "supabase.co" in self.database_url


settings = Settings()
