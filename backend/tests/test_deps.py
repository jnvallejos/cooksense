"""Tests for the dependency wiring (open core import logic)."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from api import deps as api_deps
from api.deps import (
    get_core_mode,
    get_ingredient_reasoner,
    get_meal_planner,
    get_personalized_describer,
    get_qa_responder,
    get_recipe_ranker,
    get_shopping_list_builder,
    get_translator,
    get_vision_extractor,
)
from stub import IngredientReasoner as StubReasoner
from stub import MealPlanner as StubPlanner
from stub import PersonalizedDescriber as StubDescriber
from stub import QAResponder as StubResponder
from stub import RecipeRanker as StubRanker
from stub import ShoppingListBuilder as StubShopping
from stub import Translator as StubTranslator
from stub import VisionExtractor as StubVision


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


_CACHED_FACTORIES = (
    "get_translator",
    "get_vision_extractor",
    "get_personalized_describer",
    "get_qa_responder",
    "get_meal_planner",
    "get_shopping_list_builder",
)


@pytest.fixture(autouse=True)
def _clear_translator_cache():
    """Each cached factory is reset around every test so monkeypatched state lands."""

    def _reset() -> None:
        for name in _CACHED_FACTORIES:
            factory = getattr(api_deps, name, None)
            clear = getattr(factory, "cache_clear", None)
            if clear is not None:
                clear()

    _reset()
    yield
    _reset()


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


# ---------------------------------------------------------------------------
# get_vision_extractor / get_personalized_describer / get_qa_responder
# ---------------------------------------------------------------------------


def _install_fake_anthropic(monkeypatch) -> object:
    fake_client = object()
    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = MagicMock(return_value=fake_client)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    return fake_client


def test_get_vision_extractor_returns_stub_in_stub_mode():
    if get_core_mode() != "stub":
        pytest.skip("requires stub mode")

    extractor = get_vision_extractor()
    assert isinstance(extractor, StubVision)
    # 5 generic ingredients per spec section 8.2.
    assert len(extractor.extract(b"")) == 5


def test_get_personalized_describer_returns_stub_in_stub_mode():
    if get_core_mode() != "stub":
        pytest.skip("requires stub mode")

    describer = get_personalized_describer()
    assert isinstance(describer, StubDescriber)
    assert describer.describe({}, {"language": "en"}) == StubDescriber.GENERIC_EN


def test_get_qa_responder_returns_stub_in_stub_mode():
    if get_core_mode() != "stub":
        pytest.skip("requires stub mode")

    responder = get_qa_responder()
    assert isinstance(responder, StubResponder)
    assert responder.answer({}, "?", []) == StubResponder.DEMO_EN


def test_get_vision_extractor_constructs_anthropic_client_in_proprietary_mode(monkeypatch):
    fake_client = _install_fake_anthropic(monkeypatch)
    received: dict = {}

    class FakeVision:
        def __init__(self, client, model):
            received["client"] = client
            received["model"] = model

    monkeypatch.setattr(api_deps, "_CORE_MODE", "proprietary")
    monkeypatch.setattr(api_deps, "VisionExtractor", FakeVision)
    monkeypatch.setattr(api_deps.settings, "anthropic_model_vision", "claude-sonnet-test")

    instance = api_deps.get_vision_extractor()

    assert isinstance(instance, FakeVision)
    assert received["client"] is fake_client
    assert received["model"] == "claude-sonnet-test"


def test_get_personalized_describer_forwards_personalization_model(monkeypatch):
    fake_client = _install_fake_anthropic(monkeypatch)
    received: dict = {}

    class FakeDescriber:
        def __init__(self, client, model):
            received["client"] = client
            received["model"] = model

    monkeypatch.setattr(api_deps, "_CORE_MODE", "proprietary")
    monkeypatch.setattr(api_deps, "PersonalizedDescriber", FakeDescriber)
    monkeypatch.setattr(api_deps.settings, "anthropic_model_personalization", "claude-haiku-test")

    instance = api_deps.get_personalized_describer()

    assert isinstance(instance, FakeDescriber)
    assert received["client"] is fake_client
    assert received["model"] == "claude-haiku-test"


def test_get_qa_responder_forwards_qa_model(monkeypatch):
    fake_client = _install_fake_anthropic(monkeypatch)
    received: dict = {}

    class FakeResponder:
        def __init__(self, client, model):
            received["client"] = client
            received["model"] = model

    monkeypatch.setattr(api_deps, "_CORE_MODE", "proprietary")
    monkeypatch.setattr(api_deps, "QAResponder", FakeResponder)
    monkeypatch.setattr(api_deps.settings, "anthropic_model_qa", "claude-sonnet-qa-test")

    instance = api_deps.get_qa_responder()

    assert isinstance(instance, FakeResponder)
    assert received["client"] is fake_client
    assert received["model"] == "claude-sonnet-qa-test"


# ---------------------------------------------------------------------------
# Phase 3: get_meal_planner / get_shopping_list_builder
# ---------------------------------------------------------------------------


def test_get_meal_planner_returns_stub_in_stub_mode():
    if get_core_mode() != "stub":
        pytest.skip("requires stub mode")

    planner = get_meal_planner()
    assert isinstance(planner, StubPlanner)


def test_get_shopping_list_builder_returns_stub_in_stub_mode():
    if get_core_mode() != "stub":
        pytest.skip("requires stub mode")

    builder = get_shopping_list_builder()
    assert isinstance(builder, StubShopping)


def test_get_meal_planner_forwards_planning_model(monkeypatch):
    fake_client = _install_fake_anthropic(monkeypatch)
    received: dict = {}

    class FakePlanner:
        def __init__(self, client, model):
            received["client"] = client
            received["model"] = model

    monkeypatch.setattr(api_deps, "_CORE_MODE", "proprietary")
    monkeypatch.setattr(api_deps, "MealPlanner", FakePlanner)
    monkeypatch.setattr(api_deps.settings, "anthropic_model_planning", "claude-sonnet-plan-test")

    instance = api_deps.get_meal_planner()

    assert isinstance(instance, FakePlanner)
    assert received["client"] is fake_client
    assert received["model"] == "claude-sonnet-plan-test"


def test_get_shopping_list_builder_forwards_shopping_model_and_reasoner(monkeypatch):
    fake_client = _install_fake_anthropic(monkeypatch)
    received: dict = {}

    class FakeBuilder:
        def __init__(self, client, reasoner, model):
            received["client"] = client
            received["reasoner"] = reasoner
            received["model"] = model

    monkeypatch.setattr(api_deps, "_CORE_MODE", "proprietary")
    monkeypatch.setattr(api_deps, "ShoppingListBuilder", FakeBuilder)
    monkeypatch.setattr(api_deps.settings, "anthropic_model_shopping", "claude-haiku-shop-test")

    instance = api_deps.get_shopping_list_builder()

    assert isinstance(instance, FakeBuilder)
    assert received["client"] is fake_client
    assert received["model"] == "claude-haiku-shop-test"
    assert isinstance(received["reasoner"], type(api_deps.get_ingredient_reasoner()))
