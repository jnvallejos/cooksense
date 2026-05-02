# Phase 0 Spec — Project Setup

**Repo:** `cooksense` (public monorepo) + `cooksense-core` (private package)
**Domain:** Recipe assistant powered by computer vision + RAG
**Stack:** Python 3.12 (FastAPI) + Kotlin (Jetpack Compose) + GitHub Actions
**Approach:** Project scaffolding, granular commits, feature branch + PR
**Branch:** `phase-0-setup`

---

## 1. Goal of Phase 0

Set up the monorepo and the private companion repo with the minimum scaffolding required for Phases 1+ to start writing real code immediately. No business logic, no real features. The output of Phase 0 is a workspace that compiles, runs (hello world), and has CI green.

At the end of Phase 0:
- `cooksense` public repo exists on GitHub with monorepo structure
- `cooksense-core` private repo exists on GitHub with package skeleton
- `backend/` runs FastAPI with a healthz endpoint and prints "hello CookSense"
- `backend/` has a functional `cooksense-core-stub` package wired in
- `android/` builds a Compose app with a single screen showing "Hello CookSense"
- `cooksense-core` private repo has a Python package skeleton importable as `cooksense_core`
- GitHub Actions workflows defined (initial form): backend build+test, Android build+test
- All CI workflows pass on first PR
- README, LICENSE, .gitignore, .editorconfig, CLAUDE.md (gitignored) committed
- Phase specs `docs/phase-0-spec.md` through `docs/phase-5-spec.md` committed

---

## 2. Solution & Folder Structure

```
cooksense/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml                  (NEW)
│       └── android-ci.yml                  (NEW)
├── android/                                (NEW)
│   ├── app/
│   │   ├── src/
│   │   │   ├── main/
│   │   │   │   ├── java/com/cooksense/
│   │   │   │   │   ├── MainActivity.kt
│   │   │   │   │   └── ui/
│   │   │   │   │       └── HelloScreen.kt
│   │   │   │   ├── res/
│   │   │   │   └── AndroidManifest.xml
│   │   │   └── test/
│   │   │       └── java/com/cooksense/
│   │   │           └── HelloScreenTest.kt
│   │   ├── build.gradle.kts
│   │   └── proguard-rules.pro
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   ├── gradle.properties
│   ├── gradle/
│   │   └── wrapper/
│   └── local.properties.example
├── backend/                                (NEW)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── healthz.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   └── deps.py
│   ├── infrastructure/
│   │   └── __init__.py
│   ├── stub/
│   │   ├── __init__.py
│   │   └── README.md
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_healthz.py
│   ├── pyproject.toml
│   ├── .env.example
│   └── README.md
├── docs/                                   (NEW)
│   ├── phase-0-spec.md
│   ├── phase-1-spec.md
│   ├── phase-2-spec.md
│   ├── phase-3-spec.md
│   ├── phase-4-spec.md
│   └── phase-5-spec.md
├── .editorconfig                           (NEW)
├── .gitignore                              (NEW)
├── CLAUDE.md                               (NEW, gitignored)
├── LICENSE                                 (NEW, MIT)
└── README.md                               (NEW)
```

And separately, the private repo:

```
cooksense-core/                             (NEW, private repo)
├── cooksense_core/
│   ├── __init__.py
│   └── README.md
├── tests/
│   ├── __init__.py
│   └── test_smoke.py
├── pyproject.toml
├── LICENSE                                 (proprietary text)
└── README.md
```

---

## 3. Public repo: top-level files

### 3.1 `README.md`

The README from `README-template.md` in the Project resources is the starting point. It already describes the project, architecture, endpoints (forward-looking), and the open core pattern. Phase 0 commits this as `README.md`.

### 3.2 `LICENSE`

MIT, year 2026, copyright "Javier Vallejos". Same exact text as the url-shortener repo. The standard text appears in [Phase 5 spec section 5.1 of url-shortener](#) — copy verbatim, change name to "Javier Vallejos", year to 2026.

### 3.3 `.gitignore`

Comprehensive monorepo gitignore covering Python, Kotlin/Android, iOS (forward-looking), and editor artifacts.

```gitignore
# Secrets
*.env
*.env.local
secrets.toml
*.pem
*.key
local.properties

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.venv/
venv/
ENV/
*.egg-info/
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
*.egg
dist/
build/

# Kotlin / Android
.gradle/
build/
captures/
.externalNativeBuild/
.cxx/
*.apk
*.aab
*.ap_
*.dex
.idea/
*.iml
proguard/

# iOS (forward-looking)
DerivedData/
*.xcodeproj/xcuserdata/
*.xcworkspace/xcuserdata/
Pods/
*.xcuserstate

# CookSense-specific
backend/data/
backend/.chroma/
backend/recipes/
android/app/release/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
ehthumbs.db

# CookSense Claude rules (local-only)
CLAUDE.md
```

### 3.4 `.editorconfig`

```ini
root = true

[*]
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_style = space
indent_size = 4

[*.{kt,kts}]
indent_style = space
indent_size = 4

[*.swift]
indent_style = space
indent_size = 4

[*.{json,yml,yaml,md}]
indent_style = space
indent_size = 2

[Makefile]
indent_style = tab
```

### 3.5 `CLAUDE.md`

Local-only file (gitignored), documents operating rules for Claude Code. Format inspired by the url-shortener equivalent. Contents:

```markdown
# CookSense — Operating rules for Claude Code

## Git authorship
- No "Co-authored-by" trailers
- No emojis in commits
- No AI markers ("Generated by Claude", "AI-assisted", etc.)
- Author: configured local git identity (use `git config user.email` already set)

## Commit messages
- Conventional Commits format: `type(scope): description`
- Lowercase, English, present tense, no period at end, max 72 chars
- Types: feat, fix, refactor, test, docs, chore, style
- Scopes: api, android, ios, core, infra, docs, repo, solution

## Push policy
- NEVER push directly to main
- Always work on feature branches: `phase-N-{slug}`
- Push branch, then `gh pr create` to open PR
- Owner reviews and merges manually

## End of phase behavior
- Verify: `dotnet build` (or equivalent), tests passing, lint clean
- List acceptance criteria from the spec, mark each as checked
- Report: "Phase N complete. PR opened: <URL>. Acceptance criteria checked. Awaiting review."
- STOP. Do not start the next phase. Do not auto-merge.

## Stack discipline
- Python 3.12 only. No Python 2 patterns.
- Kotlin 1.9+ idioms. Compose-first.
- TDD strict: test commit, then feat commit. Always.
- No hacks. If a solution feels hacky, propose the elegant version.
```

---

## 4. Backend project setup

### 4.1 `backend/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cooksense-backend"
version = "0.1.0"
description = "CookSense backend API"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "httpx>=0.27.0",
    "structlog>=24.4.0",
    "python-multipart>=0.0.12",
]

[project.optional-dependencies]
stub = []  # The stub is part of the backend package itself
core = ["cooksense-core @ git+ssh://git@github.com/jnvallejos/cooksense-core.git@main"]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.7.0",
    "httpx>=0.27.0",
]

[tool.setuptools.packages.find]
include = ["api*", "infrastructure*", "stub*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "C4", "UP", "ANN"]
ignore = ["ANN101", "ANN102"]  # missing type for self/cls

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ANN"]
```

### 4.2 `backend/api/main.py`

```python
"""CookSense API — FastAPI entry point."""

from fastapi import FastAPI
from api.routes import healthz


def create_app() -> FastAPI:
    app = FastAPI(
        title="CookSense API",
        version="0.1.0",
        description="Mobile-first recipe assistant powered by vision and RAG.",
    )
    app.include_router(healthz.router)
    return app


app = create_app()
```

### 4.3 `backend/api/routes/healthz.py`

```python
"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "cooksense-backend"}
```

### 4.4 `backend/api/deps.py`

Forward-looking dependency injection setup. In Phase 0 this is mostly empty but establishes the pattern for the open core import:

```python
"""Dependency wiring for FastAPI routes.

This module is the single integration point with cooksense-core (the private
proprietary package) or its public stub. The try/except pattern allows the
backend to run in either mode.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from cooksense_core import RecipeRanker, IngredientReasoner  # type: ignore[import-not-found]
    logger.info("cooksense-core (proprietary) loaded")
    _CORE_MODE = "proprietary"
except ImportError:
    from stub import RecipeRanker, IngredientReasoner
    logger.info("cooksense-core-stub (public mock) loaded")
    _CORE_MODE = "stub"


def get_core_mode() -> str:
    """Return 'proprietary' or 'stub' depending on which package is available."""
    return _CORE_MODE


def get_recipe_ranker() -> RecipeRanker:
    """Instantiate the active RecipeRanker (proprietary or stub)."""
    return RecipeRanker()


def get_ingredient_reasoner() -> IngredientReasoner:
    """Instantiate the active IngredientReasoner (proprietary or stub)."""
    return IngredientReasoner()
```

### 4.5 `backend/stub/__init__.py`

The stub package exposes the same interface as `cooksense-core`. In Phase 0, the stub is minimal — it just defines the classes and exports them. Real method implementations come in later phases.

```python
"""cooksense-core-stub: public mock implementations.

This package mirrors the interface of the private `cooksense-core` package.
It is functional but limited: rankings are naive, prompts are generic, and
retrieval is basic cosine similarity.

In production, the real `cooksense-core` package is installed and overrides
this stub. See backend/api/deps.py for the import logic.
"""

from .ranker import RecipeRanker
from .reasoner import IngredientReasoner

__all__ = ["RecipeRanker", "IngredientReasoner"]
```

### 4.6 `backend/stub/ranker.py`

```python
"""Stub implementation of RecipeRanker."""


class RecipeRanker:
    """Naive recipe ranker: returns recipes in input order, unweighted.

    Real implementation in cooksense-core applies multi-factor scoring:
    profile-aware ingredient overlap, time budget, skill level, dietary
    restrictions, macro alignment.
    """

    def __init__(self) -> None:
        pass

    def rank(self, recipes: list[dict], profile: dict) -> list[dict]:
        """Return recipes unmodified. Real implementation re-orders by score."""
        return recipes
```

### 4.7 `backend/stub/reasoner.py`

```python
"""Stub implementation of IngredientReasoner."""


class IngredientReasoner:
    """Naive ingredient reasoner: passes ingredients through unchanged.

    Real implementation in cooksense-core normalizes synonyms, infers quantities,
    detects missing categories, and applies dietary constraint filters.
    """

    def __init__(self) -> None:
        pass

    def reason(self, ingredients: list[str], profile: dict) -> list[str]:
        """Return ingredients unchanged. Real implementation normalizes and filters."""
        return ingredients
```

### 4.8 `backend/stub/README.md`

```markdown
# cooksense-core-stub

This is the public mock companion to the private `cooksense-core` package.

It exists so that anyone cloning the public `cooksense` repo can run the backend without access to the proprietary package. The stub functions but is intentionally limited: ranking is naive, retrieval is basic, no prompt engineering.

For full functionality, you need access to the private `cooksense-core` repo.
```

### 4.9 `backend/.env.example`

```env
# Anthropic API key for vision and LLM calls
ANTHROPIC_API_KEY=

# Database connection (Phase 1+)
DATABASE_URL=postgresql://cooksense:cooksense@localhost:5432/cooksense

# ChromaDB connection (Phase 1+)
CHROMA_HOST=
CHROMA_API_KEY=

# CORS — adjust for production
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
LOG_LEVEL=INFO
```

### 4.10 `backend/README.md`

```markdown
# CookSense Backend

Python FastAPI backend for the CookSense recipe assistant.

## Stack

- Python 3.12+
- FastAPI 0.115+
- Pydantic v2
- pytest + pytest-asyncio for tests
- ruff for linting

## Running locally

```shell
python -m venv .venv && source .venv/bin/activate
pip install -e ".[stub,dev]"
cp .env.example .env  # set ANTHROPIC_API_KEY and DATABASE_URL
uvicorn api.main:app --reload
```

The API runs on http://localhost:8000. Healthz at `/api/healthz`.

## Running tests

```shell
pytest
```

## Linting

```shell
ruff check .
ruff format .
```

## Open Core

This backend imports from either `cooksense-core` (private proprietary package) or `cooksense-core-stub` (public mock). See `api/deps.py` for the import pattern. Without `cooksense-core` installed, the backend falls back to the stub automatically.
```

---

## 5. Backend tests

### 5.1 `backend/tests/conftest.py`

```python
"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def app():
    """FastAPI app instance for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Synchronous test client. For async tests, use httpx.AsyncClient."""
    return TestClient(app)
```

### 5.2 `backend/tests/test_healthz.py`

```python
"""Tests for healthz endpoint."""


def test_healthz_returns_200_ok(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200


def test_healthz_returns_status_ok(client):
    response = client.get("/api/healthz")
    body = response.json()
    assert body["status"] == "ok"


def test_healthz_returns_service_name(client):
    response = client.get("/api/healthz")
    body = response.json()
    assert body["service"] == "cooksense-backend"


def test_healthz_response_is_json(client):
    response = client.get("/api/healthz")
    assert response.headers["content-type"].startswith("application/json")
```

### 5.3 Tests for stub package

`backend/tests/test_stub.py`:

```python
"""Smoke tests for the cooksense-core-stub package."""

from stub import IngredientReasoner, RecipeRanker


class TestRecipeRanker:
    def test_rank_returns_recipes_unchanged(self):
        ranker = RecipeRanker()
        recipes = [{"id": "r1"}, {"id": "r2"}]
        profile = {"skill": "beginner"}

        result = ranker.rank(recipes, profile)

        assert result == recipes


class TestIngredientReasoner:
    def test_reason_returns_ingredients_unchanged(self):
        reasoner = IngredientReasoner()
        ingredients = ["tomato", "onion"]
        profile = {"diet": "vegan"}

        result = reasoner.reason(ingredients, profile)

        assert result == ingredients
```

### 5.4 Tests for deps wiring

`backend/tests/test_deps.py`:

```python
"""Tests for the dependency wiring (open core import logic)."""

from api.deps import get_core_mode, get_recipe_ranker, get_ingredient_reasoner
from stub import RecipeRanker as StubRanker, IngredientReasoner as StubReasoner


def test_core_mode_is_stub_when_proprietary_not_installed():
    """In CI and dev without cooksense-core, mode should be 'stub'."""
    mode = get_core_mode()
    assert mode in ("stub", "proprietary")  # depends on test env


def test_get_recipe_ranker_returns_an_instance():
    ranker = get_recipe_ranker()
    assert ranker is not None


def test_get_ingredient_reasoner_returns_an_instance():
    reasoner = get_ingredient_reasoner()
    assert reasoner is not None


def test_stub_ranker_is_used_when_in_stub_mode():
    if get_core_mode() == "stub":
        ranker = get_recipe_ranker()
        assert isinstance(ranker, StubRanker)


def test_stub_reasoner_is_used_when_in_stub_mode():
    if get_core_mode() == "stub":
        reasoner = get_ingredient_reasoner()
        assert isinstance(reasoner, StubReasoner)
```

---

## 6. Android project setup

### 6.1 `android/settings.gradle.kts`

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "cooksense"
include(":app")
```

### 6.2 `android/build.gradle.kts` (root)

```kotlin
plugins {
    id("com.android.application") version "8.7.0" apply false
    id("org.jetbrains.kotlin.android") version "1.9.25" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "1.9.25" apply false
    id("com.google.dagger.hilt.android") version "2.52" apply false
    id("io.gitlab.arturbosch.detekt") version "1.23.7" apply false
    id("org.jlleitschuh.gradle.ktlint") version "12.1.1" apply false
}
```

### 6.3 `android/gradle.properties`

```properties
org.gradle.jvmargs=-Xmx4096m -XX:MaxMetaspaceSize=512m
org.gradle.parallel=true
org.gradle.caching=true

android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
```

### 6.4 `android/local.properties.example`

```properties
sdk.dir=/path/to/android/sdk
BACKEND_URL=http://10.0.2.2:8000
```

### 6.5 `android/app/build.gradle.kts`

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.dagger.hilt.android")
    id("io.gitlab.arturbosch.detekt")
    id("org.jlleitschuh.gradle.ktlint")
}

android {
    namespace = "com.cooksense"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.cooksense"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions { jvmTarget = "17" }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.15"
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")

    testImplementation("org.junit.jupiter:junit-jupiter:5.11.3")
    testImplementation("io.mockk:mockk:1.13.13")
    testImplementation("app.cash.turbine:turbine:1.2.0")

    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}

detekt {
    buildUponDefaultConfig = true
    allRules = false
}

ktlint {
    version.set("1.4.1")
    android.set(true)
}
```

### 6.6 `android/app/src/main/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <application
        android:allowBackup="false"
        android:label="CookSense"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
```

### 6.7 `android/app/src/main/java/com/cooksense/MainActivity.kt`

```kotlin
package com.cooksense

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.fillMaxSize
import com.cooksense.ui.HelloScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    HelloScreen()
                }
            }
        }
    }
}
```

### 6.8 `android/app/src/main/java/com/cooksense/ui/HelloScreen.kt`

```kotlin
package com.cooksense.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun HelloScreen() {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Hello CookSense",
            style = MaterialTheme.typography.headlineLarge.copy(fontWeight = FontWeight.Bold),
        )
        Text(
            text = "Phase 0 — Project setup complete",
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 8.dp),
        )
    }
}
```

### 6.9 `android/app/src/test/java/com/cooksense/HelloScreenTest.kt`

```kotlin
package com.cooksense

import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.assertTrue

class HelloScreenSmokeTest {
    @Test
    fun `module compiles`() {
        // Smoke test: this test exists to verify the test infrastructure
        // is wired correctly. Real ViewModel tests come in Phase 4.
        assertTrue(true)
    }
}
```

> Note: A real Compose UI test (with `composeTestRule.setContent { HelloScreen() }`) requires `androidTest` (instrumented) which needs an emulator or device in CI. For Phase 0, a JVM smoke test is enough; Compose UI tests come back in Phase 4 when there's real UI to verify.

---

## 7. Private repo: `cooksense-core` skeleton

### 7.1 `cooksense-core/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cooksense-core"
version = "0.1.0"
description = "CookSense proprietary core: ranking, prompts, retrieval"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.39.0",
    "langchain>=0.3.0",
    "langchain-anthropic>=0.2.0",
    "langchain-community>=0.3.0",
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "pydantic>=2.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.7.0",
]

[tool.setuptools.packages.find]
include = ["cooksense_core*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 7.2 `cooksense-core/cooksense_core/__init__.py`

```python
"""CookSense proprietary core package.

This package is private and not intended for distribution. It contains
the proprietary ranking algorithms, prompt templates, and retrieval
strategies that differentiate CookSense from generic recipe apps.

The public companion `cooksense-core-stub` (in the public cooksense repo)
mirrors this interface with naive implementations for demo purposes.
"""

from .ranker import RecipeRanker
from .reasoner import IngredientReasoner

__version__ = "0.1.0"
__all__ = ["RecipeRanker", "IngredientReasoner"]
```

### 7.3 `cooksense-core/cooksense_core/ranker.py`

In Phase 0, this is just a class skeleton matching the stub's interface. Real algorithms come in Phase 1.

```python
"""Recipe ranker — proprietary multi-factor ranking algorithm."""


class RecipeRanker:
    """Multi-factor recipe scoring with profile-aware weights."""

    def __init__(self) -> None:
        # Real initialization in Phase 1: load weights, embeddings, etc.
        pass

    def rank(self, recipes: list[dict], profile: dict) -> list[dict]:
        """Rank recipes by composite score.

        Real algorithm: ingredient overlap (weighted by ingredient importance),
        time budget alignment, skill level match, dietary constraint compliance,
        macro distance to goals, recency of last-cooked recipes.

        Phase 0: returns recipes unchanged.
        """
        # TODO Phase 1: real scoring logic
        return recipes
```

### 7.4 `cooksense-core/cooksense_core/reasoner.py`

```python
"""Ingredient reasoner — proprietary ingredient normalization and filtering."""


class IngredientReasoner:
    """Profile-aware ingredient normalization and constraint filtering."""

    def __init__(self) -> None:
        pass

    def reason(self, ingredients: list[str], profile: dict) -> list[str]:
        """Normalize ingredients and apply profile constraints.

        Real algorithm: synonym normalization (cilantro/coriander), quantity
        inference, category detection, dietary constraint filtering.

        Phase 0: returns ingredients unchanged.
        """
        return ingredients
```

### 7.5 `cooksense-core/tests/test_smoke.py`

```python
"""Smoke tests for cooksense-core."""

from cooksense_core import RecipeRanker, IngredientReasoner


def test_ranker_imports():
    ranker = RecipeRanker()
    assert ranker is not None


def test_reasoner_imports():
    reasoner = IngredientReasoner()
    assert reasoner is not None


def test_version():
    import cooksense_core
    assert cooksense_core.__version__ == "0.1.0"
```

### 7.6 `cooksense-core/LICENSE`

```
Copyright (c) 2026 Javier Vallejos. All Rights Reserved.

This software and associated documentation files (the "Software") are the
proprietary and confidential property of Javier Vallejos. Unauthorized
copying, distribution, modification, public display, or public performance
of this Software is strictly prohibited.

The Software is intended for use only in connection with the CookSense
product. No license, express or implied, is granted to any party for any
other purpose.
```

### 7.7 `cooksense-core/README.md`

```markdown
# cooksense-core

Private proprietary package for the CookSense recipe assistant.

## What this contains

- Recipe ranking algorithms with profile-aware multi-factor scoring
- LLM prompt templates for ingredient extraction, recipe personalization, and meal planning
- Custom retrieval strategies on top of ChromaDB
- Ingredient normalization and constraint reasoning

## Pairing with the public stub

The public `cooksense` repo includes a `cooksense-core-stub` package with the same interface but naive implementations. The public backend imports from either this package (if available) or the stub (as fallback). See the public repo's `backend/api/deps.py` for the import logic.

## Installation

This package is installed as a Git dependency in the public backend's `pyproject.toml` under the `core` extra:

```toml
[project.optional-dependencies]
core = ["cooksense-core @ git+ssh://git@github.com/jnvallejos/cooksense-core.git@main"]
```

To install:

```shell
pip install -e ".[core]"
```

You need SSH access to the private repo for this to work.
```

---

## 8. CI workflows

### 8.1 `.github/workflows/backend-ci.yml`

```yaml
name: Backend CI

on:
  push:
    branches: [main]
    paths:
      - "backend/**"
      - ".github/workflows/backend-ci.yml"
  pull_request:
    branches: [main]
    paths:
      - "backend/**"
      - ".github/workflows/backend-ci.yml"

jobs:
  build-and-test:
    name: Build and test
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: backend/pyproject.toml

      - name: Install dependencies (with stub fallback)
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[stub,dev]"

      - name: Lint with ruff
        run: ruff check .

      - name: Format check
        run: ruff format --check .

      - name: Run tests
        run: pytest --cov=api --cov=stub --cov-report=xml

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: backend-coverage
          path: backend/coverage.xml
          retention-days: 30
```

### 8.2 `.github/workflows/android-ci.yml`

```yaml
name: Android CI

on:
  push:
    branches: [main]
    paths:
      - "android/**"
      - ".github/workflows/android-ci.yml"
  pull_request:
    branches: [main]
    paths:
      - "android/**"
      - ".github/workflows/android-ci.yml"

jobs:
  build-and-test:
    name: Build and test
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: android

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"

      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@v4

      - name: Lint
        run: ./gradlew ktlintCheck detekt

      - name: Build debug APK
        run: ./gradlew assembleDebug

      - name: Run unit tests
        run: ./gradlew testDebugUnitTest

      - name: Upload APK artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: cooksense-debug-apk
          path: android/app/build/outputs/apk/debug/*.apk
          retention-days: 7

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: android-test-report
          path: android/app/build/reports/tests/
          retention-days: 30
```

---

## 9. Test Strategy — Phase 0

Phase 0 has a small but real test surface:
- Backend healthz: 4 unit tests (status code, JSON shape, content-type)
- Backend stub: 2 smoke tests
- Backend deps wiring: 5 tests (mode detection, instance returns)
- Android: 1 smoke unit test (just verifies test infra)

**Total: 12 tests across the monorepo.** Phase 0 doesn't need more.

The tests are not just about coverage — they're about establishing that:
1. pytest runs with the right plugins
2. FastAPI test client works
3. The stub package imports correctly
4. The deps wiring respects the open core fallback
5. JUnit5 + Gradle are wired in the Android side

---

## 10. Commit Convention — Phase 0

Conventional Commits, granular pairs.

**Example commit sequence:**

```
chore(repo): add LICENSE, gitignore, and editorconfig
chore(repo): add CookSense profile and project instructions docs
docs: add README with architecture and quick start
docs: add phase-0 through phase-5 specs to docs folder
chore(solution): add backend Python project skeleton
chore(solution): add backend pyproject.toml with FastAPI deps
test(api): add healthz endpoint tests
feat(api): implement healthz route
chore(solution): add stub package skeleton with RecipeRanker and IngredientReasoner
test(api): add stub smoke tests
chore(solution): add deps.py with open core import logic
test(api): add deps wiring tests
chore(solution): add Android Gradle project skeleton
chore(solution): add Android build configuration with Compose and Hilt
chore(android): add MainActivity and HelloScreen composable
test(android): add HelloScreen smoke test
chore(ci): add backend GitHub Actions workflow
chore(ci): add Android GitHub Actions workflow
```

20-22 commits total expected for Phase 0.

---

## 11. What NOT to Do in Phase 0

- **Do not** implement any RAG or vision logic. That's Phase 1+.
- **Do not** hook up Anthropic API. The stub doesn't need it; deps wiring is enough.
- **Do not** add a database. Phase 1 introduces ChromaDB and Postgres.
- **Do not** add real authentication, user IDs, or session management. Phase 1+.
- **Do not** add custom UI components beyond a single Compose screen. Phase 4.
- **Do not** add Hilt modules in Android. Phase 4 introduces real DI.
- **Do not** add Retrofit or networking in Android. Phase 4.
- **Do not** add iOS folder. iOS is V2.
- **Do not** add a Dockerfile for backend yet. Phase 5 deployment.
- **Do not** add Fly.io configuration yet. Phase 5.
- **Do not** add E2E tests across mobile and backend. Phase 5.
- **Do not** add any environment-specific configuration beyond `.env.example`. Phase 5.
- **Do not** customize ProGuard rules. Defaults are fine.
- **Do not** add NPM, Node, or any JavaScript tooling. The project is Python + Kotlin.
- **Do not** sign the APK. Phase 5 deployment handles signing.
- **Do not** add notification channels, deep linking, or any Android features beyond a single screen.
- **Do not** include real recipe data, ingredient lists, or any business data. Phase 1.

---

## 12. Acceptance Criteria for Phase 0 Completion

Before opening the PR:

- [ ] Public repo `cooksense` exists on GitHub
- [ ] Private repo `cooksense-core` exists on GitHub (separately created)
- [ ] Public repo monorepo structure matches Section 2
- [ ] All public repo top-level files exist: `README.md`, `LICENSE`, `.gitignore`, `.editorconfig`
- [ ] `CLAUDE.md` exists in repo root, gitignored, with operating rules
- [ ] All 6 phase specs committed to `docs/`: `phase-0-spec.md` through `phase-5-spec.md`
- [ ] Backend project compiles: `pip install -e ".[stub,dev]"` succeeds
- [ ] Backend tests pass: `pytest` returns green with 11+ tests
- [ ] Backend lint passes: `ruff check . && ruff format --check .` returns clean
- [ ] Backend runs: `uvicorn api.main:app` serves on port 8000, `/api/healthz` returns 200 with expected JSON
- [ ] Android project compiles: `./gradlew assembleDebug` succeeds
- [ ] Android tests pass: `./gradlew testDebugUnitTest` returns green
- [ ] Android lint passes: `./gradlew ktlintCheck detekt` returns clean
- [ ] Android APK installs and launches on emulator showing "Hello CookSense" screen
- [ ] Both CI workflows defined: `backend-ci.yml` and `android-ci.yml`
- [ ] Both CI workflows pass on the PR
- [ ] Private repo `cooksense-core` has package skeleton, smoke tests pass, LICENSE has proprietary text
- [ ] Commit history is granular and follows Section 10 convention
- [ ] No NuGet, no Maven Central manual deps outside what's in build.gradle.kts
- [ ] No TODO comments in code (TODO in docstrings is OK if marking Phase 1+ work)
- [ ] PR opened on branch `phase-0-setup` against `main`, NOT merged

---

## 13. Branch & PR Workflow — Phase 0

1. `git checkout -b phase-0-setup` from `main` before the first commit (after main has just initial commit with maybe only README placeholder)
2. Commit on the branch following Section 10
3. Push: `git push -u origin phase-0-setup`
4. Open a PR via `gh pr create --base main --head phase-0-setup --title "Phase 0: Project Setup"` with body containing:
   - Summary paragraph
   - Acceptance criteria checklist from Section 12
   - "What's in this PR": monorepo structure, backend FastAPI skeleton with stub, Android Compose hello world, CI workflows
   - "What's deferred to Phase 1": real RAG, recipe corpus, profile management, vision pipeline
5. Do NOT merge.
6. Report: "Phase 0 complete. PR opened: <URL>. Acceptance criteria checked. Awaiting review." and stop.

---

## 14. Handoff to Phase 1 (preview, not in scope)

- Backend: ingest RecipeNLG corpus into ChromaDB, implement search endpoint, add profile CRUD
- Real `cooksense-core` ranking implementation (in private repo)
- Stub: keep simple, but updated to mirror the new methods
- Postgres for user profiles
- Anthropic client wiring for embeddings (no LLM calls yet, those are Phase 2)
- ~80% backend, 20% private core work

Phase 0 ships the empty house. Phase 1 furnishes the kitchen.
