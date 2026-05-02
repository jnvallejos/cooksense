"""Recipe corpus ingestion CLI.

Reads recipes either from the bundled 30-recipe fixture (`--fixture`) or from a
RecipeNLG CSV (`--csv path --limit N`), runs them through filtering + the
translation pipeline (with disk cache), and writes them into the configured
ChromaDB collection.

The actual 5k-row corpus ingestion is run manually post-merge — this CLI is
exercised in CI only with the fixture.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from infrastructure.config import settings
from infrastructure.db.translation_pipeline import TranslationPipeline

if TYPE_CHECKING:
    from infrastructure.db.recipe_repository import RecipeRepository


class _TranslatorLike(Protocol):
    def translate_batch(self, recipes: list[dict]) -> dict[str, dict]: ...


logger = logging.getLogger(__name__)

MIN_INGREDIENTS = 3
MIN_INSTRUCTIONS = 3
MAX_INSTRUCTIONS_CHARS = 5000

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_PATH = _BACKEND_ROOT / "tests" / "fixtures" / "sample_recipes.json"


def passes_filter(row: dict) -> bool:
    """Return True when the row should be ingested.

    Rules: at least 3 ingredients, at least 3 instructions, total instruction
    text under 5000 characters, and English source. Non-English rows are
    skipped because the embedding model is multilingual but our seed corpus is
    English-first.
    """
    ingredients = row.get("ingredients") or []
    if len(ingredients) < MIN_INGREDIENTS:
        return False

    directions = row.get("directions") or row.get("instructions") or []
    if len(directions) < MIN_INSTRUCTIONS:
        return False

    if sum(len(step) for step in directions) >= MAX_INSTRUCTIONS_CHARS:
        return False

    language = row.get("language")
    if language and language != "en":
        return False

    return True


def load_recipenlg_csv(csv_path: Path, limit: int) -> list[dict]:
    """Load and filter rows from a RecipeNLG CSV. Returns at most `limit` rows."""
    rows: list[dict] = []
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = _parse_csv_row(raw)
            if passes_filter(row):
                rows.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "ingredients": row["ingredients"],
                        "instructions": row.get("directions") or row.get("instructions") or [],
                    }
                )
                if len(rows) >= limit:
                    break
    return rows


def _parse_csv_row(raw: dict) -> dict:
    """Normalize CSV fields, parsing JSON-encoded list columns."""
    parsed: dict = dict(raw)
    for key in ("ingredients", "directions", "instructions"):
        if key in parsed and isinstance(parsed[key], str):
            try:
                parsed[key] = json.loads(parsed[key])
            except json.JSONDecodeError:
                parsed[key] = []
    return parsed


def get_recipe_repository() -> RecipeRepository:  # pragma: no cover
    """Return a `RecipeRepository` ready to write into the configured ChromaDB.

    Imported lazily so tests can patch it without paying the embedding-model
    download cost.
    """
    from infrastructure.db.chroma_client import get_chroma_client
    from infrastructure.db.recipe_repository import RecipeRepository

    return RecipeRepository(client=get_chroma_client())


def _default_cache_dir() -> Path:
    return settings.translation_cache_dir


def _resolve_translator() -> _TranslatorLike:  # pragma: no cover - thin lazy-import helper
    """Resolve the active Translator from `api.deps`.

    Imported lazily so this module stays importable before the deps wiring
    is in place; tests monkeypatch this function directly.
    """
    from api.deps import get_translator

    return get_translator()


def run(fixture: bool, limit: int | None, csv_path: Path | None = None) -> None:
    """Execute one ingestion run. See module docstring for modes."""
    if fixture:
        rows = _load_fixture()
    else:
        if csv_path is None:
            raise ValueError("--csv is required unless --fixture is set")
        rows = load_recipenlg_csv(csv_path, limit=limit or 5000)

    logger.info("ingestion: loaded %d recipes", len(rows))

    translator = _resolve_translator()
    cache_dir = _default_cache_dir()
    pipeline = TranslationPipeline(translator=translator, cache_dir=cache_dir)
    translations = pipeline.translate(rows)

    enriched = [
        {
            **row,
            "title_es": translations[row["id"]]["title_es"],
            "ingredients_es": translations[row["id"]]["ingredients_es"],
            "instructions_es": translations[row["id"]]["instructions_es"],
        }
        for row in rows
    ]

    repo = get_recipe_repository()
    repo.add_recipes(enriched)
    logger.info("ingestion: wrote %d recipes to ChromaDB", len(enriched))


def _load_fixture() -> list[dict]:
    """Load the bundled 30-recipe fixture, returning EN-only fields."""
    payload = json.loads(FIXTURE_PATH.read_text())
    rows: list[dict] = []
    for recipe in payload:
        rows.append(
            {
                "id": recipe["id"],
                "title": recipe["title"],
                "ingredients": recipe["ingredients"],
                "instructions": recipe["instructions"],
                "estimated_time_minutes": recipe["estimated_time_minutes"],
                "estimated_skill": recipe["estimated_skill"],
            }
        )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest recipes into ChromaDB. Use --fixture for the bundled "
            "30-recipe sample, or --csv plus --limit for the RecipeNLG corpus."
        )
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Ingest the bundled 30-recipe public fixture (used in CI and demos).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of CSV rows to ingest after filtering.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to a RecipeNLG CSV file (ignored when --fixture is set).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    run(fixture=args.fixture, limit=args.limit, csv_path=args.csv)


if __name__ == "__main__":  # pragma: no cover
    main()
