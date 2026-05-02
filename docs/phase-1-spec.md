# Phase 1 Spec — Backend Foundation (RAG + Profiles)

**Repo:** `cooksense` (public) + `cooksense-core` (private)
**Domain:** Recipe assistant
**Stack:** Python 3.12, FastAPI, ChromaDB, PostgreSQL, SQLAlchemy, pytest, ruff
**Approach:** Test-Driven Development, granular commits, feature branch + PR
**Branch:** `phase-1-rag-foundation`

---

## 1. Goal of Phase 1

Build the backend foundation: ingest the recipe corpus, embed it, persist it in ChromaDB, expose a search endpoint, and add user profile CRUD. No vision yet, no LLM personalization yet. Just the data layer + retrieval + profile management.

At the end of Phase 1:
- RecipeNLG top 50k recipes ingested, translated to Spanish, embedded, persisted in ChromaDB
- `POST /api/recipes/search` returns recipes by ingredients + profile filters (raw, no LLM)
- `POST /api/profile`, `GET /api/profile/{user_id}` for anonymous user profile management
- PostgreSQL schema for profiles
- Real `cooksense-core.RecipeRanker` ranks by ingredient overlap + profile filters
- Stub `RecipeRanker` returns recipes in input order
- Recipe pydantic models defined
- Full integration tests with embedded ChromaDB and SQLite (test) / Postgres (prod)
- All Phase 0 code unchanged

---

## 2. Solution & Folder Structure

```
cooksense/
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── healthz.py                        (unchanged)
│   │   │   ├── recipes.py                        (NEW)
│   │   │   └── profile.py                        (NEW)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── recipe.py                         (NEW)
│   │   │   ├── profile.py                        (NEW)
│   │   │   └── search.py                         (NEW)
│   │   ├── deps.py                               (extended)
│   │   └── main.py                               (extended)
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── chroma_client.py                  (NEW)
│   │   │   ├── ingest_corpus.py                  (NEW)
│   │   │   └── translation_pipeline.py           (NEW)
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── postgres.py                       (NEW)
│   │   │   ├── models.py                         (NEW, SQLAlchemy)
│   │   │   └── profile_repository.py             (NEW)
│   │   └── config.py                             (NEW)
│   ├── stub/
│   │   ├── ranker.py                             (extended)
│   │   └── reasoner.py                           (unchanged)
│   ├── tests/
│   │   ├── conftest.py                           (extended)
│   │   ├── test_healthz.py                       (unchanged)
│   │   ├── test_stub.py                          (extended)
│   │   ├── test_deps.py                          (unchanged)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── test_recipes_search.py            (NEW)
│   │   │   └── test_profile.py                   (NEW)
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── test_chroma_client.py             (NEW)
│   │   │   ├── test_ingest_corpus.py             (NEW)
│   │   │   ├── test_translation.py               (NEW)
│   │   │   └── test_profile_repository.py        (NEW)
│   │   └── fixtures/
│   │       └── sample_recipes.json               (NEW, ~30 recipes for tests)
│   └── pyproject.toml                            (extended deps)
└── (cooksense-core private repo — see section 7)
```

---

## 3. Recipe Corpus Ingestion

### 3.1 Corpus source

**RecipeNLG** is a recipe dataset by AGH UST. License permits research/non-commercial use. Available at https://recipenlg.cs.put.poznan.pl/ as a CSV (~5GB uncompressed, 2.2M recipes).

For Phase 1, we ingest **top 50k recipes** filtered by:
- Has at least 3 ingredients
- Has at least 3 instructions
- Total instruction text < 5000 chars (filters anomalies)
- English only as source

This subset fits in <500MB on disk after embedding, has rich enough variety, and keeps ingestion under 15 minutes on a developer machine.

### 3.2 Translation pipeline

Recipes are translated to Spanish during ingestion using Claude (batch mode for cost efficiency).

**`infrastructure/db/translation_pipeline.py`:**

```python
"""Recipe translation pipeline.

Translates recipe titles, ingredients, and instructions from English to Spanish
using Anthropic Claude in batch mode. Caches translations to disk to allow
resumable ingestion.
"""

import json
import logging
from pathlib import Path

import anthropic
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TranslatedRecipe(BaseModel):
    title_es: str
    ingredients_es: list[str]
    instructions_es: list[str]


class RecipeTranslator:
    """Translates recipes via Anthropic Claude.

    Strategy: batch in groups of 20 recipes per API call. Single prompt asks
    Claude to return a JSON array of translations. Persists translations to
    disk cache (.json files keyed by recipe_id) so re-runs skip done work.
    """

    def __init__(
        self,
        client: anthropic.Anthropic,
        cache_dir: Path,
        model: str = "claude-3-5-haiku-latest",
    ) -> None:
        self._client = client
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._model = model

    def translate_batch(
        self, recipes: list[dict], batch_size: int = 20
    ) -> dict[str, TranslatedRecipe]:
        """Return translations keyed by recipe_id.

        Skips recipes already in cache. Translates the rest in batches.
        """
        results: dict[str, TranslatedRecipe] = {}

        # Load cache hits
        to_translate: list[dict] = []
        for recipe in recipes:
            cache_path = self._cache_dir / f"{recipe['id']}.json"
            if cache_path.exists():
                with cache_path.open() as f:
                    data = json.load(f)
                results[recipe["id"]] = TranslatedRecipe(**data)
            else:
                to_translate.append(recipe)

        # Batch translate the rest
        for i in range(0, len(to_translate), batch_size):
            batch = to_translate[i : i + batch_size]
            translations = self._translate_one_batch(batch)
            for recipe_id, translated in translations.items():
                results[recipe_id] = translated
                cache_path = self._cache_dir / f"{recipe_id}.json"
                with cache_path.open("w") as f:
                    json.dump(translated.model_dump(), f, ensure_ascii=False)

        return results

    def _translate_one_batch(
        self, recipes: list[dict]
    ) -> dict[str, TranslatedRecipe]:
        """Send one batch to Claude. Returns recipe_id -> TranslatedRecipe."""
        # Real implementation in Phase 1
        # This is a contract definition; actual prompt and parsing live in
        # cooksense-core for proprietary tuning. The stub returns identity
        # translations (no actual translation).
        raise NotImplementedError("Implemented in cooksense-core")
```

### 3.3 Ingestion script

**`infrastructure/db/ingest_corpus.py`:**

```python
"""Ingest RecipeNLG corpus into ChromaDB.

Workflow:
1. Read RecipeNLG CSV
2. Filter to top 50k by criteria
3. For each recipe: translate to Spanish (batched, cached)
4. Embed both English and Spanish versions (separate collections)
5. Persist in ChromaDB

Usage:
    python -m infrastructure.db.ingest_corpus --csv path/to/recipenlg.csv \\
        --top 50000 --collection-en recipes_en --collection-es recipes_es

Resumable: if interrupted, re-run skips translated recipes already cached.
"""

import argparse
import logging
from pathlib import Path

import chromadb
import pandas as pd

from infrastructure.db.chroma_client import get_chroma_client
from infrastructure.db.translation_pipeline import RecipeTranslator

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest recipe corpus")
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--top", type=int, default=50000)
    parser.add_argument("--collection-en", default="recipes_en")
    parser.add_argument("--collection-es", default="recipes_es")
    parser.add_argument("--cache-dir", type=Path, default=Path("./data/translations"))
    return parser.parse_args()


def filter_recipes(df: pd.DataFrame, top: int) -> pd.DataFrame:
    """Filter to top N recipes meeting quality criteria."""
    df = df[df["ingredients"].str.len() > 50]  # Min 3 ingredients ~50 chars
    df = df[df["directions"].str.len() > 100]  # Min 3 instructions
    df = df[df["directions"].str.len() < 5000]  # Filter anomalies
    return df.head(top)


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.csv)
    df = filter_recipes(df, args.top)
    logger.info("Ingesting %d recipes", len(df))

    client = get_chroma_client()
    coll_en = client.get_or_create_collection(args.collection_en)
    coll_es = client.get_or_create_collection(args.collection_es)

    # Translation phase
    # ... (rest of implementation)
    raise NotImplementedError("Full implementation in code, not spec")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

The above is a sketch — actual file is more complete in code.

### 3.4 Decisions

- **Two ChromaDB collections (`recipes_en`, `recipes_es`)** — one per language. Profile language drives which collection is queried. Avoids language-mixing in search results.
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` for English, `sentence-transformers/distiluse-base-multilingual-cased-v2` for Spanish. Both run locally, no API cost, good quality for recipe domain.
- **Translation cache on disk:** ingestion is resumable. Disk cache (`./data/translations/{recipe_id}.json`) survives restarts. Critical for a 50k corpus where translations cost ~USD 30-50 in Claude tokens.
- **Translation logic in `cooksense-core`:** the stub returns identity (English text). Real translation happens via Claude in the proprietary core.
- **Pre-translated, not on-the-fly:** no per-request translation latency. Recipe corpus is static.

---

## 4. ChromaDB integration

### 4.1 `infrastructure/db/chroma_client.py`

```python
"""ChromaDB client factory.

In dev, uses an embedded ChromaDB persisting to disk.
In prod, connects to ChromaDB Cloud via host + API key from env.
Test doubles use ephemeral in-memory ChromaDB.
"""

import chromadb
from chromadb.config import Settings

from infrastructure.config import settings


def get_chroma_client() -> chromadb.ClientAPI:
    if settings.chroma_host:
        return chromadb.HttpClient(
            host=settings.chroma_host,
            ssl=True,
            headers={"X-Chroma-Token": settings.chroma_api_key},
        )
    # Embedded mode for dev
    return chromadb.PersistentClient(
        path=str(settings.chroma_persist_dir),
        settings=Settings(anonymized_telemetry=False),
    )


def get_in_memory_client() -> chromadb.ClientAPI:
    """Ephemeral client for tests."""
    return chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
```

### 4.2 Decisions

- **Embedded for dev, HTTP for prod, ephemeral for tests.** Three modes, one factory.
- **Persistent path configurable via env** (`./data/.chroma` default).
- **No `chromadb-server` required for dev.** Embedded mode is fine. Prod uses ChromaDB Cloud free tier.

---

## 5. PostgreSQL profile storage

### 5.1 Schema (SQLAlchemy)

**`infrastructure/storage/models.py`:**

```python
"""SQLAlchemy models for profiles and history."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cooking_for: Mapped[str] = mapped_column(String(50))  # "self", "couple", "family"
    household_size: Mapped[int] = mapped_column()
    dietary_restrictions: Mapped[list[str]] = mapped_column(JSON, default=list)
    fitness_goal: Mapped[str] = mapped_column(String(50))  # "none", "lose", "build", "eat_better"
    cooking_skill: Mapped[str] = mapped_column(String(50))  # "beginner", "intermediate", "pro"
    time_budget_minutes: Mapped[int] = mapped_column()  # 15, 30, 45, 60
    language: Mapped[str] = mapped_column(String(2), default="en")  # "en" or "es"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

### 5.2 `infrastructure/storage/profile_repository.py`

```python
"""Profile repository with full CRUD."""

from sqlalchemy.orm import Session

from infrastructure.storage.models import UserProfile


class ProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_user_id(self, user_id: str) -> UserProfile | None:
        return self._session.query(UserProfile).filter_by(user_id=user_id).first()

    def upsert(self, profile: UserProfile) -> UserProfile:
        existing = self.get_by_user_id(profile.user_id)
        if existing:
            for field in (
                "cooking_for",
                "household_size",
                "dietary_restrictions",
                "fitness_goal",
                "cooking_skill",
                "time_budget_minutes",
                "language",
            ):
                setattr(existing, field, getattr(profile, field))
            self._session.commit()
            return existing
        self._session.add(profile)
        self._session.commit()
        return profile

    def delete(self, user_id: str) -> bool:
        profile = self.get_by_user_id(user_id)
        if profile is None:
            return False
        self._session.delete(profile)
        self._session.commit()
        return True
```

### 5.3 Decisions

- **Anonymous user_id is a UUID4 string (36 chars).** Client generates and persists it locally. Backend just stores the profile keyed by it.
- **No password, no email, no auth.** Anyone with the user_id can read/write that profile. Acceptable for V1; auth in V2.
- **JSON for dietary_restrictions:** SQLite supports JSON natively in tests; Postgres has `JSONB`. SQLAlchemy `JSON` type abstracts both.
- **Repository pattern:** mockable in tests, swappable for in-memory in unit tests.

---

## 6. API endpoints

### 6.1 `POST /api/recipes/search`

**Request:**
```json
{
  "ingredients": ["tomato", "basil", "pasta"],
  "limit": 5,
  "filters": {
    "max_time_minutes": 30
  }
}
```

`X-User-Id` header required (any UUID format string). Profile is loaded server-side.

**Response (200):**
```json
{
  "recipes": [
    {
      "id": "r123",
      "title": "Pasta with Tomato and Basil",
      "title_es": "Pasta con tomate y albahaca",
      "ingredients": ["tomato", "basil", "pasta", "olive oil"],
      "ingredients_es": ["tomate", "albahaca", "pasta", "aceite de oliva"],
      "instructions": ["...", "..."],
      "instructions_es": ["...", "..."],
      "estimated_time_minutes": 25,
      "match_percentage": 0.85,
      "score": 0.92
    }
  ],
  "total_found": 5,
  "query_id": "uuid-of-this-search"
}
```

**Errors:**
- 400 `Profile.NotFound`: user_id has no profile (must POST profile first)
- 400 `Validation.IngredientsEmpty`: ingredients array is empty
- 503 `Search.Failed`: ChromaDB unreachable or core ranker exception

### 6.2 `POST /api/profile`

**Request:**
```json
{
  "cooking_for": "family",
  "household_size": 4,
  "dietary_restrictions": ["vegetarian"],
  "fitness_goal": "eat_better",
  "cooking_skill": "intermediate",
  "time_budget_minutes": 30,
  "language": "es"
}
```

`X-User-Id` header required.

**Response (200 or 201):**
- 201 if newly created
- 200 if updated

```json
{
  "user_id": "uuid",
  "cooking_for": "family",
  "household_size": 4,
  "dietary_restrictions": ["vegetarian"],
  "fitness_goal": "eat_better",
  "cooking_skill": "intermediate",
  "time_budget_minutes": 30,
  "language": "es",
  "created_at": "2026-05-02T14:30:00Z",
  "updated_at": "2026-05-02T14:30:00Z"
}
```

**Errors:**
- 400 `Validation.*` for invalid field values

### 6.3 `GET /api/profile/{user_id}`

**Response (200):** same shape as POST response.
**Response (404):** `Profile.NotFound`

### 6.4 Pydantic models

**`api/models/recipe.py`:**

```python
"""Recipe domain models exposed via API."""

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
    match_percentage: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0)


class RecipeSearchRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    filters: dict = Field(default_factory=dict)


class RecipeSearchResponse(BaseModel):
    recipes: list[Recipe]
    total_found: int
    query_id: str
```

**`api/models/profile.py`:**

```python
"""User profile model."""

from datetime import datetime
from pydantic import BaseModel, Field


class ProfileRequest(BaseModel):
    cooking_for: str = Field(pattern="^(self|couple|family)$")
    household_size: int = Field(ge=1, le=20)
    dietary_restrictions: list[str] = Field(default_factory=list)
    fitness_goal: str = Field(pattern="^(none|lose|build|eat_better)$")
    cooking_skill: str = Field(pattern="^(beginner|intermediate|pro)$")
    time_budget_minutes: int = Field(ge=15, le=180)
    language: str = Field(pattern="^(en|es)$", default="en")


class ProfileResponse(BaseModel):
    user_id: str
    cooking_for: str
    household_size: int
    dietary_restrictions: list[str]
    fitness_goal: str
    cooking_skill: str
    time_budget_minutes: int
    language: str
    created_at: datetime
    updated_at: datetime
```

---

## 7. Private repo: `cooksense-core` Phase 1

### 7.1 What goes here

The proprietary ranking algorithm. The stub returns recipes unchanged; the real ranker scores by:

```python
# In cooksense-core/cooksense_core/ranker.py
class RecipeRanker:
    """Multi-factor recipe scoring."""

    def __init__(self) -> None:
        # Weights are proprietary, tuned empirically
        pass

    def rank(self, recipes: list[dict], profile: dict) -> list[dict]:
        """Score and re-rank recipes.

        Score = w1 * ingredient_overlap_pct
              + w2 * time_alignment_score
              + w3 * skill_match_score
              + w4 * dietary_compliance_score
              - w5 * macro_distance_penalty

        Returns recipes sorted by descending score, with score field added.
        """
        # Real implementation
        ...
```

The stub in the public repo returns recipes in order with score=1.0 for all.

### 7.2 Tests in private repo

```python
# In cooksense-core/tests/test_ranker.py
def test_ranks_more_overlapping_ingredients_higher():
    ranker = RecipeRanker()
    recipes = [
        {"id": "r1", "ingredients": ["a", "b"]},
        {"id": "r2", "ingredients": ["a", "b", "c"]},
    ]
    profile = {"language": "en"}

    ranked = ranker.rank(recipes, profile, query_ingredients=["a", "b", "c"])

    assert ranked[0]["id"] == "r2"  # 100% overlap
    assert ranked[1]["id"] == "r1"  # 67% overlap


def test_penalizes_skill_mismatch():
    ranker = RecipeRanker()
    recipes = [
        {"id": "easy", "estimated_skill": "beginner"},
        {"id": "hard", "estimated_skill": "pro"},
    ]
    profile = {"cooking_skill": "beginner", "language": "en"}

    ranked = ranker.rank(recipes, profile, query_ingredients=[])

    assert ranked[0]["id"] == "easy"  # Skill matches
```

---

## 8. Test Strategy — Phase 1

Phase 1 has three test categories:
- **Unit tests** (mock-based): API route handlers with mocked deps, profile repository with in-memory session
- **Integration tests** (real DB): ChromaDB ephemeral + SQLite in-memory for full integration
- **Smoke tests for stub**

### 8.1 `tests/conftest.py` (extended)

```python
"""Shared fixtures for Phase 1 tests."""

import pytest
from chromadb.api import ClientAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.main import create_app
from infrastructure.db.chroma_client import get_in_memory_client
from infrastructure.storage.models import Base


@pytest.fixture
def chroma_client() -> ClientAPI:
    """Ephemeral ChromaDB client per test."""
    return get_in_memory_client()


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(sqlite_engine) -> Session:
    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_recipes_collection(chroma_client):
    """Ingest 30 sample recipes for tests."""
    coll = chroma_client.create_collection("recipes_en")
    # Load from tests/fixtures/sample_recipes.json
    # ... (real impl loads and embeds)
    return coll


@pytest.fixture
def app(chroma_client, session):
    """App with test fixtures wired."""
    return create_app(chroma_client=chroma_client, db_session=session)


@pytest.fixture
def client(app):
    return TestClient(app)
```

### 8.2 Tests by file

**`tests/api/test_profile.py`:**

```
test_post_profile_creates_returns_201
test_post_profile_updates_returns_200
test_post_profile_with_invalid_cooking_for_returns_400
test_post_profile_with_invalid_household_size_returns_400
test_post_profile_with_invalid_fitness_goal_returns_400
test_post_profile_with_invalid_skill_returns_400
test_post_profile_with_time_budget_below_15_returns_400
test_post_profile_with_invalid_language_returns_400
test_get_profile_existing_returns_200_with_full_data
test_get_profile_missing_returns_404
test_post_profile_persists_to_database
test_get_profile_round_trip_returns_same_data
```

**`tests/api/test_recipes_search.py`:**

```
test_search_with_existing_profile_returns_200
test_search_without_profile_returns_400_profile_not_found
test_search_with_empty_ingredients_returns_400
test_search_returns_recipes_in_response_array
test_search_returns_total_found
test_search_returns_query_id
test_search_with_limit_5_returns_at_most_5_recipes
test_search_with_limit_default_returns_at_most_5_recipes
test_search_with_max_time_filter_excludes_long_recipes
test_search_returns_match_percentage_per_recipe
test_search_returns_score_per_recipe
test_search_with_spanish_profile_returns_spanish_titles
test_search_with_english_profile_returns_english_titles
test_search_when_chromadb_unreachable_returns_503
```

**`tests/infrastructure/test_chroma_client.py`:**

```
test_in_memory_client_creates_collection
test_in_memory_client_persists_documents
test_in_memory_client_queries_by_ingredients
test_persistent_client_loads_from_disk
test_http_client_initialized_with_correct_settings
```

**`tests/infrastructure/test_ingest_corpus.py`:**

```
test_filter_recipes_excludes_short_ingredients
test_filter_recipes_excludes_short_directions
test_filter_recipes_excludes_anomalously_long_directions
test_filter_recipes_returns_top_n
test_ingest_writes_recipes_to_collection
test_ingest_includes_translated_versions
test_ingest_skips_already_ingested_recipes
test_ingest_handles_csv_with_missing_columns
```

**`tests/infrastructure/test_translation.py`:**

```
test_translator_caches_translations_to_disk
test_translator_skips_recipes_already_in_cache
test_translator_batches_uncached_recipes
test_translator_returns_translated_recipe_keyed_by_id
test_translator_handles_empty_input
```

**`tests/infrastructure/test_profile_repository.py`:**

```
test_get_by_user_id_returns_profile_when_exists
test_get_by_user_id_returns_none_when_missing
test_upsert_creates_new_profile_when_missing
test_upsert_updates_existing_profile
test_upsert_preserves_user_id
test_upsert_updates_updated_at_timestamp
test_delete_removes_existing_profile
test_delete_returns_false_when_missing
```

**`tests/test_stub.py` (extended):**

```
test_ranker_returns_recipes_unchanged
test_ranker_assigns_match_percentage_zero
test_ranker_assigns_score_one
test_ranker_handles_empty_recipes
test_reasoner_returns_ingredients_unchanged
```

### 8.3 Sample recipes fixture

`tests/fixtures/sample_recipes.json` contains ~30 small recipes for fast tests:

```json
[
  {
    "id": "r001",
    "title": "Tomato Basil Pasta",
    "title_es": "Pasta con tomate y albahaca",
    "ingredients": ["pasta", "tomato", "basil", "olive oil", "garlic"],
    "ingredients_es": ["pasta", "tomate", "albahaca", "aceite de oliva", "ajo"],
    "instructions": ["Boil pasta", "Sauté garlic", "Mix"],
    "instructions_es": ["Hervir pasta", "Saltear ajo", "Mezclar"],
    "estimated_time_minutes": 25
  },
  ...
]
```

---

## 9. Configuration

### 9.1 `infrastructure/config.py`

```python
"""Application configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "postgresql://cooksense:cooksense@localhost:5432/cooksense"
    chroma_host: str = ""
    chroma_api_key: str = ""
    chroma_persist_dir: Path = Path("./data/.chroma")
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"


settings = Settings()
```

---

## 10. Commit Convention — Phase 1

```
chore(infra): add config module with environment-based settings
chore(infra): add chroma client factory for embedded, http, ephemeral modes
test(infra): add chroma client tests
chore(infra): add SQLAlchemy models for user profiles
chore(infra): add postgres session and engine setup
test(infra): add profile repository tests
feat(infra): implement profile repository CRUD
chore(infra): add translation pipeline contract
test(infra): add translation pipeline cache tests
feat(infra): implement disk caching in translation pipeline
chore(infra): add corpus ingestion script with filtering
test(infra): add corpus filtering tests
test(infra): add corpus ingestion smoke tests
feat(infra): implement corpus ingestion CSV reader
chore(api): add recipe and profile pydantic models
test(api): add recipe model validation tests
test(api): add profile model validation tests
feat(api): implement recipe model with field constraints
feat(api): implement profile request and response models
test(api): add profile endpoint create tests
feat(api): implement POST /api/profile endpoint
test(api): add profile endpoint update tests
feat(api): make POST /api/profile upsert
test(api): add profile endpoint get tests
feat(api): implement GET /api/profile/{user_id} endpoint
test(api): add recipe search endpoint validation tests
feat(api): implement POST /api/recipes/search endpoint without ranking
test(api): add recipe search ranking tests
feat(api): wire RecipeRanker via deps.py to search endpoint
chore(stub): extend RecipeRanker with rank() that returns input unchanged
test(stub): add ranker stub tests
docs(api): document recipes search and profile endpoints in OpenAPI
docs: add Phase 1 progress note to backend README
```

~30-35 commits expected.

---

## 11. What NOT to Do in Phase 1

- **Do not** add LLM personalization to recipes. That's Phase 2.
- **Do not** add vision/image upload. Phase 2.
- **Do not** add follow-up Q&A on recipes. Phase 2.
- **Do not** add meal plan generation. Phase 3.
- **Do not** add real authentication. Anonymous user IDs only.
- **Do not** modify Phase 0 code (healthz, hello world).
- **Do not** add caching (Redis, etc.). The stub doesn't need it; real Phase 1 doesn't either.
- **Do not** add rate limiting. Phase 5.
- **Do not** add database migrations (Alembic). Use `Base.metadata.create_all` for V1; migrations come if there's a schema change in V2.
- **Do not** ingest the real 50k corpus in CI. Tests use the 30-recipe fixture.
- **Do not** translate fixture recipes via real Claude calls. The fixture has hand-translated Spanish; translator tests use mocks.
- **Do not** add real Anthropic API calls in any test. Mock the translator.
- **Do not** add Docker. Phase 5.
- **Do not** add CORS yet beyond a config field. Phase 5.
- **Do not** modify the Phase 0 stub interface. Extend it with real methods, but keep the contract.
- **Do not** add NPM, Node, or any JS tooling.

---

## 12. Acceptance Criteria for Phase 1 Completion

- [ ] `pip install -e ".[stub,dev]"` succeeds
- [ ] `pytest` returns green with 60+ tests
- [ ] `ruff check . && ruff format --check .` clean
- [ ] All endpoints documented in OpenAPI (visible at `/docs` when running)
- [ ] Phase 0 code unchanged (verify with `git diff main..phase-1-rag-foundation -- backend/api/routes/healthz.py`)
- [ ] `cooksense-core` private repo has real ranker implementation with tests passing
- [ ] Public stub still functional (returns recipes unchanged)
- [ ] Sample recipes fixture (`sample_recipes.json`) has 30 recipes with both EN and ES versions
- [ ] Profile CRUD works end-to-end via TestClient
- [ ] Recipe search returns recipes from sample corpus when called via TestClient
- [ ] Translation pipeline caches to disk (verifiable in test)
- [ ] Ingestion script runs without errors against the sample CSV
- [ ] No real Anthropic API calls in tests (verified by mocking)
- [ ] Backend CI workflow green
- [ ] PR opened on `phase-1-rag-foundation` against `main`, NOT merged

---

## 13. Branch & PR Workflow — Phase 1

1. `git checkout -b phase-1-rag-foundation` from `main`
2. Commit on branch following Section 10
3. `git push -u origin phase-1-rag-foundation`
4. `gh pr create --base main --head phase-1-rag-foundation --title "Phase 1: Backend Foundation (RAG + Profiles)"` with body including:
   - Summary
   - Acceptance criteria checklist
   - "What's deferred to Phase 2": vision pipeline, LLM personalization, conversational Q&A
5. NOT merge.
6. Report: "Phase 1 complete. PR opened: <URL>. Acceptance criteria checked. Awaiting review." and stop.

---

## 14. Handoff to Phase 2 (preview)

- Vision endpoint: `POST /api/vision/extract-ingredients` (multipart upload)
- LLM personalization: real Claude calls to generate personalized recipe descriptions
- Conversational Q&A: `POST /api/recipes/{id}/ask`
- Image hash caching to avoid re-vision on duplicate photos
- Bilingual LLM responses driven by profile language

Phase 2 brings vision + LLM. Phase 1 ships the RAG foundation underneath.
