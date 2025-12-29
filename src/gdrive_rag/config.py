"""Configuration management for gdrive-rag."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gdrive_rag"

    google_service_account_file: str | None = None
    google_delegated_user: str | None = None

    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    chunk_target_size: int = 600
    chunk_overlap: int = 100
    embedding_batch_size: int = 100

    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_key: str | None = None

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8002
    mcp_auth_token: str | None = None

    log_level: str = "INFO"
    environment: str = "development"


settings = Settings()
