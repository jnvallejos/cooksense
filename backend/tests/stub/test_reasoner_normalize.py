"""Tests for the IngredientReasoner stub's `normalize` extension."""

from __future__ import annotations

from stub.reasoner import IngredientReasoner


def test_normalize_returns_list_of_same_length():
    reasoner = IngredientReasoner()
    detected = [
        {"name": "tomato", "confidence": 0.9},
        {"name": "onion", "confidence": 0.8},
    ]
    result = reasoner.normalize(detected, language="en")
    assert len(result) == 2


def test_normalize_defaults_missing_category_to_other():
    reasoner = IngredientReasoner()
    result = reasoner.normalize([{"name": "tomato"}], language="en")
    assert result[0]["category"] == "other"


def test_normalize_preserves_existing_category():
    reasoner = IngredientReasoner()
    detected = [{"name": "tomato", "category": "vegetable"}]
    assert reasoner.normalize(detected, language="en")[0]["category"] == "vegetable"


def test_normalize_does_not_mutate_input():
    reasoner = IngredientReasoner()
    detected = [{"name": "tomato"}]
    snapshot = [dict(item) for item in detected]
    reasoner.normalize(detected, language="en")
    assert detected == snapshot


def test_normalize_handles_empty_input():
    reasoner = IngredientReasoner()
    assert reasoner.normalize([], language="en") == []


def test_normalize_passes_through_other_fields():
    reasoner = IngredientReasoner()
    detected = [
        {
            "name": "tomato",
            "name_es": "tomate",
            "confidence": 0.85,
            "estimated_quantity": "3 medium",
        }
    ]
    result = reasoner.normalize(detected, language="en")
    assert result[0]["name"] == "tomato"
    assert result[0]["name_es"] == "tomate"
    assert result[0]["confidence"] == 0.85
    assert result[0]["estimated_quantity"] == "3 medium"


def test_normalize_accepts_spanish_language_kwarg():
    reasoner = IngredientReasoner()
    result = reasoner.normalize([{"name": "tomato"}], language="es")
    # The stub does not language-switch, but the kwarg must be accepted.
    assert isinstance(result, list)


def test_legacy_reason_still_returns_input_unchanged():
    reasoner = IngredientReasoner()
    ingredients = ["tomato", "onion"]
    assert reasoner.reason(ingredients, profile={"diet": "vegan"}) == ingredients
