"""Recipe repository backed by ChromaDB + sentence-transformers embeddings.

We compute embeddings in-process (with `sentence-transformers`) rather than
delegating to ChromaDB's built-in embedding function. This pins the model
version to `settings.embedding_model` and keeps everything mockable.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from infrastructure.config import settings

if TYPE_CHECKING:
    import chromadb
    from sentence_transformers import SentenceTransformer


_LIST_FIELDS = ("ingredients", "ingredients_es", "instructions", "instructions_es")
_OPTIONAL_FIELDS = (
    "title_es",
    "ingredients_es",
    "instructions_es",
    "estimated_time_minutes",
    "estimated_skill",
)


def _load_default_model() -> SentenceTransformer:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


class RecipeRepository:
    """Embed-and-store + nearest-neighbour query interface over ChromaDB."""

    def __init__(
        self,
        client: chromadb.api.client.ClientAPI,
        collection_name: str = "recipes",
        embedding_model: SentenceTransformer | None = None,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._collection = client.get_or_create_collection(collection_name)
        self._embedding_model = embedding_model

    @property
    def model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = _load_default_model()
        return self._embedding_model

    def add_recipes(self, recipes: list[dict]) -> None:
        """Embed and persist recipes. Recipes must carry every metadata field."""
        if not recipes:
            return

        documents = [self._build_document(r) for r in recipes]
        embeddings = self.model.encode(documents, convert_to_numpy=True).tolist()
        ids = [r["id"] for r in recipes]
        metadatas = [self._build_metadata(r) for r in recipes]

        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query_by_ingredients(self, ingredients: list[str], limit: int = 20) -> list[dict]:
        """Return up to `limit` recipes most similar to the joined ingredient query."""
        if not ingredients:
            return []

        query = ", ".join(ingredients)
        embedding = self.model.encode([query], convert_to_numpy=True).tolist()
        result = self._collection.query(query_embeddings=embedding, n_results=limit)

        ids = result.get("ids", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        return [
            self._metadata_to_recipe(rid, meta) for rid, meta in zip(ids, metadatas, strict=False)
        ]

    def count(self) -> int:
        return self._collection.count()

    def get_by_id(self, recipe_id: str) -> dict | None:
        """Return a single recipe by id, or None when missing.

        Used by the conversational follow-up endpoint, which needs a recipe
        lookup that does not depend on ingredient similarity.
        """
        result = self._collection.get(ids=[recipe_id])
        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []
        if not ids:
            return None
        return self._metadata_to_recipe(ids[0], metadatas[0] if metadatas else {})

    def clear(self) -> None:
        """Test helper: remove all recipes from the collection."""
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(self._collection_name)

    @staticmethod
    def _build_document(recipe: dict) -> str:
        """Build the text we embed: title + ingredients + instructions in EN.

        ES strings are stored in metadata but not embedded separately because the
        multilingual model maps both languages into the same space.
        """
        ingredients = " ".join(recipe.get("ingredients", []))
        instructions = " ".join(recipe.get("instructions", []))
        return f"{recipe.get('title', '')}. Ingredients: {ingredients}. Steps: {instructions}"

    @staticmethod
    def _build_metadata(recipe: dict) -> dict:
        """Project a recipe into ChromaDB metadata. Lists are JSON-encoded."""
        meta: dict = {
            "title": recipe.get("title", ""),
        }
        for field in _OPTIONAL_FIELDS:
            value = recipe.get(field)
            if value is None:
                continue
            if field in _LIST_FIELDS:
                meta[field] = json.dumps(value, ensure_ascii=False)
            else:
                meta[field] = value
        # Embed-context fields:
        meta["ingredients"] = json.dumps(recipe.get("ingredients", []), ensure_ascii=False)
        meta["instructions"] = json.dumps(recipe.get("instructions", []), ensure_ascii=False)
        return meta

    @staticmethod
    def _metadata_to_recipe(rid: str, meta: dict) -> dict:
        recipe = {"id": rid}
        for key, value in meta.items():
            if key in _LIST_FIELDS and isinstance(value, str):
                try:
                    recipe[key] = json.loads(value)
                except json.JSONDecodeError:
                    recipe[key] = []
            else:
                recipe[key] = value
        return recipe
