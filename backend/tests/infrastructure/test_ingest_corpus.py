"""Filtering-rule tests for the corpus ingestion CLI.

The ingestion script reads RecipeNLG CSV (or the public 30-recipe fixture) and
applies a small filter pipeline before embedding. These tests pin the rules.
"""

from __future__ import annotations

import csv
import json

from infrastructure.db import ingest_corpus


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
