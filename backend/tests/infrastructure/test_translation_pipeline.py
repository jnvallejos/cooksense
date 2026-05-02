"""Tests for `TranslationPipeline` — disk-cached EN→ES translation orchestrator.

The pipeline wraps a `Translator` (real or stub) and a disk cache. On miss it
calls the translator and persists the result; on hit it reads from disk and
skips the translator entirely. This keeps ingestion resumable and free of
duplicate API calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure.db.translation_pipeline import TranslationPipeline


class _RecordingTranslator:
    """Test double that counts how many times `translate_batch` was called."""

    def __init__(self) -> None:
        self.calls: list[list[dict]] = []

    def translate_batch(self, recipes: list[dict]) -> dict[str, dict]:
        self.calls.append(recipes)
        return {
            r["id"]: {
                "title_es": f"ES:{r['title']}",
                "ingredients_es": [f"ES:{i}" for i in r["ingredients"]],
                "instructions_es": [f"ES:{step}" for step in r["instructions"]],
            }
            for r in recipes
        }


def _recipe(rid: str, title: str = "Pancakes") -> dict:
    return {
        "id": rid,
        "title": title,
        "ingredients": ["flour", "milk"],
        "instructions": ["mix", "cook"],
    }


@pytest.fixture
def cache_dir(tmp_path) -> Path:
    return tmp_path / "translations"


def test_miss_calls_translator_and_writes_cache(cache_dir):
    translator = _RecordingTranslator()
    pipeline = TranslationPipeline(translator=translator, cache_dir=cache_dir)

    result = pipeline.translate([_recipe("r1")])

    assert "r1" in result
    assert result["r1"]["title_es"] == "ES:Pancakes"
    assert len(translator.calls) == 1

    cache_file = cache_dir / "r1.json"
    assert cache_file.exists()
    payload = json.loads(cache_file.read_text())
    assert payload["recipe_id"] == "r1"
    assert payload["title_es"] == "ES:Pancakes"
    assert payload["ingredients_es"] == ["ES:flour", "ES:milk"]
    assert payload["instructions_es"] == ["ES:mix", "ES:cook"]
    assert "translated_at" in payload


def test_hit_skips_translator(cache_dir):
    translator = _RecordingTranslator()
    pipeline = TranslationPipeline(translator=translator, cache_dir=cache_dir)
    pipeline.translate([_recipe("r1")])
    translator.calls.clear()

    second = pipeline.translate([_recipe("r1")])

    assert second["r1"]["title_es"] == "ES:Pancakes"
    assert translator.calls == []  # cache hit, translator not invoked


def test_partial_hit_only_translates_missing(cache_dir):
    translator = _RecordingTranslator()
    pipeline = TranslationPipeline(translator=translator, cache_dir=cache_dir)
    pipeline.translate([_recipe("r1", title="Cached")])
    translator.calls.clear()

    result = pipeline.translate([_recipe("r1", title="Cached"), _recipe("r2", title="Fresh")])

    # r1 served from cache, r2 went through the translator.
    assert result["r1"]["title_es"] == "ES:Cached"
    assert result["r2"]["title_es"] == "ES:Fresh"
    assert len(translator.calls) == 1
    assert {r["id"] for r in translator.calls[0]} == {"r2"}


def test_resumable_after_partial_failure(cache_dir):
    """Simulate ingestion that crashed mid-batch: only some cache files were written.

    On resume, the pipeline re-runs the translator only for missing recipe ids.
    """
    translator = _RecordingTranslator()
    pipeline = TranslationPipeline(translator=translator, cache_dir=cache_dir)
    pipeline.translate([_recipe("r1"), _recipe("r2")])

    # Wipe r2's cache to simulate a partial failure.
    (cache_dir / "r2.json").unlink()
    translator.calls.clear()

    result = pipeline.translate([_recipe("r1"), _recipe("r2")])

    assert result["r1"]["title_es"] == "ES:Pancakes"
    assert result["r2"]["title_es"] == "ES:Pancakes"
    # Only r2 had to be retranslated.
    assert len(translator.calls) == 1
    assert {r["id"] for r in translator.calls[0]} == {"r2"}


def test_creates_cache_directory_if_missing(tmp_path):
    nested = tmp_path / "deep" / "translations"
    translator = _RecordingTranslator()
    pipeline = TranslationPipeline(translator=translator, cache_dir=nested)

    pipeline.translate([_recipe("r1")])

    assert nested.exists()
    assert (nested / "r1.json").exists()
