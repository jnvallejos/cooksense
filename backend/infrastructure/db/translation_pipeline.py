"""Translation pipeline: orchestrates EN→ES translation with a disk cache.

Layout: `{cache_dir}/{recipe_id}.json` containing the translated fields plus a
timestamp. The pipeline checks the cache before invoking the translator and
writes back per recipe so a partial run can be resumed.

Translator implementations live elsewhere:
- `cooksense_core.Translator`: real Anthropic client, batching, JSON-schema
  enforcement (private repo).
- `stub.Translator`: identity translator for the public stub.

The pipeline only depends on the `translate_batch(recipes) -> dict` contract.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


class _TranslatorLike(Protocol):
    def translate_batch(self, recipes: list[dict]) -> dict[str, dict]: ...


_TRANSLATED_FIELDS = ("title_es", "ingredients_es", "instructions_es")


class TranslationPipeline:
    """Disk-cached EN→ES translation orchestrator."""

    def __init__(self, translator: _TranslatorLike, cache_dir: Path) -> None:
        self._translator = translator
        self._cache_dir = cache_dir

    def translate(self, recipes: list[dict]) -> dict[str, dict]:
        """Return `{recipe_id: translated_fields}` for every recipe in the input.

        Cache hits are read from disk; misses are forwarded to the translator and
        the result is written to disk. Resumable across crashes.
        """
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        results: dict[str, dict] = {}
        misses: list[dict] = []
        for recipe in recipes:
            cached = self._read_cache(recipe["id"])
            if cached is not None:
                results[recipe["id"]] = cached
            else:
                misses.append(recipe)

        if misses:
            translated = self._translator.translate_batch(misses)
            for rid, fields in translated.items():
                self._write_cache(rid, fields)
                results[rid] = {k: fields[k] for k in _TRANSLATED_FIELDS}

        return results

    def _cache_path(self, recipe_id: str) -> Path:
        return self._cache_dir / f"{recipe_id}.json"

    def _read_cache(self, recipe_id: str) -> dict | None:
        path = self._cache_path(recipe_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        return {k: payload[k] for k in _TRANSLATED_FIELDS}

    def _write_cache(self, recipe_id: str, fields: dict) -> None:
        payload = {
            "recipe_id": recipe_id,
            **{k: fields[k] for k in _TRANSLATED_FIELDS},
            "translated_at": datetime.now(UTC).isoformat(),
        }
        self._cache_path(recipe_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2))
