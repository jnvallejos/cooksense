# Phase 3 Spec — Backend Meal Planning + Shopping List

**Repo:** `cooksense` (public) + `cooksense-core` (private)
**Domain:** Recipe assistant — multi-meal coordination
**Stack:** Python 3.12, FastAPI, Anthropic Claude SDK, ChromaDB, pytest
**Approach:** Test-Driven Development, granular commits, feature branch + PR
**Branch:** `phase-3-meal-planning`

---

## 1. Goal of Phase 3

The differentiator. Phases 1 and 2 give us "find me a recipe" — Phase 3 gives us "plan my next 3 days with what I have." This is what separates CookSense from generic recipe apps. The proprietary planning logic in `cooksense-core` is the heart of the product.

At the end of Phase 3:
- `POST /api/meal-plan/generate` returns a 3-day, 9-meal plan (breakfast/lunch/dinner) given pantry ingredients + profile
- `POST /api/meal-plan/{plan_id}/shopping` returns a shopping list of missing ingredients consolidated across the plan
- Plans are persisted in PostgreSQL keyed by user_id + plan_id (UUID)
- Real `cooksense-core.MealPlanner` optimizes: ingredient reuse, variety, macro alignment, time budget across days
- Public stub `MealPlanner` returns 9 random recipes from the corpus with no optimization
- Real `cooksense-core.ShoppingListBuilder` consolidates ingredients with quantity inference
- Public stub `ShoppingListBuilder` returns a flat union of ingredients minus pantry
- All Phase 0-2 code unchanged

---

## 2. Solution & Folder Structure

```
cooksense/
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── healthz.py                     (unchanged)
│   │   │   ├── recipes.py                     (unchanged)
│   │   │   ├── profile.py                     (unchanged)
│   │   │   ├── vision.py                      (unchanged)
│   │   │   └── meal_plan.py                   (NEW)
│   │   ├── models/
│   │   │   ├── recipe.py                      (unchanged)
│   │   │   ├── profile.py                     (unchanged)
│   │   │   ├── search.py                      (unchanged)
│   │   │   ├── vision.py                      (unchanged)
│   │   │   ├── question.py                    (unchanged)
│   │   │   ├── meal_plan.py                   (NEW)
│   │   │   └── shopping.py                    (NEW)
│   │   ├── deps.py                            (extended)
│   │   └── main.py                            (extended)
│   ├── infrastructure/
│   │   ├── llm/                               (unchanged)
│   │   ├── db/                                (unchanged)
│   │   ├── storage/
│   │   │   ├── models.py                      (extended: MealPlan + MealPlanRecipe tables)
│   │   │   └── meal_plan_repository.py        (NEW)
│   │   └── config.py                          (unchanged)
│   ├── stub/
│   │   ├── ranker.py                          (unchanged)
│   │   ├── reasoner.py                        (unchanged)
│   │   ├── vision_extractor.py                (unchanged)
│   │   ├── personalizer.py                    (unchanged)
│   │   ├── qa_responder.py                    (unchanged)
│   │   ├── meal_planner.py                    (NEW)
│   │   └── shopping_list_builder.py           (NEW)
│   ├── tests/
│   │   ├── api/
│   │   │   ├── test_meal_plan_generate.py     (NEW)
│   │   │   └── test_meal_plan_shopping.py     (NEW)
│   │   ├── infrastructure/
│   │   │   └── test_meal_plan_repository.py   (NEW)
│   │   └── stub/
│   │       ├── test_meal_planner.py           (NEW)
│   │       └── test_shopping_list_builder.py  (NEW)
│   └── pyproject.toml                         (unchanged from Phase 2)
└── (cooksense-core: see section 6)
```

---

## 3. Meal Plan Generation

### 3.1 `POST /api/meal-plan/generate`

**Request:**
```json
{
  "ingredients": ["pasta", "tomato", "onion", "chicken", "rice", "olive oil", "garlic", "spinach", "egg", "milk", "bread"],
  "days": 3,
  "meals_per_day": ["breakfast", "lunch", "dinner"]
}
```

`X-User-Id` required. Profile loaded server-side for personalization (skill, time, dietary, household size, macros).

`days` is currently fixed at 3 (V1 scope) but accepts the field for forward compatibility. `meals_per_day` defaults to `["breakfast", "lunch", "dinner"]`. V1 supports only these three.

**Response (201 Created):**
```json
{
  "plan_id": "uuid",
  "user_id": "uuid",
  "language": "es",
  "created_at": "2026-05-02T14:30:00Z",
  "days": [
    {
      "day_number": 1,
      "meals": [
        {
          "slot": "breakfast",
          "recipe": {
            "id": "r042",
            "title": "Tostadas con palta y huevo",
            "estimated_time_minutes": 10,
            "match_percentage": 0.95,
            "ingredients_summary": ["pan", "palta", "huevo"],
            "personalized_note": "Quick to make, uses pantry items, fits your eat-better goal."
          }
        },
        {
          "slot": "lunch",
          "recipe": { }
        },
        {
          "slot": "dinner",
          "recipe": { }
        }
      ]
    },
    { "day_number": 2, "meals": [ ] },
    { "day_number": 3, "meals": [ ] }
  ],
  "ingredient_reuse_score": 0.78,
  "variety_score": 0.85,
  "macro_alignment_score": 0.72,
  "from_cache": false
}
```

**Errors:**
- 400 `Validation.IngredientsEmpty`
- 400 `Profile.NotFound`
- 400 `Validation.DaysInvalid` if days != 3 (V1 constraint)
- 400 `Validation.MealsPerDayInvalid` if not the canonical 3 slots
- 429 `RateLimit.Exceeded` (1 plan per day per user; planning is heavier than search)
- 503 `Planning.Failed` (LLM error or core exception)

### 3.2 Plan generation flow

```
1. Validate request, load profile
2. Cache key: hash(sorted(ingredients) + profile_signature)
3. Cache hit -> return cached plan (rare, but useful for re-tries)
4. Cache miss:
   a. Apply IngredientReasoner.reason() to normalize ingredients
   b. Call cooksense-core.MealPlanner.plan(normalized_ingredients, profile, days=3)
   c. Real MealPlanner: Multi-step LLM-driven plan with constraint satisfaction
      - Step 1: Retrieve candidate recipe set via RAG (top 50)
      - Step 2: Score each candidate per slot (breakfast/lunch/dinner) considering profile
      - Step 3: LLM-driven selection optimizing reuse + variety + time across 9 slots
      - Step 4: Generate personalized notes per selected recipe
   d. Stub MealPlanner: Take 9 random recipes from corpus, assign to slots arbitrarily
   e. Persist plan in PostgreSQL with all metadata
5. Cache the plan keyed by hash
6. Return plan with from_cache=false
7. Increment user's daily usage counter
```

### 3.3 Decisions

- **3 days fixed in V1.** Scope discipline. V2 can add 5-day or weekly plans.
- **Slots fixed: breakfast/lunch/dinner.** V1 doesn't model snacks, dessert, or skipped meals. V2 can extend.
- **Persistent plans.** Each generated plan persists in DB with a UUID. Mobile client can re-fetch by plan_id without re-running LLM. Useful for "show my last plan" UX.
- **Ingredient reuse score.** Float 0-1. % of ingredients used in 2+ meals. Higher = less waste, fewer extras to buy. Surfaced in response so client can show it as a metric.
- **Variety score.** Float 0-1. Inverse penalty if same recipe type repeats (3 pastas in 3 days = low variety).
- **Macro alignment score.** Float 0-1. Distance from profile's macro goals (if `fitness_goal` is `lose` or `build`). For `none` or `eat_better`, this is always 1.0.
- **Per-user rate limit: 1 plan per day.** Planning is the most expensive operation; protect aggressively. 429 returns clear retry-after.
- **Cache key hashes the sorted ingredient list.** Same set -> same plan, regardless of input order.
- **Profile signature in cache key.** Profile change invalidates cached plan, as expected.

### 3.4 The proprietary algorithm (cooksense-core)

Conceptually, the real planner is:

```
Inputs:
  - normalized_ingredients: list[str]
  - profile: Profile
  - days: int = 3

Algorithm:
  1. Load all candidate recipes via RAG (top 50 from ChromaDB filtered by ingredients overlap)
  2. For each candidate, compute scores:
     - ingredient_overlap_score (% of recipe ingredients in pantry)
     - time_fit_score (how well recipe time fits profile.time_budget)
     - skill_fit_score (recipe difficulty vs profile.cooking_skill)
     - dietary_compliance_score (matches profile.dietary_restrictions)
     - macro_score (distance from profile macros, 1.0 if irrelevant)
  3. Group candidates by meal slot suitability (breakfast: <30 min, lunch/dinner: open)
  4. Run constraint solver with these objectives:
     - Maximize total ingredient reuse across 9 slots
     - Maximize variety (no two recipes of same type, no two with same primary protein)
     - Maximize average score
     - Respect dietary constraints absolutely
     - Respect time budget per meal slot
  5. For each selected recipe, generate personalized note (1-2 sentences, LLM call)
  6. Return MealPlan with day-by-day breakdown + scores
```

The constraint solver in V1 is a heuristic greedy algorithm + LLM-driven re-shuffle. Not pure ILP; pragmatic for portfolio scope. Real product would tune iteratively with user feedback.

### 3.5 Stub implementation

Public `backend/stub/meal_planner.py`:

```python
"""Stub meal planner: returns 9 random recipes from the sample corpus.

No optimization. ingredient_reuse_score, variety_score, macro_alignment_score
all return constant 0.5 (neutral baseline). Personalized notes are generic.
"""

import random


class MealPlanner:
    def __init__(self) -> None:
        pass

    def plan(
        self,
        ingredients: list[str],
        profile: dict,
        days: int = 3,
        meals_per_day: list[str] | None = None,
        candidates: list[dict] | None = None,
    ) -> dict:
        meals_per_day = meals_per_day or ["breakfast", "lunch", "dinner"]
        candidates = candidates or []

        if not candidates:
            return self._empty_plan(days, meals_per_day, profile)

        random.shuffle(candidates)
        slots_needed = days * len(meals_per_day)
        selected = candidates[:slots_needed]

        # Pad if not enough candidates
        while len(selected) < slots_needed:
            selected.append({
                "id": "stub-r000",
                "title": "Demo recipe (install cooksense-core for real recipes)",
                "estimated_time_minutes": 30,
                "match_percentage": 0.5,
                "ingredients_summary": ingredients[:3],
                "personalized_note": "Demo placeholder.",
            })

        days_data = []
        for day_num in range(1, days + 1):
            meals = []
            for slot_idx, slot in enumerate(meals_per_day):
                recipe_idx = (day_num - 1) * len(meals_per_day) + slot_idx
                meals.append({"slot": slot, "recipe": selected[recipe_idx]})
            days_data.append({"day_number": day_num, "meals": meals})

        return {
            "days": days_data,
            "ingredient_reuse_score": 0.5,
            "variety_score": 0.5,
            "macro_alignment_score": 0.5,
        }
```

The stub is deliberately bland. The real planner is the differentiator.

---

## 4. Shopping List Generation

### 4.1 `POST /api/meal-plan/{plan_id}/shopping`

**Request:** empty body (POST is used because some clients prefer to track this as a deliberate action; could be GET).

`X-User-Id` required. plan_id must belong to the user.

**Response (200):**
```json
{
  "plan_id": "uuid",
  "items": [
    {
      "ingredient": "tomato",
      "ingredient_es": "tomate",
      "estimated_quantity": "6 medium",
      "category": "vegetable",
      "needed_for": ["recipe_id_1", "recipe_id_4"]
    },
    {
      "ingredient": "olive oil",
      "ingredient_es": "aceite de oliva",
      "estimated_quantity": "small bottle",
      "category": "oil",
      "needed_for": ["recipe_id_1", "recipe_id_2", "recipe_id_5"]
    }
  ],
  "total_items": 12,
  "language": "es"
}
```

**Errors:**
- 404 `MealPlan.NotFound` if plan_id doesn't exist
- 403 `MealPlan.Forbidden` if plan_id exists but doesn't belong to this user
- 400 `Profile.NotFound`

### 4.2 Shopping list flow

```
1. Load plan from DB by plan_id, verify user_id matches
2. Load original pantry ingredients (persisted with the plan)
3. For each recipe in plan, collect ingredients
4. Subtract pantry ingredients (case-insensitive normalization)
5. Pass remaining ingredients to ShoppingListBuilder
6. Real builder:
   - Consolidates same ingredient appearing across recipes
   - Sums approximate quantities ("2 tomatoes" + "3 tomatoes" = "5 tomatoes")
   - Categorizes by type (vegetable, protein, etc.)
   - Generates Spanish translations
7. Stub builder:
   - Returns a flat list with no consolidation, generic quantities ("some")
   - No category detection
8. Return shopping list with from_cache=false (no caching for shopping list V1)
```

### 4.3 Decisions

- **Pantry ingredients are stored with the plan.** When the plan is generated, we persist the original `ingredients` field. Shopping list subtraction works deterministically even if user's pantry has changed since.
- **Quantity inference is best-effort.** Real ShoppingListBuilder uses LLM to estimate quantities from recipe instructions. Stub returns "some" or count-based heuristics.
- **No caching for shopping list V1.** Plans are cached; deriving the shopping list is cheap (no LLM call beyond what builder does). Skip unnecessary cache layer.
- **Categories help client UX.** Mobile app can group by aisle: produce, protein, dairy, etc. V1 categories: vegetable, fruit, protein, grain, dairy, oil, herb, spice, condiment, other.

---

## 5. Persistence Schema

### 5.1 SQLAlchemy models (extended)

```python
# infrastructure/storage/models.py (extended)

class MealPlan(Base):
    __tablename__ = "meal_plans"

    plan_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    pantry_ingredients: Mapped[list[str]] = mapped_column(JSON)
    language: Mapped[str] = mapped_column(String(2))
    ingredient_reuse_score: Mapped[float] = mapped_column()
    variety_score: Mapped[float] = mapped_column()
    macro_alignment_score: Mapped[float] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MealPlanRecipe(Base):
    __tablename__ = "meal_plan_recipes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), index=True)
    day_number: Mapped[int] = mapped_column()
    slot: Mapped[str] = mapped_column(String(20))  # breakfast/lunch/dinner
    recipe_id: Mapped[str] = mapped_column(String(64))
    recipe_title: Mapped[str] = mapped_column(String(500))
    recipe_title_es: Mapped[str] = mapped_column(String(500))
    estimated_time_minutes: Mapped[int] = mapped_column()
    match_percentage: Mapped[float] = mapped_column()
    ingredients_summary: Mapped[list[str]] = mapped_column(JSON)
    personalized_note: Mapped[str] = mapped_column(String(500))
```

### 5.2 Repository

```python
# infrastructure/storage/meal_plan_repository.py

class MealPlanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, plan: MealPlan, recipes: list[MealPlanRecipe]) -> str:
        self._session.add(plan)
        self._session.add_all(recipes)
        self._session.commit()
        return plan.plan_id

    def get_by_plan_id(self, plan_id: str) -> MealPlan | None:
        return self._session.query(MealPlan).filter_by(plan_id=plan_id).first()

    def get_recipes_for_plan(self, plan_id: str) -> list[MealPlanRecipe]:
        return (
            self._session.query(MealPlanRecipe)
            .filter_by(plan_id=plan_id)
            .order_by(MealPlanRecipe.day_number, MealPlanRecipe.slot)
            .all()
        )

    def is_owner(self, plan_id: str, user_id: str) -> bool:
        plan = self.get_by_plan_id(plan_id)
        return plan is not None and plan.user_id == user_id
```

### 5.3 Decisions

- **Two tables (plan + recipes) instead of JSON blob.** Easier to query individual recipes. Better DB hygiene. Cost: more rows, fine at this scale.
- **CASCADE delete:** if a plan is deleted, recipes go with it.
- **No update operation.** Plans are immutable once created. New plan = new plan_id.
- **No "delete plan" endpoint in V1.** User-facing feature would matter, but not for MVP. Plans can be deleted via DB ops if needed.

---

## 6. `cooksense-core` Phase 3 Work

### 6.1 What goes in private repo

```
cooksense-core/
├── cooksense_core/
│   ├── __init__.py                       (extended)
│   ├── ranker.py                         (unchanged from Phase 1)
│   ├── reasoner.py                       (unchanged from Phase 2)
│   ├── vision_extractor.py               (unchanged from Phase 2)
│   ├── personalizer.py                   (unchanged from Phase 2)
│   ├── qa_responder.py                   (unchanged from Phase 2)
│   ├── meal_planner.py                   (NEW)
│   ├── shopping_list_builder.py          (NEW)
│   ├── prompts/
│   │   ├── ingredient_extraction.txt     (unchanged)
│   │   ├── recipe_personalization.txt    (unchanged)
│   │   ├── recipe_qa.txt                 (unchanged)
│   │   ├── meal_plan_selection.txt       (NEW)
│   │   ├── meal_plan_personalization.txt (NEW)
│   │   └── shopping_list_consolidation.txt (NEW)
│   └── planning/
│       ├── __init__.py
│       ├── scoring.py                    # Per-recipe scoring functions
│       ├── slot_assignment.py            # Assign recipes to breakfast/lunch/dinner
│       └── greedy_optimizer.py           # Greedy + LLM re-shuffle
└── tests/
    ├── test_meal_planner.py              (NEW)
    ├── test_shopping_list_builder.py     (NEW)
    ├── test_planning_scoring.py          (NEW)
    ├── test_planning_slot_assignment.py  (NEW)
    └── test_planning_greedy_optimizer.py (NEW)
```

### 6.2 MealPlanner (real)

```python
# cooksense-core/cooksense_core/meal_planner.py
"""Proprietary meal planner."""


class MealPlanner:
    def __init__(self, anthropic_client, ranker) -> None:
        self._anthropic = anthropic_client
        self._ranker = ranker

    def plan(
        self,
        ingredients: list[str],
        profile: dict,
        days: int = 3,
        meals_per_day: list[str] | None = None,
        candidates: list[dict] | None = None,
    ) -> dict:
        # 1. Score candidates per slot
        # 2. Greedy assignment with constraints
        # 3. LLM re-shuffle for variety/reuse balance
        # 4. Per-recipe personalized notes (LLM)
        # 5. Compute scores
        ...
```

### 6.3 ShoppingListBuilder (real)

```python
# cooksense-core/cooksense_core/shopping_list_builder.py
"""Proprietary shopping list builder with quantity consolidation."""


class ShoppingListBuilder:
    def __init__(self, anthropic_client) -> None:
        self._anthropic = anthropic_client

    def build(
        self,
        plan_recipes: list[dict],
        pantry_ingredients: list[str],
        language: str = "en",
    ) -> dict:
        # 1. Collect all ingredients across recipes
        # 2. Subtract pantry (normalized comparison)
        # 3. LLM call to consolidate quantities and categorize
        # 4. Return structured list
        ...
```

### 6.4 Stub equivalents in public repo

`backend/stub/shopping_list_builder.py`:

```python
class ShoppingListBuilder:
    """Stub: flat list of ingredients minus pantry, generic quantities."""

    def build(
        self,
        plan_recipes: list[dict],
        pantry_ingredients: list[str],
        language: str = "en",
    ) -> dict:
        all_ingredients: set[str] = set()
        for recipe in plan_recipes:
            for ing in recipe.get("ingredients", []):
                all_ingredients.add(ing.lower())

        pantry_normalized = {p.lower() for p in pantry_ingredients}
        needed = all_ingredients - pantry_normalized

        items = [
            {
                "ingredient": ing,
                "ingredient_es": ing,  # No translation in stub
                "estimated_quantity": "some",
                "category": "other",
                "needed_for": ["unknown"],
            }
            for ing in sorted(needed)
        ]
        return {"items": items, "total_items": len(items)}
```

### 6.5 Open core wiring

`backend/api/deps.py` extended:

```python
try:
    from cooksense_core import (
        IngredientReasoner,
        MealPlanner,
        PersonalizedDescriber,
        QAResponder,
        RecipeRanker,
        ShoppingListBuilder,
        VisionExtractor,
    )
    _CORE_MODE = "proprietary"
except ImportError:
    from stub import (
        IngredientReasoner,
        MealPlanner,
        PersonalizedDescriber,
        QAResponder,
        RecipeRanker,
        ShoppingListBuilder,
        VisionExtractor,
    )
    _CORE_MODE = "stub"
```

---

## 7. Pydantic Models

### 7.1 `api/models/meal_plan.py`

```python
"""Meal plan request/response models."""

from datetime import datetime
from pydantic import BaseModel, Field


class MealRecipeSummary(BaseModel):
    id: str
    title: str
    estimated_time_minutes: int = Field(ge=1)
    match_percentage: float = Field(ge=0.0, le=1.0)
    ingredients_summary: list[str]
    personalized_note: str


class MealSlot(BaseModel):
    slot: str = Field(pattern="^(breakfast|lunch|dinner)$")
    recipe: MealRecipeSummary


class MealDay(BaseModel):
    day_number: int = Field(ge=1, le=3)
    meals: list[MealSlot] = Field(min_length=3, max_length=3)


class MealPlanRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1)
    days: int = Field(default=3, ge=3, le=3)  # Fixed at 3 in V1
    meals_per_day: list[str] = Field(
        default=["breakfast", "lunch", "dinner"], min_length=3, max_length=3
    )


class MealPlanResponse(BaseModel):
    plan_id: str
    user_id: str
    language: str
    created_at: datetime
    days: list[MealDay] = Field(min_length=3, max_length=3)
    ingredient_reuse_score: float = Field(ge=0.0, le=1.0)
    variety_score: float = Field(ge=0.0, le=1.0)
    macro_alignment_score: float = Field(ge=0.0, le=1.0)
    from_cache: bool
```

### 7.2 `api/models/shopping.py`

```python
"""Shopping list response models."""

from pydantic import BaseModel, Field


class ShoppingItem(BaseModel):
    ingredient: str
    ingredient_es: str
    estimated_quantity: str
    category: str = Field(
        pattern="^(vegetable|fruit|protein|grain|dairy|oil|herb|spice|condiment|other)$"
    )
    needed_for: list[str]  # recipe_ids


class ShoppingListResponse(BaseModel):
    plan_id: str
    items: list[ShoppingItem]
    total_items: int = Field(ge=0)
    language: str
```

---

## 8. Test Strategy — Phase 3

### 8.1 Categories

- **Unit tests**: pydantic validation, repository methods with in-memory SQLite
- **Integration tests**: full FastAPI flow with TestClient, mocked LLM, ChromaDB ephemeral, SQLite session, sample recipes corpus

No real Anthropic API calls. All `cooksense-core` interactions in tests use the stub.

### 8.2 Tests by file

**`tests/api/test_meal_plan_generate.py`:**

```
test_post_generate_with_valid_request_returns_201
test_post_generate_response_has_plan_id
test_post_generate_response_has_3_days
test_post_generate_each_day_has_3_meal_slots
test_post_generate_meal_slots_are_breakfast_lunch_dinner
test_post_generate_persists_plan_in_db
test_post_generate_persists_recipes_with_plan
test_post_generate_with_empty_ingredients_returns_400
test_post_generate_with_days_other_than_3_returns_400
test_post_generate_with_invalid_meal_slots_returns_400
test_post_generate_without_profile_returns_400
test_post_generate_uses_profile_language_for_titles
test_post_generate_caches_repeat_request
test_post_generate_returns_from_cache_true_on_repeat
test_post_generate_increments_user_daily_usage
test_post_generate_returns_429_when_daily_limit_hit
test_post_generate_returns_503_when_planner_fails
test_post_generate_includes_ingredient_reuse_score
test_post_generate_includes_variety_score
test_post_generate_includes_macro_alignment_score
test_post_generate_personalized_note_in_user_language
```

**`tests/api/test_meal_plan_shopping.py`:**

```
test_post_shopping_with_valid_plan_returns_200
test_post_shopping_response_has_items_array
test_post_shopping_response_has_total_items
test_post_shopping_excludes_pantry_ingredients
test_post_shopping_each_item_has_required_fields
test_post_shopping_categories_valid_for_each_item
test_post_shopping_with_unknown_plan_id_returns_404
test_post_shopping_with_other_users_plan_returns_403
test_post_shopping_in_spanish_profile_returns_spanish_ingredients
test_post_shopping_includes_needed_for_recipe_ids
test_post_shopping_handles_empty_pantry
test_post_shopping_handles_all_ingredients_in_pantry
```

**`tests/infrastructure/test_meal_plan_repository.py`:**

```
test_save_persists_plan_and_recipes
test_save_returns_plan_id
test_get_by_plan_id_returns_plan_when_exists
test_get_by_plan_id_returns_none_when_missing
test_get_recipes_for_plan_returns_in_order_by_day_and_slot
test_is_owner_returns_true_for_owning_user
test_is_owner_returns_false_for_other_user
test_is_owner_returns_false_for_missing_plan
test_cascade_delete_recipes_when_plan_deleted
```

**`tests/stub/test_meal_planner.py`:**

```
test_meal_planner_returns_3_days
test_meal_planner_each_day_has_3_meals
test_meal_planner_assigns_recipes_to_slots
test_meal_planner_with_empty_candidates_returns_placeholder_plan
test_meal_planner_returns_neutral_scores
test_meal_planner_does_not_optimize_reuse
test_meal_planner_does_not_optimize_variety
```

**`tests/stub/test_shopping_list_builder.py`:**

```
test_builder_returns_items_minus_pantry
test_builder_handles_empty_recipes
test_builder_handles_empty_pantry
test_builder_handles_all_pantry_match
test_builder_returns_generic_quantities
test_builder_returns_other_category_for_all
test_builder_normalizes_case_for_pantry_comparison
```

### 8.3 Test fixtures

Sample meal plan fixture (`tests/fixtures/sample_plan.json`) for repository round-trip tests. ~9 recipe records across 3 days.

---

## 9. Commit Convention — Phase 3

```
chore(infra): add MealPlan and MealPlanRecipe SQLAlchemy models
test(infra): add meal plan repository tests
feat(infra): implement meal plan repository with save and get
chore(infra): add cascade delete for meal plan recipes
chore(api): add meal plan pydantic models with validation
chore(api): add shopping list pydantic models
test(api): add meal plan endpoint validation tests
chore(stub): add MealPlanner stub with random selection
test(stub): add meal planner stub tests
test(api): add meal plan generation happy path tests
feat(api): implement POST /api/meal-plan/generate endpoint
test(api): add meal plan persistence tests
feat(api): wire meal plan repository to generate endpoint
test(api): add meal plan caching tests
feat(api): add LLM cache integration to meal plan generation
test(api): add meal plan rate limit tests
feat(api): add 1-plan daily limit per user
chore(stub): add ShoppingListBuilder stub with simple subtraction
test(stub): add shopping list builder stub tests
test(api): add shopping list endpoint validation tests
feat(api): implement POST /api/meal-plan/{plan_id}/shopping endpoint
test(api): add shopping list ownership tests
feat(api): enforce plan ownership in shopping endpoint
test(api): add shopping list bilingual tests
docs(api): document meal plan and shopping endpoints in OpenAPI
chore(api): wire MealPlanner and ShoppingListBuilder to deps via try/except
docs: add Phase 3 progress note to backend README
```

~28 commits expected.

---

## 10. What NOT to Do in Phase 3

- **Do not** support `days` other than 3. Validation rejects.
- **Do not** support custom meal slots. V1 is breakfast/lunch/dinner only.
- **Do not** add a "delete plan" endpoint. V1 plans are immutable.
- **Do not** add an "edit plan" endpoint. New plan = new ID.
- **Do not** persist shopping lists separately. Derive on demand.
- **Do not** implement constraint solvers in pure Python (ILP, SAT). Greedy + LLM re-shuffle is enough for V1.
- **Do not** add real-time updates (WebSocket, SSE). REST only.
- **Do not** add export-to-PDF, export-to-Trello, or any third-party integrations. V1 is API only.
- **Do not** add macro tracking or nutrition recomputation. Use existing recipe metadata.
- **Do not** add user-collaborative plans (sharing, comments). V1 is single-user.
- **Do not** add scheduled plan generation (e.g., "every Sunday auto-plan"). V1 is on-demand.
- **Do not** modify Phase 0-2 code beyond agreed extensions in `deps.py` and `models.py`.
- **Do not** call real Anthropic API in tests.
- **Do not** add frontend hints, dietary substitution suggestions, or "alternative recipes" in plan response. Single recipe per slot.
- **Do not** add seasonal logic (e.g., "winter recipes in winter"). Date-blind.

---

## 11. Acceptance Criteria for Phase 3 Completion

- [ ] `pytest` returns green with 130+ tests (100 from Phase 2 + ~30 from Phase 3)
- [ ] Phase 0-2 code unchanged in this PR's diff
- [ ] Two new endpoints reachable: `POST /api/meal-plan/generate` and `POST /api/meal-plan/{plan_id}/shopping`
- [ ] MealPlan and MealPlanRecipe persist correctly in DB (round-trip test passes)
- [ ] Plan ownership enforced (403 for cross-user access)
- [ ] Daily rate limit: 1 plan per user
- [ ] Plans cached by ingredient + profile signature
- [ ] Bilingual responses (Spanish/English) per profile language
- [ ] Stub `MealPlanner` returns 9 recipes from sample corpus, neutral scores
- [ ] Stub `ShoppingListBuilder` does subtraction without LLM consolidation
- [ ] Real `cooksense-core.MealPlanner` and `ShoppingListBuilder` exist with passing tests in private repo
- [ ] No real Anthropic API calls in tests
- [ ] `ruff check . && ruff format --check .` clean
- [ ] OpenAPI docs include meal plan and shopping endpoints
- [ ] Backend CI workflow green
- [ ] PR opened on `phase-3-meal-planning` against `main`, NOT merged

---

## 12. Branch & PR Workflow — Phase 3

1. `git checkout -b phase-3-meal-planning` from `main`
2. Commit on branch following Section 9
3. `git push -u origin phase-3-meal-planning`
4. `gh pr create --base main --head phase-3-meal-planning --title "Phase 3: Meal Planning + Shopping List"`
5. PR body: summary + acceptance criteria + "What's deferred to Phase 4": Android app
6. NOT merge.
7. Report and stop.

---

## 13. Handoff to Phase 4 (preview)

Phase 4 is the largest phase: the Android app consuming the entire backend.

- Onboarding flow (4-5 screens, Compose)
- Camera capture flow (CameraX -> ingredient extraction)
- Recipe search results screen
- Recipe detail + Q&A modal
- Meal plan screen with day tabs
- Shopping list screen
- Profile settings screen
- Network layer (Retrofit + OkHttp)
- Local persistence (DataStore)
- ViewModel tests + integration tests with MockWebServer
- Bilingual strings (ES/EN)

Phase 3 closes the backend story. Phase 4 wraps it in mobile.
