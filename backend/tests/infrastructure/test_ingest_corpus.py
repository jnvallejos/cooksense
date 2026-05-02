"""Tests for the corpus ingestion CLI.

The ingestion script reads RecipeNLG CSV (or the public 30-recipe fixture) and
applies a small filter pipeline before embedding. Filter-rule tests pin the
filters; the smoke test runs the fixture path end-to-end with the recipe
repository and translator mocked, asserting no real API calls happen.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from infrastructure.db import ingest_corpus

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_recipes.json"


def _row(**overrides) -> dict:
    base = {
        "id": "r1",
        "title": "Pancakes",
        "ingredients": ["flour", "milk", "eggs"],
        "directions": ["mix", "cook", "serve"],
        "language": "en",
    }
    base.update(overrides)
    return base


def test_filter_keeps_well_formed_row():
    assert ingest_corpus.passes_filter(_row()) is True


def test_filter_rejects_too_few_ingredients():
    assert ingest_corpus.passes_filter(_row(ingredients=["flour", "milk"])) is False


def test_filter_rejects_too_few_instructions():
    assert ingest_corpus.passes_filter(_row(directions=["mix", "cook"])) is False


def test_filter_rejects_anomalously_long_instructions():
    huge = ["lorem ipsum " * 500] * 3
    assert ingest_corpus.passes_filter(_row(directions=huge)) is False


def test_filter_rejects_non_english_when_language_field_present():
    assert ingest_corpus.passes_filter(_row(language="fr")) is False


def test_load_recipenlg_csv_filters_and_normalizes(tmp_path):
    csv_path = tmp_path / "recipenlg.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "ingredients", "directions", "language"])
        # Valid row.
        w.writerow(
            [
                "r1",
                "Pancakes",
                json.dumps(["flour", "milk", "eggs"]),
                json.dumps(["mix", "cook", "serve"]),
                "en",
            ]
        )
        # Too few ingredients — drop.
        w.writerow(
            [
                "r2",
                "Half-baked",
                json.dumps(["flour"]),
                json.dumps(["mix", "cook", "serve"]),
                "en",
            ]
        )
        # Too few instructions — drop.
        w.writerow(
            [
                "r3",
                "Mystery",
                json.dumps(["a", "b", "c"]),
                json.dumps(["mix"]),
                "en",
            ]
        )
        # Non-English — drop.
        w.writerow(
            [
                "r4",
                "Pâté",
                json.dumps(["a", "b", "c"]),
                json.dumps(["mix", "cook", "serve"]),
                "fr",
            ]
        )

    rows = ingest_corpus.load_recipenlg_csv(csv_path, limit=10)

    assert len(rows) == 1
    assert rows[0]["id"] == "r1"
    assert rows[0]["ingredients"] == ["flour", "milk", "eggs"]
    assert rows[0]["instructions"] == ["mix", "cook", "serve"]


def test_load_recipenlg_csv_respects_limit(tmp_path):
    csv_path = tmp_path / "recipenlg.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "ingredients", "directions", "language"])
        for i in range(5):
            w.writerow(
                [
                    f"r{i}",
                    f"Recipe {i}",
                    json.dumps(["a", "b", "c", "d"]),
                    json.dumps(["mix", "cook", "serve"]),
                    "en",
                ]
            )

    rows = ingest_corpus.load_recipenlg_csv(csv_path, limit=2)
    assert len(rows) == 2


class _IdentityTranslator:
    """In-test stand-in for the real Translator used by the smoke pipeline."""

    def translate_batch(self, recipes: list[dict]) -> dict[str, dict]:
        return {
            r["id"]: {
                "title_es": r["title"],
                "ingredients_es": list(r["ingredients"]),
                "instructions_es": list(r["instructions"]),
            }
            for r in recipes
        }


def test_run_fixture_mode_loads_recipes_into_repository(tmp_path):
    """Smoke test: --fixture mode wires the fixture through the full pipeline.

    The recipe repository is faked so no embedding model is loaded; the
    translator is patched to an identity stub and the cache dir is a tmp dir.
    No real API or model calls happen.
    """
    captured: list[list[dict]] = []

    class FakeRepo:
        def add_recipes(self, recipes: list[dict]) -> None:
            captured.append(recipes)

    cache_dir = tmp_path / "translations"

    with (
        patch.object(ingest_corpus, "get_recipe_repository", return_value=FakeRepo()),
        patch.object(ingest_corpus, "_default_cache_dir", return_value=cache_dir),
        patch.object(ingest_corpus, "_resolve_translator", return_value=_IdentityTranslator()),
    ):
        ingest_corpus.run(fixture=True, limit=None)

    assert len(captured) == 1
    enriched = captured[0]
    assert len(enriched) == 30
    # Every enriched recipe carries Spanish fields produced by the translation pipeline.
    sample = enriched[0]
    assert "title_es" in sample
    assert "ingredients_es" in sample
    assert "instructions_es" in sample
    # Translation cache wrote one file per recipe.
    cache_files = sorted(cache_dir.glob("*.json"))
    assert len(cache_files) == 30


def test_cli_help_lists_fixture_and_limit_flags():
    """The CLI accepts both `--fixture` and `--limit N` modes."""
    parser = ingest_corpus.build_parser()
    help_text = parser.format_help()

    assert "--fixture" in help_text
    assert "--limit" in help_text
    assert "--csv" in help_text


def test_cli_main_fixture_invocation(monkeypatch):
    """`python -m infrastructure.db.ingest_corpus --fixture` calls run(fixture=True)."""
    called: dict = {}

    def fake_run(fixture: bool, limit: int | None, csv_path: Path | None = None) -> None:
        called["fixture"] = fixture
        called["limit"] = limit
        called["csv_path"] = csv_path

    monkeypatch.setattr(ingest_corpus, "run", fake_run)
    ingest_corpus.main(["--fixture"])

    assert called == {"fixture": True, "limit": None, "csv_path": None}


def test_cli_main_limit_invocation(monkeypatch):
    called: dict = {}

    def fake_run(fixture: bool, limit: int | None, csv_path: Path | None = None) -> None:
        called["fixture"] = fixture
        called["limit"] = limit
        called["csv_path"] = csv_path

    monkeypatch.setattr(ingest_corpus, "run", fake_run)
    ingest_corpus.main(["--limit", "100", "--csv", "/tmp/recipenlg.csv"])

    assert called["fixture"] is False
    assert called["limit"] == 100
    assert called["csv_path"] == Path("/tmp/recipenlg.csv")


@pytest.fixture
def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text())


def test_fixture_has_thirty_recipes(fixture_payload):
    assert len(fixture_payload) == 30


def test_fixture_recipes_have_required_fields(fixture_payload):
    required = {
        "id",
        "title",
        "title_es",
        "ingredients",
        "ingredients_es",
        "instructions",
        "instructions_es",
        "estimated_time_minutes",
        "estimated_skill",
    }
    for recipe in fixture_payload:
        assert required.issubset(recipe.keys()), f"missing fields in {recipe.get('id')}"
