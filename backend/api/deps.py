"""Dependency wiring for FastAPI routes.

This module is the single integration point with cooksense-core (the private
proprietary package) or its public stub. The try/except pattern allows the
backend to run in either mode.
"""

import logging
from functools import lru_cache

from infrastructure.db.chroma_client import get_chroma_client
from infrastructure.db.recipe_repository import RecipeRepository

logger = logging.getLogger(__name__)

try:
    from cooksense_core import (  # type: ignore[import-not-found]
        IngredientReasoner,
        RecipeRanker,
        Translator,
    )

    logger.info("cooksense-core (proprietary) loaded")
    _CORE_MODE = "proprietary"
except ImportError:
    from stub import IngredientReasoner, RecipeRanker, Translator

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
def get_recipe_repository() -> RecipeRepository:
    """Return the process-wide `RecipeRepository`.

    The repository owns a sentence-transformers model and a ChromaDB client.
    Both are expensive to construct, so we cache a single instance for the
    lifetime of the process. Tests replace this dependency via FastAPI's
    `app.dependency_overrides`.
    """
    return RecipeRepository(client=get_chroma_client())
