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


def get_translator() -> Translator:
    """Instantiate the active Translator (proprietary or stub)."""
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
