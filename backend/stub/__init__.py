"""cooksense-core-stub: public mock implementations.

This package mirrors the interface of the private `cooksense-core` package.
It is functional but limited: rankings are naive, prompts are generic, and
retrieval is basic cosine similarity.

In production, the real `cooksense-core` package is installed and overrides
this stub. See backend/api/deps.py for the import logic.
"""

from .personalized_describer import PersonalizedDescriber
from .qa_responder import QAResponder
from .ranker import RecipeRanker
from .reasoner import IngredientReasoner
from .translator import Translator
from .vision_extractor import VisionExtractor

__all__ = [
    "IngredientReasoner",
    "PersonalizedDescriber",
    "QAResponder",
    "RecipeRanker",
    "Translator",
    "VisionExtractor",
]
