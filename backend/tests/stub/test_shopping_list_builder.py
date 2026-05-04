"""Tests for the public stub `ShoppingListBuilder`.

Identity subtraction: every input ingredient round-trips with
`estimated_quantity="some"` and `category="other"`, attribution preserved.
"""

from __future__ import annotations

from stub import ShoppingListBuilder


def test_returns_one_item_per_input_ingredient():
    items = ShoppingListBuilder().build(
        {"tomato": ["r1"], "onion": ["r2", "r3"]},
        profile={"language": "en"},
    )
    assert len(items) == 2
    names = [i["ingredient"] for i in items]
    assert set(names) == {"tomato", "onion"}


def test_uses_generic_quantity_and_category():
    items = ShoppingListBuilder().build(
        {"tomato": ["r1"]}, profile={"language": "en"}
    )
    item = items[0]
    assert item["estimated_quantity"] == "some"
    assert item["category"] == "other"


def test_identity_translation_for_es():
    items = ShoppingListBuilder().build(
        {"tomato": ["r1"]}, profile={"language": "es"}
    )
    assert items[0]["ingredient_es"] == "tomato"


def test_preserves_attribution_recipe_ids():
    items = ShoppingListBuilder().build(
        {"tomato": ["r1", "r2", "r4"]}, profile={"language": "en"}
    )
    assert items[0]["needed_for"] == ["r1", "r2", "r4"]


def test_returns_empty_list_for_empty_input():
    items = ShoppingListBuilder().build({}, profile={"language": "en"})
    assert items == []


def test_accepts_reasoner_kwarg_and_ignores_it():
    items = ShoppingListBuilder(reasoner=object()).build(
        {"x": ["r1"]}, profile={"language": "en"}
    )
    assert items[0]["ingredient"] == "x"
