"""Validation tests for the `Recipe` Pydantic model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.models.recipe import Recipe


def _payload(**overrides) -> dict:
    base = {
        "id": "r1",
        "title": "Pancakes",
        "ingredients": ["flour", "milk"],
        "instructions": ["mix", "cook"],
        "estimated_time_minutes": 20,
        "estimated_skill": "beginner",
        "match_percentage": 0.5,
        "score": 0.7,
    }
    base.update(overrides)
    return base


def test_recipe_accepts_minimum_required_fields():
    recipe = Recipe(**_payload())
    assert recipe.title == "Pancakes"
    assert recipe.title_es is None


def test_recipe_accepts_full_payload_with_es_fields():
    recipe = Recipe(
        **_payload(
            title_es="Panqueques",
            ingredients_es=["harina", "leche"],
            instructions_es=["mezclar", "cocinar"],
        )
    )
    assert recipe.title_es == "Panqueques"
    assert recipe.ingredients_es == ["harina", "leche"]


def test_recipe_rejects_invalid_skill():
    with pytest.raises(ValidationError):
        Recipe(**_payload(estimated_skill="expert"))


def test_recipe_rejects_match_percentage_above_one():
    with pytest.raises(ValidationError):
        Recipe(**_payload(match_percentage=1.5))


def test_recipe_rejects_match_percentage_below_zero():
    with pytest.raises(ValidationError):
        Recipe(**_payload(match_percentage=-0.1))


def test_recipe_rejects_negative_score():
    with pytest.raises(ValidationError):
        Recipe(**_payload(score=-1.0))
