"""Recipe search request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from api.models.recipe import Recipe


class RecipeSearchRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class RecipeSearchResponse(BaseModel):
    recipes: list[Recipe]
    total_found: int
    query_id: str
