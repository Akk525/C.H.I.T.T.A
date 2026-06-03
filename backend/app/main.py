from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.middleware import BodySizeLimitMiddleware
from app.models import site as _site  # noqa: F401
from app.models import site_analysis as _site_analysis  # noqa: F401
from app.models import saved_run as _saved_run  # noqa: F401

_log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    if not os.environ.get("CHITTA_API_KEY", "").strip():
        _log.warning(
            "CHITTA_API_KEY is not set — all API routes are unauthenticated. "
            "Set CHITTA_API_KEY in .env (backend) and NEXT_PUBLIC_CHITTA_API_KEY "
            "in .env.local (frontend) before exposing this service to the internet."
        )

    max_body_bytes = int(os.environ.get("CHITTA_MAX_BODY_BYTES", "2097152"))

    app = FastAPI(
        title="CHITTA API",
        version="0.1.0",
        description="Climate Heuristics & Intelligent Turbine Terrain Analysis (MVP).",
    )

    # Middleware is applied in reverse-addition order; BodySizeLimitMiddleware is
    # added last so it wraps everything and runs first on every incoming request.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_body_bytes)

    app.include_router(router)

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app


app = create_app()

