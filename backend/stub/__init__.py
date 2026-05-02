"""cooksense-core-stub: public mock implementations.

This package mirrors the interface of the private `cooksense-core` package.
It is functional but limited: rankings are naive, prompts are generic, and
retrieval is basic cosine similarity.

In production, the real `cooksense-core` package is installed and overrides
this stub. See backend/api/deps.py for the import logic.
"""

from .ranker import RecipeRanker
from .reasoner import IngredientReasoner
from .translator import Translator

__all__ = ["IngredientReasoner", "RecipeRanker", "Translator"]
