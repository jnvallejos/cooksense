"""Dependency wiring for FastAPI routes.

This module is the single integration point with cooksense-core (the private
proprietary package) or its public stub. The try/except pattern allows the
backend to run in either mode.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from cooksense_core import IngredientReasoner, RecipeRanker  # type: ignore[import-not-found]

    logger.info("cooksense-core (proprietary) loaded")
    _CORE_MODE = "proprietary"
except ImportError:
    from stub import IngredientReasoner, RecipeRanker

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
