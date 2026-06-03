from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


def _get_configured_key() -> str | None:
    """Read CHITTA_API_KEY from env on each call to pick up dotenv-loaded values."""
    key = os.environ.get("CHITTA_API_KEY", "").strip()
    return key or None


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> None:
    """FastAPI dependency: enforce shared API key on protected routes.

    When CHITTA_API_KEY is unset the dependency is a no-op (dev passthrough).
    A startup warning in main.py tells operators the backend is unauthenticated.
    """
    configured_key = _get_configured_key()
    if configured_key is None:
        return  # dev passthrough
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Api-Key header",
        )
    if not hmac.compare_digest(x_api_key.encode(), configured_key.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
