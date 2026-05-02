"""Tests for the Translator stub.

The stub returns identity translations (English content as both EN and ES) so
the ingestion pipeline can run end-to-end in CI without any real API calls.
"""

from stub import Translator


def _recipe(rid: str, title: str = "Pancakes") -> dict:
    return {
        "id": rid,
        "title": title,
        "ingredients": ["flour", "milk"],
        "instructions": ["mix", "cook"],
    }


def test_translate_batch_returns_dict_keyed_by_id():
    translator = Translator()
    result = translator.translate_batch([_recipe("r1"), _recipe("r2", title="Tacos")])
    assert set(result.keys()) == {"r1", "r2"}


def test_translate_batch_returns_identity_for_title():
    translator = Translator()
    result = translator.translate_batch([_recipe("r1", title="Pancakes")])
    assert result["r1"]["title_es"] == "Pancakes"


def test_translate_batch_returns_identity_for_ingredients():
    translator = Translator()
    result = translator.translate_batch([_recipe("r1")])
    assert result["r1"]["ingredients_es"] == ["flour", "milk"]


def test_translate_batch_returns_identity_for_instructions():
    translator = Translator()
    result = translator.translate_batch([_recipe("r1")])
    assert result["r1"]["instructions_es"] == ["mix", "cook"]


def test_translate_batch_handles_empty_input():
    translator = Translator()
    assert translator.translate_batch([]) == {}


def test_translate_batch_does_not_mutate_input():
    translator = Translator()
    recipes = [_recipe("r1")]
    snapshot = [dict(r) for r in recipes]

    translator.translate_batch(recipes)

    assert recipes == snapshot
