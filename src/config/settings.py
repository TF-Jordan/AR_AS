"""
Application settings and configuration management.
Uses pydantic-settings for environment variable loading.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AR_AS RaaS Platform"
    app_version: str = "2.0.0"
    debug: bool = False
    environment: str = "development"

    # API Settings
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # PostgreSQL Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "ar_as_db"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Qdrant Vector Database
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Embedding Model
    embedding_model_name: str = "paraphrase-multilingual-mpnet-base-v2"
    embedding_dimension: int = 768

    # Sentiment Model (Module 1)
    sentiment_model_path: str = "./models/distil-camembert-sentiment"

    # Recommendation Settings
    default_top_k: int = 10
    cache_ttl_seconds: int = 3600
    sentiment_score_tolerance: float = 0.1

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_api_key: str = "admin_secret_change_me"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
