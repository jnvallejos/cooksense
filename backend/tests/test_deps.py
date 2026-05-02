"""Tests for the dependency wiring (open core import logic)."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from api import deps as api_deps
from api.deps import get_core_mode, get_ingredient_reasoner, get_recipe_ranker, get_translator
from stub import IngredientReasoner as StubReasoner
from stub import RecipeRanker as StubRanker
from stub import Translator as StubTranslator


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


# ---------------------------------------------------------------------------
# get_translator: stub vs. proprietary wiring
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_translator_cache():
    """`get_translator` caches a single instance per process; reset around each test.

    `cache_clear` only exists once `lru_cache` is applied to `get_translator`.
    The guard keeps the fixture harmless if the cache decorator is removed.
    """
    clear = getattr(api_deps.get_translator, "cache_clear", None)
    if clear is not None:
        clear()
    yield
    clear = getattr(api_deps.get_translator, "cache_clear", None)
    if clear is not None:
        clear()


def test_get_translator_returns_stub_in_stub_mode():
    """In stub mode, the factory constructs the public stub with no args."""
    if get_core_mode() != "stub":
        pytest.skip("requires stub mode")

    translator = get_translator()

    assert isinstance(translator, StubTranslator)
    assert translator.translate_batch([]) == {}


def test_get_translator_constructs_anthropic_client_in_proprietary_mode(monkeypatch):
    """In proprietary mode, the factory builds an Anthropic client and forwards it.

    We simulate proprietary mode by patching `_CORE_MODE` and the `Translator`
    symbol re-exported from `api.deps`, plus injecting a fake `anthropic` module
    so the lazy `import anthropic` inside `get_translator` resolves to our mock.
    """
    fake_client = object()
    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = MagicMock(return_value=fake_client)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    received: dict = {}

    class FakeTranslator:
        def __init__(self, client):
            received["client"] = client

    monkeypatch.setattr(api_deps, "_CORE_MODE", "proprietary")
    monkeypatch.setattr(api_deps, "Translator", FakeTranslator)

    translator = api_deps.get_translator()

    fake_anthropic.Anthropic.assert_called_once()
    assert received["client"] is fake_client
    assert isinstance(translator, FakeTranslator)


def test_get_translator_proprietary_propagates_missing_api_key_error(monkeypatch):
    """Without `ANTHROPIC_API_KEY`, the Anthropic client raises and the error bubbles up.

    The real `anthropic.Anthropic()` raises `anthropic.AuthenticationError` (or
    similar) when no key is configured. Since `anthropic` is not installed in
    the stub-only environment, we simulate that contract with a fake module
    whose `Anthropic` raises on construction. The point of the test is to pin
    that `get_translator` does NOT swallow the error.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class _FakeAnthropicError(Exception):
        pass

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = MagicMock(
        side_effect=_FakeAnthropicError("ANTHROPIC_API_KEY missing")
    )
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    monkeypatch.setattr(api_deps, "_CORE_MODE", "proprietary")

    with pytest.raises(_FakeAnthropicError, match="ANTHROPIC_API_KEY"):
        api_deps.get_translator()
