"""ChromaDB client factory.

Three modes:
- Embedded persistent (dev): no `CHROMA_HOST` env, persisted to disk.
- HTTP (prod): `CHROMA_HOST` set, talks to ChromaDB Cloud over TLS with token header.
- Ephemeral (tests): explicit `get_in_memory_client()` returning an isolated in-memory store.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings

from infrastructure.config import settings


def get_chroma_client() -> chromadb.api.client.ClientAPI:
    """Return the chromadb client appropriate for the active configuration."""
    if settings.chroma_host:
        return chromadb.HttpClient(
            host=settings.chroma_host,
            ssl=True,
            headers={"X-Chroma-Token": settings.chroma_api_key},
        )

    persist_dir = settings.chroma_persist_dir
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_in_memory_client() -> chromadb.api.client.ClientAPI:
    """Return an ephemeral in-memory chromadb client. Used by tests."""
    return chromadb.EphemeralClient(settings=ChromaSettings(anonymized_telemetry=False))
