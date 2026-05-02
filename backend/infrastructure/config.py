"""Application configuration loaded from environment variables.

Configuration is read from a `.env` file in development and from real environment
variables in production. The `Settings` instance is constructed once at import
time; downstream modules import `settings` and read fields from it.

Phase 2 follows a configuration-first principle: every Anthropic model name,
image cap, cache TTL, and rate limit lives here so endpoints and services
never hardcode tunables. Phase 5 will override these via Fly.io secrets.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Phase 1 ---
    anthropic_api_key: str = ""
    database_url: str = "postgresql://cooksense:cooksense@localhost:5432/cooksense"
    chroma_host: str = ""
    chroma_api_key: str = ""
    chroma_persist_dir: Path = Path("./data/.chroma")
    translation_cache_dir: Path = Path("./data/translations")
    embedding_model: str = "sentence-transformers/distiluse-base-multilingual-cased-v2"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # --- Phase 2: Anthropic models (Claude 4.x family) ---
    anthropic_model_translation: str = "claude-haiku-4-5"
    anthropic_model_vision: str = "claude-sonnet-4-6"
    anthropic_model_personalization: str = "claude-haiku-4-5"
    anthropic_model_qa: str = "claude-sonnet-4-6"

    # --- Phase 2: image upload constraints ---
    image_max_size_bytes: int = 4 * 1024 * 1024
    image_min_dimension: int = 200
    image_max_dimension: int = 4096
    image_allowed_formats: str = "jpeg,png,webp"

    # --- Phase 2: QA conversation ---
    qa_max_previous_questions: int = 5

    # --- Phase 2: personalization ---
    personalize_top_n_recipes: int = 5

    # --- Phase 2: rate limits per user per day ---
    rate_limit_vision_per_day: int = 5
    rate_limit_qa_per_day: int = 10

    # --- Phase 2: LLM cache TTLs (seconds) ---
    cache_ttl_vision_seconds: int = 30 * 24 * 3600
    cache_ttl_personalization_seconds: int = 7 * 24 * 3600
    cache_ttl_qa_seconds: int = 7 * 24 * 3600

    # --- Phase 2: Anthropic call ceilings ---
    anthropic_max_tokens_vision: int = 2048
    anthropic_max_tokens_personalization: int = 512
    anthropic_max_tokens_qa: int = 1024


settings = Settings()
