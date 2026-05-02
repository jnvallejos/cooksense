"""Recipe repository backed by ChromaDB + sentence-transformers embeddings.

We compute embeddings in-process (with `sentence-transformers`) rather than
delegating to ChromaDB's built-in embedding function. This pins the model
version to `settings.embedding_model` and keeps everything mockable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chromadb
    from sentence_transformers import SentenceTransformer


class RecipeRepository:
    """Embed-and-store + nearest-neighbour query interface over ChromaDB."""

    def __init__(
        self,
        client: chromadb.api.client.ClientAPI,
        collection_name: str = "recipes",
        embedding_model: SentenceTransformer | None = None,
    ) -> None:
        raise NotImplementedError

    def add_recipes(self, recipes: list[dict]) -> None:
        """Embed and persist recipes. Recipes must carry every metadata field."""
        raise NotImplementedError

    def query_by_ingredients(self, ingredients: list[str], limit: int = 20) -> list[dict]:
        """Return up to `limit` recipes most similar to the joined ingredient query."""
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError

    def clear(self) -> None:
        """Test helper: remove all recipes from the collection."""
        raise NotImplementedError
