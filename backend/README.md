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
