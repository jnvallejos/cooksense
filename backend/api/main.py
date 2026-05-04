"""CookSense API — FastAPI entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import healthz, meal_plan, profile, recipes, vision
from infrastructure.storage.postgres import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        init_db()
    except Exception:  # pragma: no cover - non-fatal in dev without DB
        logger.exception("init_db failed; profile endpoints inactive until DB is reachable")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CookSense API",
        version="0.1.0",
        description="Mobile-first recipe assistant powered by vision and RAG.",
        lifespan=_lifespan,
    )
    app.include_router(healthz.router)
    app.include_router(profile.router)
    app.include_router(recipes.router)
    app.include_router(vision.router)
    app.include_router(meal_plan.router)
    return app


app = create_app()
