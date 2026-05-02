"""Recipe domain models exposed via the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Recipe(BaseModel):
    id: str
    title: str
    title_es: str | None = None
    ingredients: list[str]
    ingredients_es: list[str] | None = None
    instructions: list[str]
    instructions_es: list[str] | None = None
    estimated_time_minutes: int
    estimated_skill: str = Field(pattern="^(beginner|intermediate|pro)$")
    match_percentage: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0)
    personalized_description: str | None = None
