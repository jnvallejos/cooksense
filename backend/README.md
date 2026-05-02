# CookSense Backend

Python FastAPI backend for the CookSense recipe assistant.

## Stack

- Python 3.12+
- FastAPI 0.115+
- Pydantic v2
- SQLAlchemy 2.0 (PostgreSQL in prod, SQLite in tests)
- ChromaDB (embedded in dev, ChromaDB Cloud in prod)
- sentence-transformers (multilingual `distiluse-base-multilingual-cased-v2`)
- pytest + pytest-asyncio for tests
- ruff for linting

## Running locally

```shell
python -m venv .venv && source .venv/bin/activate
pip install -e ".[stub,dev]"
cp .env.example .env  # set ANTHROPIC_API_KEY, DATABASE_URL, CHROMA_*
uvicorn api.main:app --reload
```

The API runs on http://localhost:8000. Healthz at `/api/healthz`. OpenAPI docs at `/docs`.

## Endpoints (Phase 1)

All endpoints except `/api/healthz` require an `X-User-Id` header containing a UUID v4. Clients (Android, web) generate the UUID on first launch and persist it locally — there is no auth bootstrap.

- `GET  /api/healthz` — liveness probe.
- `POST /api/profile` — upsert the profile for the current user. Returns 201 on create, 200 on update.
- `GET  /api/profile/me` — read the current user's profile, or 404 if it does not exist.
- `POST /api/recipes/search` — search recipes by ingredients. Body: `{"ingredients": [...], "limit": 5}`. Returns `RecipeSearchResponse` with ranked candidates, `total_found`, and a `query_id`.

The search endpoint reads the user's profile (defaults are used if missing), queries ChromaDB for the top 20 candidates, and runs them through `RecipeRanker.rank` before returning the top `limit`. Stub ranker preserves order and assigns `score=1.0`; the real ranker in `cooksense-core` scores by ingredient overlap, skill match, dietary compliance, and time alignment.

## Recipe corpus ingestion

The ingestion CLI loads recipes, runs them through the EN→ES translation pipeline (with disk cache), and writes them into the configured ChromaDB collection.

```shell
# Demo / CI: 30 hand-translated recipes from the public fixture
python -m infrastructure.db.ingest_corpus --fixture

# Real corpus (requires cooksense-core for the production translator)
python -m infrastructure.db.ingest_corpus --csv path/to/recipenlg.csv --limit 5000
```

The translation cache lives at `./data/translations/{recipe_id}.json` and survives restarts. Re-running ingestion after a partial failure only retranslates missing rows.

In stub mode the Translator is identity (English → English), so the ingestion script can run end-to-end in CI without any Anthropic calls. The 5k-row corpus run is performed manually by the maintainer post-merge.

## Running tests

```shell
pytest
```

The test suite uses an in-memory SQLite database, an ephemeral ChromaDB client, and the real sentence-transformers model (cached locally after first download). No real Anthropic API calls happen — translator tests mock the SDK.

## Linting

```shell
ruff check .
ruff format .
```

## Open Core

This backend imports from either `cooksense-core` (private proprietary package) or the bundled `stub` package. See `api/deps.py` for the import pattern. Without `cooksense-core` installed, the backend falls back to the stub automatically and the API runs end-to-end with naive ranking + identity translation.
