"""CookSense API — FastAPI entry point."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="CookSense API",
        version="0.1.0",
        description="Mobile-first recipe assistant powered by vision and RAG.",
    )
    return app


app = create_app()
