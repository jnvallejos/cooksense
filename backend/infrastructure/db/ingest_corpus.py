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
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrastructure.db.recipe_repository import RecipeRepository


def passes_filter(row: dict) -> bool:
    """Return True when the row should be ingested.

    Rules: at least 3 ingredients, at least 3 instructions, total instruction
    text under 5000 characters, and English source. Non-English rows are
    skipped because the embedding model is multilingual but our seed corpus is
    English-first.
    """
    raise NotImplementedError


def load_recipenlg_csv(csv_path: Path, limit: int) -> list[dict]:
    """Load and filter rows from a RecipeNLG CSV. Returns at most `limit` rows."""
    raise NotImplementedError


def get_recipe_repository() -> RecipeRepository:  # pragma: no cover
    """Return a `RecipeRepository` ready to write into the configured ChromaDB.

    Imported lazily so tests can patch it without paying the embedding-model
    download cost.
    """
    raise NotImplementedError


def _default_cache_dir() -> Path:
    """Translation cache location. Tests override via patch."""
    raise NotImplementedError


def run(fixture: bool, limit: int | None, csv_path: Path | None = None) -> None:
    """Execute one ingestion run. See module docstring for modes."""
    raise NotImplementedError


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
