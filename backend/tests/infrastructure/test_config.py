"""Tests for `Settings` defaults and env-var overrides.

Phase 2 introduces a configuration-first principle: every model name, cap,
TTL, and rate limit lives in `Settings` and is overridable via env. The tests
below pin the defaults from the spec (section 2.1) and prove pydantic-settings
loads each field from the environment.
"""

from __future__ import annotations

import pytest

from infrastructure.config import Settings


def test_settings_default_anthropic_model_translation():
    assert Settings().anthropic_model_translation == "claude-haiku-4-5"


def test_settings_default_anthropic_model_vision():
    assert Settings().anthropic_model_vision == "claude-sonnet-4-6"


def test_settings_default_anthropic_model_personalization():
    assert Settings().anthropic_model_personalization == "claude-haiku-4-5"


def test_settings_default_anthropic_model_qa():
    assert Settings().anthropic_model_qa == "claude-sonnet-4-6"


def test_settings_default_image_max_size_bytes():
    assert Settings().image_max_size_bytes == 4 * 1024 * 1024


def test_settings_default_image_min_dimension():
    assert Settings().image_min_dimension == 200


def test_settings_default_image_max_dimension():
    assert Settings().image_max_dimension == 4096


def test_settings_default_image_allowed_formats():
    assert Settings().image_allowed_formats == "jpeg,png,webp"


def test_settings_default_qa_max_previous_questions():
    assert Settings().qa_max_previous_questions == 5


def test_settings_default_personalize_top_n_recipes():
    assert Settings().personalize_top_n_recipes == 5


def test_settings_default_rate_limit_vision_per_day():
    assert Settings().rate_limit_vision_per_day == 5


def test_settings_default_rate_limit_qa_per_day():
    assert Settings().rate_limit_qa_per_day == 10


def test_settings_default_cache_ttl_vision_seconds():
    assert Settings().cache_ttl_vision_seconds == 30 * 24 * 3600


def test_settings_default_cache_ttl_personalization_seconds():
    assert Settings().cache_ttl_personalization_seconds == 7 * 24 * 3600


def test_settings_default_cache_ttl_qa_seconds():
    assert Settings().cache_ttl_qa_seconds == 7 * 24 * 3600


def test_settings_default_anthropic_max_tokens_vision():
    assert Settings().anthropic_max_tokens_vision == 2048


def test_settings_default_anthropic_max_tokens_personalization():
    assert Settings().anthropic_max_tokens_personalization == 512


def test_settings_default_anthropic_max_tokens_qa():
    assert Settings().anthropic_max_tokens_qa == 1024


# ---------------------------------------------------------------------------
# Env overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """Strip Phase 2 env vars and disable .env loading so the test pins behavior.

    pydantic-settings reads from the process env and from a `.env` file. We
    redirect the env_file to a path that does not exist so only env vars and
    explicit defaults influence the test.
    """
    for key in (
        "ANTHROPIC_MODEL_TRANSLATION",
        "ANTHROPIC_MODEL_VISION",
        "ANTHROPIC_MODEL_PERSONALIZATION",
        "ANTHROPIC_MODEL_QA",
        "IMAGE_MAX_SIZE_BYTES",
        "RATE_LIMIT_VISION_PER_DAY",
        "RATE_LIMIT_QA_PER_DAY",
        "CACHE_TTL_VISION_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


def test_settings_env_override_anthropic_model_vision(isolated_env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL_VISION", "claude-opus-4-5")
    assert Settings().anthropic_model_vision == "claude-opus-4-5"


def test_settings_env_override_rate_limit_vision_per_day(isolated_env, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_VISION_PER_DAY", "3")
    assert Settings().rate_limit_vision_per_day == 3


def test_settings_env_override_cache_ttl_vision_seconds(isolated_env, monkeypatch):
    monkeypatch.setenv("CACHE_TTL_VISION_SECONDS", "60")
    assert Settings().cache_ttl_vision_seconds == 60
