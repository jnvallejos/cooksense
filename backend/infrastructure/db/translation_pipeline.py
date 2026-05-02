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

from pathlib import Path
from typing import Protocol


class _TranslatorLike(Protocol):
    def translate_batch(self, recipes: list[dict]) -> dict[str, dict]: ...


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
        raise NotImplementedError
