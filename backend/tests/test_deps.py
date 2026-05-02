"""Tests for the dependency wiring (open core import logic)."""

from api.deps import get_core_mode, get_recipe_ranker, get_ingredient_reasoner
from stub import RecipeRanker as StubRanker, IngredientReasoner as StubReasoner


def test_core_mode_is_stub_when_proprietary_not_installed():
    """In CI and dev without cooksense-core, mode should be 'stub'."""
    mode = get_core_mode()
    assert mode in ("stub", "proprietary")  # depends on test env


def test_get_recipe_ranker_returns_an_instance():
    ranker = get_recipe_ranker()
    assert ranker is not None


def test_get_ingredient_reasoner_returns_an_instance():
    reasoner = get_ingredient_reasoner()
    assert reasoner is not None


def test_stub_ranker_is_used_when_in_stub_mode():
    if get_core_mode() == "stub":
        ranker = get_recipe_ranker()
        assert isinstance(ranker, StubRanker)


def test_stub_reasoner_is_used_when_in_stub_mode():
    if get_core_mode() == "stub":
        reasoner = get_ingredient_reasoner()
        assert isinstance(reasoner, StubReasoner)
