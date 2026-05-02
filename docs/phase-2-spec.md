# Phase 2 Spec — Backend Vision Pipeline + Conversational RAG

**Repo:** `cooksense` (public) + `cooksense-core` (private)
**Domain:** Recipe assistant
**Stack:** Python 3.12, FastAPI, Anthropic Claude SDK, ChromaDB, pytest
**Approach:** Test-Driven Development, granular commits, feature branch + PR
**Branch:** `phase-2-vision-llm`

---

## 1. Goal of Phase 2

Add the AI muscle. Phase 1 has RAG and profiles. Phase 2 adds Claude Vision (ingredient detection from photos), LLM-personalized recipe descriptions, and conversational follow-ups on individual recipes. Caching is built in from day one to control costs.

At the end of Phase 2:
- `POST /api/vision/extract-ingredients` accepts multipart image, returns detected ingredients
- Claude Vision called via real Anthropic SDK with hash-based cache (same image → no re-call)
- `POST /api/recipes/search` (extended) returns recipes with LLM-personalized descriptions per the user's profile language
- `POST /api/recipes/{recipe_id}/ask` accepts a follow-up question, streams or returns full text answer
- Caching layer: image hash cache + question/recipe cache (not the same as ChromaDB retrieval cache)
- Real `cooksense-core.IngredientReasoner` normalizes detected ingredients (synonyms, quantity inference)
- Stub `IngredientReasoner` returns ingredients unchanged
- All Phase 0 + Phase 1 code unchanged
- Real Anthropic SDK calls in `cooksense-core`; stub uses canned responses

---

## 2. Solution & Folder Structure

```
cooksense/
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── healthz.py                    (unchanged)
│   │   │   ├── recipes.py                    (extended)
│   │   │   ├── profile.py                    (unchanged)
│   │   │   └── vision.py                     (NEW)
│   │   ├── models/
│   │   │   ├── recipe.py                     (extended)
│   │   │   ├── profile.py                    (unchanged)
│   │   │   ├── search.py                     (unchanged)
│   │   │   ├── vision.py                     (NEW)
│   │   │   └── question.py                   (NEW)
│   │   ├── deps.py                           (extended)
│   │   └── main.py                           (extended)
│   ├── infrastructure/
│   │   ├── llm/
│   │   │   ├── __init__.py                   (NEW)
│   │   │   ├── anthropic_client.py           (NEW)
│   │   │   └── cache.py                      (NEW)
│   │   ├── db/                               (unchanged)
│   │   ├── storage/                          (unchanged)
│   │   └── config.py                         (extended)
│   ├── stub/
│   │   ├── ranker.py                         (extended)
│   │   ├── reasoner.py                       (extended)
│   │   ├── vision_extractor.py               (NEW)
│   │   ├── personalizer.py                   (NEW)
│   │   └── qa_responder.py                   (NEW)
│   ├── tests/
│   │   ├── conftest.py                       (extended)
│   │   ├── api/
│   │   │   ├── test_vision.py                (NEW)
│   │   │   ├── test_recipes_search.py        (extended)
│   │   │   └── test_recipes_ask.py           (NEW)
│   │   ├── infrastructure/
│   │   │   ├── test_anthropic_client.py      (NEW)
│   │   │   └── test_llm_cache.py             (NEW)
│   │   └── fixtures/
│   │       └── images/
│   │           ├── pantry_basic.jpg
│   │           ├── fridge_well_lit.jpg
│   │           └── empty.jpg
│   └── pyproject.toml                        (extended)
└── (cooksense-core: see section 7)
```

---

## 3. Vision Pipeline

### 3.1 `POST /api/vision/extract-ingredients`

**Request:** multipart form-data
- `file`: image file (jpg, png, webp; max 10MB)

`X-User-Id` header required (profile loaded server-side for language preference).

**Response (200):**
```json
{
  "request_id": "uuid-of-this-request",
  "ingredients": [
    {
      "name": "tomato",
      "name_es": "tomate",
      "confidence": 0.92,
      "estimated_quantity": "2-3 medium",
      "category": "vegetable"
    },
    {
      "name": "olive oil",
      "name_es": "aceite de oliva",
      "confidence": 0.88,
      "estimated_quantity": "small bottle",
      "category": "oil"
    }
  ],
  "image_hash": "sha256-...",
  "from_cache": false
}
```

**Errors:**
- 400 `Validation.ImageMissing`: no file in request
- 400 `Validation.ImageTooLarge`: file > 10MB
- 400 `Validation.ImageInvalidFormat`: not jpg/png/webp
- 400 `Profile.NotFound`: user_id has no profile
- 429 `RateLimit.Exceeded`: per-user daily limit hit (5 photos/day per Profile section in cooksense-profile.md)
- 503 `Vision.Failed`: Anthropic API error or network issue

**Notes:**
- Image is stored ephemerally (in memory only during request). Hash is computed and image discarded after vision processing.
- `image_hash` returned so client can check `from_cache` for transparency.
- `category` is one of: vegetable, fruit, protein, grain, dairy, oil, herb, spice, condiment, other

### 3.2 Vision flow inside the backend

```
1. Receive multipart upload
2. Read bytes, validate format and size
3. Compute SHA-256 hash of bytes
4. Check cache: if hash exists → return cached result immediately
5. Cache miss:
   a. Call Anthropic Claude Vision via cooksense-core (or stub)
   b. Real implementation in cooksense-core sends image + prompt to Claude
   c. Parse Claude response into Ingredient[] list
   d. Apply IngredientReasoner.reason() for normalization (synonyms, etc.)
   e. Store in cache keyed by hash
6. Return response with from_cache=false
7. Update per-user rate limit counter (5/day)
```

### 3.3 Decisions

- **Hash-based cache, not similarity-based.** Same exact image bytes → cache hit. Different image (even slightly different lighting) → cache miss. Simple, predictable, cheap. Phase 2 doesn't try to be clever about "similar" images.
- **Image bytes never persisted to disk or database.** Privacy-friendly. Only the extraction result (ingredients list) and the hash are persisted.
- **Cache TTL: 30 days** by default, configurable. Recipes don't change, ingredients don't change, but stale caches eventually take up space.
- **Cache backend: SQLite for dev, PostgreSQL for prod.** Reuses the same database setup from Phase 1.
- **Vision implementation lives in `cooksense-core`.** The stub returns a canned response (e.g., always returns 5 generic ingredients). The real one calls Claude.

---

## 4. LLM Personalization in Recipe Search

### 4.1 Extended `POST /api/recipes/search`

Phase 1's response had raw recipes. Phase 2 adds an LLM-rewritten description per recipe, in the user's language.

**Response (extended):**
```json
{
  "recipes": [
    {
      "id": "r123",
      "title": "Pasta with Tomato and Basil",
      "title_es": "Pasta con tomate y albahaca",
      "ingredients": ["..."],
      "ingredients_es": ["..."],
      "instructions": ["..."],
      "instructions_es": ["..."],
      "estimated_time_minutes": 25,
      "match_percentage": 0.85,
      "score": 0.92,
      "personalized_description": "A quick 25-min pasta that fits your 30-min budget, aligns with your vegetarian profile, and uses 5 of the 6 ingredients you already have."
    }
  ],
  "total_found": 5,
  "query_id": "uuid-of-this-search"
}
```

The `personalized_description` is generated by the `cooksense-core.PersonalizedDescriber` (proprietary). The stub returns a generic description.

### 4.2 LLM call optimization

- **Personalize only top-N recipes** (default: top 5, configurable). Don't waste LLM tokens on the long tail.
- **Cache personalized descriptions** by `(recipe_id, profile_signature)` where profile_signature is a stable hash of the relevant profile fields (skill, time_budget, dietary_restrictions, language).
- **Cache TTL: 7 days.** Personalized descriptions are stable for a profile.

### 4.3 Decisions

- **Personalization is proprietary (in `cooksense-core`).** The stub returns a one-sentence generic description like "A simple recipe matching your preferences."
- **Streaming optional, not used in V1.** The Android app waits for full response. Streaming complicates the mobile client and offers marginal UX gain.

---

## 5. Conversational Follow-up: `POST /api/recipes/{recipe_id}/ask`

**Request:**
```json
{
  "question": "Can I substitute spinach for the basil?",
  "context": {
    "previous_questions": [
      {
        "question": "Is this gluten-free?",
        "answer": "No, this recipe contains pasta which has gluten. You could substitute with gluten-free pasta."
      }
    ]
  }
}
```

`X-User-Id` required. `recipe_id` must match a real recipe in the corpus.

**Response (200):**
```json
{
  "answer": "Yes, spinach works well as a substitute. Wilt it in olive oil with garlic for 2-3 minutes before adding to the pasta. The flavor is milder than basil but still complements the tomato.",
  "answer_es": null,
  "language": "en",
  "request_id": "uuid",
  "from_cache": false
}
```

`answer_es` is populated only if user's profile language is `es`. The opposite for `answer` if language is en.

**Errors:**
- 404 `Recipe.NotFound`: recipe_id doesn't exist
- 429 `RateLimit.Exceeded`: 10 questions/day per user (per Profile section)
- 400 `Profile.NotFound`
- 400 `Validation.QuestionEmpty`: empty question
- 503 `LLM.Failed`: Anthropic error

### 5.1 Q&A flow

```
1. Validate request
2. Load recipe from ChromaDB (fetch by id, not search)
3. Compute cache key: (recipe_id, hash(question), profile.language)
4. Cache hit → return immediately with from_cache=true
5. Cache miss:
   a. Build prompt: recipe context + previous_questions + new question
   b. Call Claude via cooksense-core.QAResponder (real) or stub
   c. Parse response, validate not empty
   d. Cache the answer
6. Return response, increment per-user rate limit
```

### 5.2 Decisions

- **Previous questions is client-managed context.** Backend doesn't store conversation history per recipe; client sends recent Q&A as context. Stateless backend, simpler scaling.
- **Question hash for cache:** normalize whitespace, lowercase, strip punctuation. So "Can I substitute spinach?" and "can i substitute spinach" hit the same cache.
- **Cache TTL: 7 days.** Q&A answers about static recipes don't go stale fast.
- **No streaming in V1.** Same reasoning as personalization.

---

## 6. Caching Layer

### 6.1 `infrastructure/llm/cache.py`

```python
"""LLM call cache.

Generic cache abstraction backed by SQLite (dev) or PostgreSQL (prod).
Stores LLM responses keyed by content hash to avoid duplicate API calls.

Cache entries have:
- key: deterministic hash of inputs
- response: serialized JSON of the LLM response
- created_at: for TTL eviction
- access_count: useful for debugging hot keys

Eviction: lazy on read (check TTL) + scheduled job to delete expired (out of scope V1).
"""

import hashlib
import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from infrastructure.storage.models import LLMCacheEntry


class LLMCache:
    def __init__(self, session: Session, default_ttl: timedelta = timedelta(days=7)) -> None:
        self._session = session
        self._default_ttl = default_ttl

    @staticmethod
    def make_key(*parts: str) -> str:
        """Compute a deterministic cache key from string parts."""
        joined = "|".join(parts)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict | None:
        entry = self._session.query(LLMCacheEntry).filter_by(key=key).first()
        if entry is None:
            return None
        if entry.created_at + self._default_ttl < datetime.utcnow():
            self._session.delete(entry)
            self._session.commit()
            return None
        entry.access_count += 1
        self._session.commit()
        return json.loads(entry.response)

    def set(self, key: str, response: dict) -> None:
        entry = LLMCacheEntry(
            key=key,
            response=json.dumps(response),
            created_at=datetime.utcnow(),
            access_count=0,
        )
        # Upsert
        existing = self._session.query(LLMCacheEntry).filter_by(key=key).first()
        if existing:
            existing.response = entry.response
            existing.created_at = entry.created_at
            existing.access_count = 0
        else:
            self._session.add(entry)
        self._session.commit()
```

### 6.2 SQLAlchemy model addition

`infrastructure/storage/models.py` (extended):

```python
class LLMCacheEntry(Base):
    __tablename__ = "llm_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA-256 hex
    response: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    access_count: Mapped[int] = mapped_column(default=0)
```

### 6.3 Per-user rate limiting

A simple table tracks daily counts per user:

```python
class UserDailyUsage(Base):
    __tablename__ = "user_daily_usage"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)  # ISO date
    vision_count: Mapped[int] = mapped_column(default=0)
    qa_count: Mapped[int] = mapped_column(default=0)
```

Limits enforced in middleware or as a dependency in route handlers.

### 6.4 Decisions

- **Cache + rate limit share the same database.** Postgres in prod. Avoids Redis dependency for V1.
- **Daily reset is implicit.** New row per (user, date) means yesterday's usage doesn't matter for today.
- **No background job for cache eviction.** TTL checked on read; expired entries are deleted then. Acceptable for V1 scale.

---

## 7. Private repo: `cooksense-core` Phase 2 work

### 7.1 What goes in `cooksense-core` Phase 2

```
cooksense-core/
├── cooksense_core/
│   ├── __init__.py              (extended)
│   ├── ranker.py                (unchanged from Phase 1)
│   ├── reasoner.py              (real implementation)
│   ├── vision_extractor.py      (NEW, real)
│   ├── personalizer.py          (NEW, real)
│   ├── qa_responder.py          (NEW, real)
│   └── prompts/
│       ├── __init__.py
│       ├── ingredient_extraction.txt
│       ├── recipe_personalization.txt
│       └── recipe_qa.txt
└── tests/
    ├── test_ranker.py           (unchanged)
    ├── test_reasoner.py         (extended)
    ├── test_vision.py           (NEW)
    ├── test_personalizer.py     (NEW)
    └── test_qa_responder.py     (NEW)
```

### 7.2 Vision extractor (proprietary)

```python
# cooksense-core/cooksense_core/vision_extractor.py
"""Real Claude Vision call for ingredient extraction."""

import anthropic

from .prompts import load_prompt


class VisionExtractor:
    def __init__(self, client: anthropic.Anthropic, model: str = "claude-3-5-sonnet-latest") -> None:
        self._client = client
        self._model = model
        self._system_prompt = load_prompt("ingredient_extraction.txt")

    def extract(self, image_bytes: bytes, language: str = "en") -> list[dict]:
        """Send image to Claude Vision, parse response into ingredient list."""
        # Real implementation:
        # 1. Encode image to base64
        # 2. Call Claude Messages API with image + system prompt
        # 3. Parse JSON response
        # 4. Validate schema with Pydantic
        # 5. Return list of {name, name_es, confidence, estimated_quantity, category}
        ...
```

### 7.3 Personalizer (proprietary)

```python
# cooksense-core/cooksense_core/personalizer.py
"""LLM-driven recipe description personalization."""


class PersonalizedDescriber:
    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    def describe(self, recipe: dict, profile: dict) -> str:
        """Generate a 1-2 sentence personalized description of the recipe."""
        # Real implementation:
        # Compose prompt referencing profile (skill, time, diet, family size)
        # and recipe details. Returns personalized string.
        ...
```

### 7.4 QA responder (proprietary)

```python
# cooksense-core/cooksense_core/qa_responder.py
"""Conversational Q&A on a specific recipe."""


class QAResponder:
    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    def answer(
        self,
        recipe: dict,
        question: str,
        previous_questions: list[dict],
        language: str,
    ) -> str:
        """Generate an answer to the user's question about the recipe."""
        # Real implementation:
        # Compose a prompt with the recipe context, conversation history,
        # and the new question. Returns text in user's language.
        ...
```

### 7.5 Stub equivalents (in public repo)

`backend/stub/vision_extractor.py`:

```python
class VisionExtractor:
    """Stub: returns 5 generic ingredients regardless of image."""

    def extract(self, image_bytes: bytes, language: str = "en") -> list[dict]:
        return [
            {
                "name": "tomato",
                "name_es": "tomate",
                "confidence": 0.7,
                "estimated_quantity": "unknown",
                "category": "vegetable",
            },
            {"name": "onion", "name_es": "cebolla", "confidence": 0.7, "estimated_quantity": "unknown", "category": "vegetable"},
            {"name": "garlic", "name_es": "ajo", "confidence": 0.7, "estimated_quantity": "unknown", "category": "vegetable"},
            {"name": "olive oil", "name_es": "aceite de oliva", "confidence": 0.7, "estimated_quantity": "unknown", "category": "oil"},
            {"name": "salt", "name_es": "sal", "confidence": 0.9, "estimated_quantity": "unknown", "category": "spice"},
        ]
```

`backend/stub/personalizer.py`:

```python
class PersonalizedDescriber:
    """Stub: returns generic description regardless of profile."""

    def describe(self, recipe: dict, profile: dict) -> str:
        title = recipe.get("title", "this recipe")
        return f"A simple recipe matching your preferences: {title}."
```

`backend/stub/qa_responder.py`:

```python
class QAResponder:
    """Stub: returns generic answer."""

    def answer(self, recipe, question, previous_questions, language) -> str:
        if language == "es":
            return "No puedo responder preguntas detalladas en este modo demo. Por favor instalá el paquete completo de cooksense-core para respuestas reales."
        return "I can't answer detailed questions in this demo mode. Please install the full cooksense-core package for real answers."
```

### 7.6 Stub vs real package

`backend/api/deps.py` extended:

```python
try:
    from cooksense_core import (
        IngredientReasoner,
        PersonalizedDescriber,
        QAResponder,
        RecipeRanker,
        VisionExtractor,
    )
    _CORE_MODE = "proprietary"
except ImportError:
    from stub import (
        IngredientReasoner,
        PersonalizedDescriber,
        QAResponder,
        RecipeRanker,
        VisionExtractor,
    )
    _CORE_MODE = "stub"
```

---

## 8. Anthropic Client wiring

### 8.1 `infrastructure/llm/anthropic_client.py`

```python
"""Centralized Anthropic SDK client.

Single instance shared across requests for connection pooling.
"""

import anthropic

from infrastructure.config import settings


class AnthropicClientFactory:
    _instance: anthropic.Anthropic | None = None

    @classmethod
    def get(cls) -> anthropic.Anthropic:
        if cls._instance is None:
            cls._instance = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return cls._instance


def get_anthropic_client() -> anthropic.Anthropic:
    """FastAPI dependency."""
    return AnthropicClientFactory.get()
```

The vision/qa/personalizer use this via injection.

---

## 9. Test Strategy — Phase 2

### 9.1 Test categories

- **Unit tests** for caches, validators, request/response models
- **Integration tests** with FastAPI TestClient + mocked Anthropic SDK + ephemeral ChromaDB + SQLite
- **Smoke tests** for stub: ensure vision/personalizer/qa stubs return expected shapes

No real Anthropic API calls in tests. All `Anthropic()` clients are mocked. The `cooksense-core` private repo's tests can mock at the SDK level too.

### 9.2 Tests by file

**`tests/api/test_vision.py`:**

```
test_post_vision_with_valid_image_returns_200
test_post_vision_with_no_file_returns_400_image_missing
test_post_vision_with_oversized_file_returns_400
test_post_vision_with_invalid_format_returns_400
test_post_vision_without_user_id_returns_400_profile_not_found
test_post_vision_response_includes_request_id
test_post_vision_response_includes_image_hash
test_post_vision_response_includes_ingredients_array
test_post_vision_each_ingredient_has_required_fields
test_post_vision_uses_cache_on_duplicate_image_hash
test_post_vision_returns_from_cache_true_when_cached
test_post_vision_returns_from_cache_false_on_first_call
test_post_vision_persists_only_extraction_not_image
test_post_vision_increments_user_rate_limit
test_post_vision_returns_429_when_rate_limit_hit
test_post_vision_handles_anthropic_error_returns_503
```

**`tests/api/test_recipes_search.py` (extended from Phase 1):**

```
test_search_now_returns_personalized_description
test_search_personalized_description_in_user_language_es
test_search_personalized_description_in_user_language_en
test_search_personalization_caches_results
test_search_personalization_skips_long_tail_recipes
```

**`tests/api/test_recipes_ask.py`:**

```
test_post_ask_with_valid_question_returns_200
test_post_ask_response_includes_answer
test_post_ask_response_includes_request_id
test_post_ask_with_empty_question_returns_400
test_post_ask_with_unknown_recipe_id_returns_404
test_post_ask_without_user_id_returns_400_profile_not_found
test_post_ask_with_previous_context_includes_in_prompt
test_post_ask_caches_question_recipe_combination
test_post_ask_returns_from_cache_true_when_cached
test_post_ask_increments_user_rate_limit
test_post_ask_returns_429_when_rate_limit_hit
test_post_ask_in_spanish_profile_returns_spanish_answer
test_post_ask_in_english_profile_returns_english_answer
test_post_ask_handles_anthropic_error_returns_503
```

**`tests/infrastructure/test_anthropic_client.py`:**

```
test_factory_returns_singleton_client
test_factory_passes_api_key_from_settings
test_factory_handles_missing_api_key_gracefully_in_test_mode
```

**`tests/infrastructure/test_llm_cache.py`:**

```
test_cache_get_returns_none_for_missing_key
test_cache_set_persists_value
test_cache_get_returns_persisted_value
test_cache_get_returns_none_for_expired_entry
test_cache_set_overwrites_existing_key
test_cache_get_increments_access_count
test_cache_make_key_returns_deterministic_hash
test_cache_make_key_different_for_different_inputs
test_cache_handles_concurrent_set_calls
```

**`tests/test_stub.py` (extended):**

```
test_stub_vision_extractor_returns_5_ingredients
test_stub_vision_extractor_returns_required_fields
test_stub_personalizer_returns_generic_description
test_stub_qa_responder_returns_demo_message_in_english
test_stub_qa_responder_returns_demo_message_in_spanish
```

### 9.3 Image fixtures

`tests/fixtures/images/`:
- `pantry_basic.jpg` (~50KB, low res, fake pantry photo)
- `fridge_well_lit.jpg` (~50KB)
- `empty.jpg` (~10KB, blank-ish)

Used in tests to send via TestClient. The stub doesn't process them; just hashes the bytes.

---

## 10. Commit Convention — Phase 2

```
chore(infra): add Anthropic client factory with singleton
test(infra): add Anthropic client factory tests
chore(infra): add LLM cache SQLAlchemy model
chore(infra): add user daily usage SQLAlchemy model
test(infra): add LLM cache get/set tests
feat(infra): implement LLMCache with TTL eviction
test(infra): add LLM cache TTL tests
test(infra): add LLM cache deterministic key tests
feat(infra): implement deterministic make_key in LLMCache
chore(api): add vision request/response pydantic models
chore(api): add question request/response pydantic models
test(api): add vision endpoint validation tests
feat(api): implement POST /api/vision/extract-ingredients endpoint
test(api): add vision endpoint cache tests
feat(api): wire image hash cache to vision endpoint
test(api): add vision endpoint rate limit tests
feat(api): add daily usage tracking and 5-photo limit
chore(stub): add VisionExtractor stub returning 5 generic ingredients
test(stub): add VisionExtractor stub tests
chore(stub): add PersonalizedDescriber stub
test(stub): add PersonalizedDescriber stub tests
chore(stub): add QAResponder stub with bilingual demo messages
test(stub): add QAResponder stub tests
test(api): extend recipes search tests with personalization
feat(api): personalize top recipes with PersonalizedDescriber via deps
test(api): add personalization caching tests
feat(api): wire LLMCache to personalization
test(api): add recipe ask endpoint validation tests
feat(api): implement POST /api/recipes/{id}/ask endpoint
test(api): add recipe ask cache tests
feat(api): wire LLMCache to ask endpoint
test(api): add recipe ask rate limit tests
feat(api): add 10-question daily limit to ask endpoint
test(api): add bilingual answer language tests
docs(api): document vision and ask endpoints in OpenAPI
docs: add Phase 2 progress note to backend README
```

~35 commits expected.

---

## 11. What NOT to Do in Phase 2

- **Do not** call real Anthropic API in tests. Mock everything.
- **Do not** add streaming responses. V1 returns full responses synchronously.
- **Do not** persist images. Hash and discard.
- **Do not** add image preprocessing (resize, crop, compress). Phase 4 mobile client should handle that.
- **Do not** implement similarity-based caching for images. Hash only.
- **Do not** add Redis or any external cache. SQL is fine.
- **Do not** add background jobs (Celery, etc.). Cache eviction is lazy (on-read).
- **Do not** modify Phase 0 or Phase 1 code beyond agreed extensions.
- **Do not** persist conversation history server-side. Client manages context.
- **Do not** add real-time websockets or SSE. V1 is REST only.
- **Do not** add OAuth, JWT, or any auth. Anonymous user IDs.
- **Do not** generate ingredient images (vision is detection only, not generation).
- **Do not** add a queue between request and Anthropic call. Synchronous.
- **Do not** retry failed Anthropic calls. Return 503 on first failure. Phase 5 may add retry logic.
- **Do not** compose multi-modal prompts (image + many recipes). One image, one task.

---

## 12. Acceptance Criteria for Phase 2 Completion

- [ ] `pytest` returns green with 100+ tests (60 from Phase 1 + ~40 from Phase 2)
- [ ] All Phase 2 endpoints reachable: vision/extract-ingredients, recipes/{id}/ask, recipes/search (extended)
- [ ] Vision endpoint accepts multipart upload, validates format/size
- [ ] Hash-based image cache works (verified by test: same image twice → from_cache=true second time)
- [ ] Daily rate limit per user: 5 vision calls, 10 questions
- [ ] Personalized descriptions returned in user's profile language
- [ ] Q&A endpoint returns relevant answers (with stub: demo message; with real: actual content)
- [ ] LLM cache module deletes expired entries on read
- [ ] No real Anthropic API calls in tests (mocked SDK)
- [ ] `cooksense-core` private has VisionExtractor, PersonalizedDescriber, QAResponder with passing tests
- [ ] Public stub returns expected shapes for all three
- [ ] `ruff check . && ruff format --check .` clean
- [ ] Phase 0 + Phase 1 code unchanged
- [ ] Backend CI green
- [ ] PR opened on `phase-2-vision-llm` against `main`, NOT merged

---

## 13. Branch & PR Workflow — Phase 2

1. `git checkout -b phase-2-vision-llm` from `main`
2. Commit on branch following Section 10
3. `git push -u origin phase-2-vision-llm`
4. `gh pr create --base main --head phase-2-vision-llm --title "Phase 2: Vision + Conversational RAG"`
5. PR body: summary + acceptance criteria + "What's deferred to Phase 3": meal planning, shopping list
6. NOT merge.
7. Report and stop.

---

## 14. Handoff to Phase 3 (preview)

- 3-day meal plan generator (multiple recipes, optimized for ingredient reuse, variety, macros)
- Shopping list generator from a meal plan
- New endpoint: `POST /api/meal-plan/generate`
- New endpoint: `POST /api/meal-plan/{plan_id}/shopping`
- Heaviest LLM use case yet (multi-recipe coordination)
- Caching strategy adapts to multi-recipe scope

Phase 3 is the differentiator. Phase 2 made the AI features real; Phase 3 chains them into something competitors don't have.
