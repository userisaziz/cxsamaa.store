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
    nvidia_timeout: int = 300  # 5 minutes per API call

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
