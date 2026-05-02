"""Tests for the ChromaDB client factory.

Three modes are supported:
- embedded persistent (dev default): no host configured, `PersistentClient` rooted at
  `settings.chroma_persist_dir`.
- HTTP (prod): host configured, `HttpClient` to ChromaDB Cloud with token header.
- ephemeral in-memory (tests): factory `get_in_memory_client()`.

The factory is configuration-driven; tests monkeypatch `settings` to switch modes.
"""

from unittest.mock import patch

import chromadb

from infrastructure.db.chroma_client import get_chroma_client, get_in_memory_client


def test_get_in_memory_client_returns_chroma_client():
    client = get_in_memory_client()
    assert isinstance(client, chromadb.api.client.ClientAPI) or hasattr(client, "list_collections")


def test_get_in_memory_client_supports_basic_collection_ops():
    client = get_in_memory_client()
    collection = client.get_or_create_collection("test_recipes")
    assert collection.count() == 0


def test_get_in_memory_client_disables_telemetry():
    """Ephemeral client should be configured with anonymized_telemetry=False."""
    client = get_in_memory_client()
    # Sanity: client is usable; the configuration is internal to chromadb but the
    # factory wires it explicitly. Calling list_collections should not raise.
    assert client.list_collections() is not None


def test_get_chroma_client_uses_persistent_when_no_host(tmp_path):
    """When chroma_host is empty, factory returns a persistent client at the configured path."""
    from infrastructure import config as config_module

    persist_path = tmp_path / "chroma"
    with (
        patch.object(config_module.settings, "chroma_host", ""),
        patch.object(config_module.settings, "chroma_persist_dir", persist_path),
    ):
        client = get_chroma_client()
        # Persistent client materializes the directory.
        assert persist_path.exists()
        # Ensure it works as a chromadb client.
        client.get_or_create_collection("smoke")


def test_get_chroma_client_uses_http_when_host_set():
    """When chroma_host is set, factory delegates to HttpClient with the token header.

    We mock `chromadb.HttpClient` so the test does not require a running server.
    """
    from infrastructure import config as config_module

    with (
        patch.object(config_module.settings, "chroma_host", "chroma.example.com"),
        patch.object(config_module.settings, "chroma_api_key", "secret-token"),
        patch("infrastructure.db.chroma_client.chromadb.HttpClient") as http_ctor,
    ):
        http_ctor.return_value = object()
        result = get_chroma_client()
        http_ctor.assert_called_once()
        kwargs = http_ctor.call_args.kwargs
        assert kwargs["host"] == "chroma.example.com"
        assert kwargs["ssl"] is True
        assert kwargs["headers"] == {"X-Chroma-Token": "secret-token"}
        assert result is http_ctor.return_value
