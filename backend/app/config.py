"""
Application configuration.

All secrets and environment-specific values are loaded from environment
variables (via a local .env file in development). Nothing sensitive is
hard-coded so the same image/codebase can run in dev, staging, and prod.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Pharma Complaint Management System"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    # Example: postgresql+psycopg2://user:password@localhost:5432/pharma_complaints
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pharma_complaints"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Groq (LLM provider) ---
    GROQ_API_KEY: str = ""
    GROQ_PRIMARY_MODEL: str = "openai/gpt-oss-20b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-120b"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so we parse the .env file only once."""
    return Settings()
