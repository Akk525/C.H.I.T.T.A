from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.models import site as _site  # noqa: F401
from app.models import site_analysis as _site_analysis  # noqa: F401


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="CHITTA API",
        version="0.1.0",
        description="Climate Heuristics & Intelligent Turbine Terrain Analysis (MVP).",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app


app = create_app()

