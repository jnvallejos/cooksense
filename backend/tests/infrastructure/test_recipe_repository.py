"""Tests for `RecipeRepository` — ChromaDB + sentence-transformers wrapper.

Tests use the ephemeral chromadb client and the real multilingual embedding
model (`distiluse-base-multilingual-cased-v2`). The model is ~135MB and
downloads on first use; afterwards it is served from the HuggingFace cache.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure.db.chroma_client import get_in_memory_client
from infrastructure.db.recipe_repository import RecipeRepository

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_recipes.json"


def _seed_recipes() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture(scope="module")
def repo() -> RecipeRepository:
    """Module-scoped repository so the embedding model loads once per test session."""
    client = get_in_memory_client()
    repository = RecipeRepository(client=client, collection_name="recipes_test")
    repository.clear()
    repository.add_recipes(_seed_recipes())
    return repository


def test_add_recipes_writes_count_matches(repo):
    assert repo.count() == 30


def test_query_returns_recipes(repo):
    results = repo.query_by_ingredients(["tomato", "basil", "mozzarella"], limit=5)
    assert 1 <= len(results) <= 5
    titles = [r["title"] for r in results]
    # The Margherita pizza ingredients overlap heavily with the query.
    assert "Classic Margherita Pizza" in titles or "Caprese Salad" in titles


def test_query_returns_recipe_with_required_fields(repo):
    results = repo.query_by_ingredients(["chicken", "yogurt", "garam masala"], limit=3)
    assert results
    sample = results[0]
    for key in (
        "id",
        "title",
        "ingredients",
        "instructions",
        "estimated_time_minutes",
        "estimated_skill",
    ):
        assert key in sample, f"missing {key}"


def test_query_in_spanish_finds_matching_recipes(repo):
    """Multilingual model: Spanish ingredients land in the same vector space."""
    results = repo.query_by_ingredients(["tomate", "mozzarella", "albahaca"], limit=5)
    titles = [r["title"] for r in results]
    assert "Classic Margherita Pizza" in titles or "Caprese Salad" in titles


def test_query_respects_limit(repo):
    results = repo.query_by_ingredients(["chicken"], limit=2)
    assert len(results) == 2


def test_clear_empties_collection():
    """clear() is destructive; run on its own client to avoid leaking state."""
    client = get_in_memory_client()
    repository = RecipeRepository(client=client, collection_name="recipes_clear_test")
    repository.add_recipes(_seed_recipes()[:3])
    assert repository.count() == 3

    repository.clear()
    assert repository.count() == 0
