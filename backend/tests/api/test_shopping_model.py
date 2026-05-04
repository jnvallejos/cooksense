"""Validation tests for the shopping list Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.models.shopping import ShoppingItem, ShoppingListResponse


def test_shopping_item_minimal_payload():
    item = ShoppingItem(
        ingredient="tomato",
        estimated_quantity="6 medium",
        category="vegetable",
        needed_for=["r1"],
    )
    assert item.ingredient == "tomato"
    assert item.ingredient_es is None
    assert item.estimated_quantity == "6 medium"
    assert item.category == "vegetable"
    assert item.needed_for == ["r1"]


def test_shopping_item_accepts_optional_translation():
    item = ShoppingItem(
        ingredient="onion",
        ingredient_es="cebolla",
        estimated_quantity="2",
        category="vegetable",
        needed_for=["r1", "r2"],
    )
    assert item.ingredient_es == "cebolla"


def test_shopping_item_requires_estimated_quantity():
    with pytest.raises(ValidationError):
        ShoppingItem(
            ingredient="x",
            category="other",
            needed_for=["r1"],
        )


def test_shopping_item_requires_category():
    with pytest.raises(ValidationError):
        ShoppingItem(
            ingredient="x",
            estimated_quantity="some",
            needed_for=["r1"],
        )


def test_shopping_list_response_round_trips():
    body = ShoppingListResponse(
        plan_id="plan-1",
        items=[
            ShoppingItem(
                ingredient="tomato",
                estimated_quantity="6",
                category="vegetable",
                needed_for=["r1"],
            )
        ],
        total_items=1,
        language="en",
    )
    dumped = body.model_dump()
    assert dumped["plan_id"] == "plan-1"
    assert dumped["items"][0]["ingredient"] == "tomato"
    assert dumped["total_items"] == 1
    assert dumped["language"] == "en"


def test_shopping_list_response_supports_empty_items():
    body = ShoppingListResponse(plan_id="p", items=[], total_items=0, language="es")
    assert body.items == []
    assert body.total_items == 0
