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
    app_name: str = "Sentiment Recommendation System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # API Settings
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # PostgreSQL Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "test"
    postgres_password: str = "testPass123"
    postgres_db: str = "test_db"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
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
    qdrant_collection_vehicles: str = "vehicles"

    # Embedding Model
    embedding_model_name: str = "paraphrase-multilingual-mpnet-base-v2"
    embedding_dimension: int = 768

    # Sentiment Model (Module 1)
    sentiment_model_path: str = "./models/distil-camembert-sentiment"

    # Recommendation Settings
    default_top_k: int = 10
    similarity_weight: float = 0.6
    availability_weight: float = 0.25
    reputation_weight: float = 0.15
    cache_ttl_seconds: int = 3600
    sentiment_score_tolerance: float = 0.1

    # Rate Limiting (global defaults, overridden per-tenant in DB)
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Security (legacy, kept for backward compatibility)
    secret_key: str = "maclésecrete"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Keycloak OAuth2
    keycloak_host: str = Field(default="http://localhost:8080")
    keycloak_port: int = Field(default=8080)
    keycloak_realm: str = Field(default="raas")
    keycloak_client_id: str = Field(default="raas-api")
    keycloak_client_secret: Optional[str] = Field(default=None)

    @property
    def keycloak_url(self) -> str:
        """Full Keycloak base URL."""
        return f"{self.keycloak_host}"

    @property
    def keycloak_jwks_url(self) -> str:
        """JWKS endpoint for fetching Keycloak public signing keys."""
        return (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            "/protocol/openid-connect/certs"
        )

    @property
    def keycloak_issuer_url(self) -> str:
        """Expected issuer claim in JWT tokens."""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_token_url(self) -> str:
        """Token endpoint for obtaining access tokens."""
        return (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            "/protocol/openid-connect/token"
        )

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"



@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
