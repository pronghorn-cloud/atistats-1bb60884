"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application Settings
    APP_NAME: str = "ATI-Stats"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ati_stats"
    DATABASE_ECHO: bool = False

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
