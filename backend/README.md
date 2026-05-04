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

## Endpoints

All endpoints except `/api/healthz` require an `X-User-Id` header containing a UUID v4. Clients (Android, web) generate the UUID on first launch and persist it locally — there is no auth bootstrap.

- `GET  /api/healthz` — liveness probe.
- `POST /api/profile` — upsert the profile for the current user. Returns 201 on create, 200 on update.
- `GET  /api/profile/me` — read the current user's profile, or 404 if it does not exist.
- `POST /api/recipes/search` — search recipes by ingredients. Body: `{"ingredients": [...], "limit": 5}`. Returns `RecipeSearchResponse` with ranked candidates, `total_found`, `query_id`, and a `personalized_description` on the top `personalize_top_n_recipes` results.
- `POST /api/vision/extract-ingredients` — multipart upload (`image` field). Returns the detected ingredients, the SHA-256 image hash, `from_cache`, and `remaining_calls_today`. Daily quota: `rate_limit_vision_per_day`.
- `POST /api/recipes/{recipe_id}/ask` — conversational follow-up. Body: `{"question": "...", "previous_questions": [...]}`. Server caps history to `qa_max_previous_questions`. Daily quota: `rate_limit_qa_per_day`.
- `POST /api/meal-plan/generate` — generate a 3-day meal plan (breakfast/lunch/dinner) from pantry ingredients. Body: `{"ingredients": [...], "days": 3, "meals_per_day": ["breakfast", "lunch", "dinner"]}`. Returns 201 with the persisted plan, `from_cache`, and three score floats. V1 fixes `days=3` and the canonical slot triple; other values yield 400. Cache hits short-circuit the planner and skip the daily quota. Daily quota: `rate_limit_meal_plan_per_day` (default 1).
- `POST /api/meal-plan/{plan_id}/shopping` — derive a shopping list from a persisted plan minus its pantry. 404 when the plan is missing, 403 when it belongs to a different user. No caching. Items default to bilingual identity in stub mode and to consolidated quantities in proprietary mode.

The search endpoint reads the user's profile (defaults are used if missing), queries ChromaDB for the top 20 candidates, runs them through `RecipeRanker.rank`, and personalizes the top-N via `PersonalizedDescriber`. The vision endpoint hashes uploaded images, caches results in `LLMCache` for `cache_ttl_vision_seconds`, and never persists the bytes. The ask endpoint keys the response cache by `(recipe_id, question_hash, history_hash, language)`. The meal plan endpoint keys the cache by `(sorted_canonical_ingredients, profile_signature)` and stores `{plan_id}` so cache hits resolve back to the persisted plan; the cache TTL is `cache_ttl_meal_plan_seconds`. The shopping endpoint subtracts pantry items case-insensitively (substring match) before passing the remainder to `ShoppingListBuilder.build`.

Every model name, cap, TTL, and daily limit is config-driven (`infrastructure/config.py`); endpoints never hardcode tunables. Phase 5 will override defaults via Fly.io secrets.

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
