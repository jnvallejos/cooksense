"""Dependency wiring for FastAPI routes.

This module is the single integration point with cooksense-core (the private
proprietary package) or its public stub. The try/except pattern allows the
backend to run in either mode.

Phase 2 introduces three new factories — `get_vision_extractor`,
`get_personalized_describer`, `get_qa_responder` — that follow the same
`lru_cache(maxsize=1)` shape as `get_translator`. In stub mode each one
constructs the no-arg stub class; in proprietary mode they lazily build an
`anthropic.Anthropic` client and forward the relevant `settings.anthropic_*`
model name. `anthropic` stays an optional dependency for the stub install.
"""

import logging
from functools import lru_cache

from infrastructure.config import settings
from infrastructure.db.chroma_client import get_chroma_client
from infrastructure.db.recipe_repository import RecipeRepository

logger = logging.getLogger(__name__)

try:
    from cooksense_core import (  # type: ignore[import-not-found]
        IngredientReasoner,
        MealPlanner,
        PersonalizedDescriber,
        QAResponder,
        RecipeRanker,
        ShoppingListBuilder,
        Translator,
        VisionExtractor,
    )

    logger.info("cooksense-core (proprietary) loaded")
    _CORE_MODE = "proprietary"
except ImportError:
    from stub import (
        IngredientReasoner,
        MealPlanner,
        PersonalizedDescriber,
        QAResponder,
        RecipeRanker,
        ShoppingListBuilder,
        Translator,
        VisionExtractor,
    )

    logger.info("cooksense-core-stub (public mock) loaded")
    _CORE_MODE = "stub"


def get_core_mode() -> str:
    """Return 'proprietary' or 'stub' depending on which package is available."""
    return _CORE_MODE


def get_recipe_ranker() -> RecipeRanker:
    """Instantiate the active RecipeRanker (proprietary or stub)."""
    return RecipeRanker()


def get_ingredient_reasoner() -> IngredientReasoner:
    """Instantiate the active IngredientReasoner (proprietary or stub)."""
    return IngredientReasoner()


@lru_cache(maxsize=1)
def get_translator() -> Translator:
    """Instantiate the active Translator (proprietary or stub).

    The public stub takes no constructor args. The proprietary
    `cooksense_core.Translator` requires an `anthropic.Anthropic` client; we
    build one lazily here so `anthropic` stays an optional runtime dependency
    of the stub install. The Anthropic client reads `ANTHROPIC_API_KEY` from
    the environment and raises if it is missing — we let that error propagate
    so misconfiguration fails loudly at first use instead of producing a
    half-broken object.
    """
    if _CORE_MODE == "proprietary":
        import anthropic  # local: not required for stub installs

        logger.info("constructing proprietary Translator with Anthropic client")
        return Translator(client=anthropic.Anthropic())
    return Translator()


@lru_cache(maxsize=1)
def get_vision_extractor() -> VisionExtractor:
    """Instantiate the active VisionExtractor (proprietary or stub).

    Stub mode uses a no-arg constructor. Proprietary mode lazily builds an
    Anthropic client and forwards `settings.anthropic_model_vision`.
    """
    if _CORE_MODE == "proprietary":
        import anthropic

        logger.info(
            "constructing proprietary VisionExtractor (model=%s)",
            settings.anthropic_model_vision,
        )
        return VisionExtractor(
            client=anthropic.Anthropic(),
            model=settings.anthropic_model_vision,
        )
    return VisionExtractor()


@lru_cache(maxsize=1)
def get_personalized_describer() -> PersonalizedDescriber:
    """Instantiate the active PersonalizedDescriber (proprietary or stub)."""
    if _CORE_MODE == "proprietary":
        import anthropic

        logger.info(
            "constructing proprietary PersonalizedDescriber (model=%s)",
            settings.anthropic_model_personalization,
        )
        return PersonalizedDescriber(
            client=anthropic.Anthropic(),
            model=settings.anthropic_model_personalization,
        )
    return PersonalizedDescriber()


@lru_cache(maxsize=1)
def get_qa_responder() -> QAResponder:
    """Instantiate the active QAResponder (proprietary or stub)."""
    if _CORE_MODE == "proprietary":
        import anthropic

        logger.info(
            "constructing proprietary QAResponder (model=%s)",
            settings.anthropic_model_qa,
        )
        return QAResponder(
            client=anthropic.Anthropic(),
            model=settings.anthropic_model_qa,
        )
    return QAResponder()


@lru_cache(maxsize=1)
def get_meal_planner() -> MealPlanner:
    """Instantiate the active MealPlanner (proprietary or stub).

    Stub mode uses a no-arg constructor. Proprietary mode lazily builds an
    Anthropic client and forwards `settings.anthropic_model_planning`.
    """
    if _CORE_MODE == "proprietary":
        import anthropic

        logger.info(
            "constructing proprietary MealPlanner (model=%s)",
            settings.anthropic_model_planning,
        )
        return MealPlanner(
            client=anthropic.Anthropic(),
            model=settings.anthropic_model_planning,
        )
    return MealPlanner()


@lru_cache(maxsize=1)
def get_shopping_list_builder() -> ShoppingListBuilder:
    """Instantiate the active ShoppingListBuilder (proprietary or stub).

    The proprietary builder needs an `IngredientReasoner` for category lookup.
    The stub takes the same kwarg and ignores it.
    """
    if _CORE_MODE == "proprietary":
        import anthropic

        logger.info(
            "constructing proprietary ShoppingListBuilder (model=%s)",
            settings.anthropic_model_shopping,
        )
        return ShoppingListBuilder(
            client=anthropic.Anthropic(),
            reasoner=get_ingredient_reasoner(),
            model=settings.anthropic_model_shopping,
        )
    return ShoppingListBuilder(reasoner=get_ingredient_reasoner())


@lru_cache(maxsize=1)
def get_recipe_repository() -> RecipeRepository:
    """Return the process-wide `RecipeRepository`.

    The repository owns a sentence-transformers model and a ChromaDB client.
    Both are expensive to construct, so we cache a single instance for the
    lifetime of the process. Tests replace this dependency via FastAPI's
    `app.dependency_overrides`.
    """
    return RecipeRepository(client=get_chroma_client())
