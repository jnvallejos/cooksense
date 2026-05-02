"""Application configuration loaded from environment variables.

Configuration is read from a `.env` file in development and from real environment
variables in production. The `Settings` instance is constructed once at import
time; downstream modules import `settings` and read fields from it.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "postgresql://cooksense:cooksense@localhost:5432/cooksense"
    chroma_host: str = ""
    chroma_api_key: str = ""
    chroma_persist_dir: Path = Path("./data/.chroma")
    translation_cache_dir: Path = Path("./data/translations")
    embedding_model: str = "sentence-transformers/distiluse-base-multilingual-cased-v2"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"


settings = Settings()
