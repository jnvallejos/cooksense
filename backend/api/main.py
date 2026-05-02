"""CookSense API — FastAPI entry point."""

from fastapi import FastAPI

from api.routes import healthz, profile, recipes


def create_app() -> FastAPI:
    app = FastAPI(
        title="CookSense API",
        version="0.1.0",
        description="Mobile-first recipe assistant powered by vision and RAG.",
    )
    app.include_router(healthz.router)
    app.include_router(profile.router)
    app.include_router(recipes.router)
    return app


app = create_app()
