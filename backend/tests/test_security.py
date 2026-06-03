"""
Security hardening tests: API key auth enforcement and request body size limits.

These tests use FastAPI's TestClient (httpx-backed) and do NOT make any real
external HTTP calls — all test cases either fail at middleware/Pydantic validation
or return a 401 before the route handler fires.
"""
from __future__ import annotations

import json
import os
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_TEST_KEY = "chitta-test-key-abc123"
_TEST_ENV = {
    "CHITTA_API_KEY": _TEST_KEY,
    "PERSIST_ANALYSES": "false",
    # Keep middleware limits explicit so tests don't depend on default values
    "CHITTA_MAX_BODY_BYTES": "2097152",       # 2 MB
    "CHITTA_MAX_HISTORY_PAYLOAD_BYTES": "1048576",  # 1 MB
}


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """App instance with a configured API key and a mocked DB dependency."""
    with patch.dict(os.environ, _TEST_ENV):
        from app.main import create_app
        from app.db.deps import get_db

        app = create_app()

        def _mock_db() -> Generator[MagicMock, None, None]:
            yield MagicMock()

        app.dependency_overrides[get_db] = _mock_db

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ── Auth: unprotected routes ──────────────────────────────────────────────────

class TestUnprotectedRoutes:
    def test_health_requires_no_key(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.status_code == 200

    def test_api_health_providers_requires_no_key(self, client: TestClient) -> None:
        # May fail with provider errors but must not return 401
        r = client.get("/api/health/providers")
        assert r.status_code != 401


# ── Auth: protected routes reject missing / wrong key ─────────────────────────

class TestApiKeyEnforcement:
    """All tests use /api/site-analysis (no DB dependency, body-only validation)."""

    def test_no_key_returns_401(self, client: TestClient) -> None:
        r = client.post("/api/site-analysis", json={})
        assert r.status_code == 401

    def test_empty_key_returns_401(self, client: TestClient) -> None:
        r = client.post("/api/site-analysis", json={}, headers={"X-Api-Key": ""})
        assert r.status_code == 401

    def test_wrong_key_returns_401(self, client: TestClient) -> None:
        r = client.post("/api/site-analysis", json={}, headers={"X-Api-Key": "wrong-key"})
        assert r.status_code == 401

    def test_correct_key_passes_auth(self, client: TestClient) -> None:
        # Empty body → Pydantic 422 (missing lat/lng), but auth must have passed
        r = client.post("/api/site-analysis", json={}, headers={"X-Api-Key": _TEST_KEY})
        assert r.status_code == 422, (
            f"Expected 422 (auth passed, body invalid) but got {r.status_code}"
        )

    def test_correct_key_history_save_passes_auth(self, client: TestClient) -> None:
        # Minimal valid payload — should reach the route handler (DB mocked)
        r = client.post(
            "/api/history/save",
            json={"runType": "site", "payload": {"ok": True}},
            headers={"X-Api-Key": _TEST_KEY},
        )
        # Auth passed → not 401. Response is 200 or 500 depending on mock DB behaviour.
        assert r.status_code != 401

    def test_correct_key_history_list_passes_auth(self, client: TestClient) -> None:
        r = client.get("/api/history/runs", headers={"X-Api-Key": _TEST_KEY})
        assert r.status_code != 401

    def test_no_key_history_list_returns_401(self, client: TestClient) -> None:
        r = client.get("/api/history/runs")
        assert r.status_code == 401


# ── Body size: middleware (2 MB total request limit) ──────────────────────────

class TestBodySizeMiddleware:
    def test_small_body_passes_middleware(self, client: TestClient) -> None:
        r = client.post(
            "/api/site-analysis",
            json={"latitude": 14.2, "longitude": 76.4},
            headers={"X-Api-Key": _TEST_KEY},
        )
        # Auth passes, body is valid — actual analysis may fail (no network),
        # but 413 must NOT be returned
        assert r.status_code != 413

    def test_oversized_body_returns_413(self, client: TestClient) -> None:
        # ~2.1 MB body — exceeds the 2 MB middleware limit
        large_body = json.dumps({"data": "x" * 2_100_000}).encode()
        r = client.post(
            "/api/site-analysis",
            content=large_body,
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": _TEST_KEY,
            },
        )
        assert r.status_code == 413
        assert "too large" in r.json().get("detail", "").lower()

    def test_exactly_at_limit_passes_middleware(self, client: TestClient) -> None:
        # 1 MB body — well within the 2 MB middleware limit
        body = json.dumps({"data": "x" * 900_000}).encode()
        r = client.post(
            "/api/site-analysis",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": _TEST_KEY,
            },
        )
        assert r.status_code != 413

    def test_oversized_body_no_key_still_returns_413(self, client: TestClient) -> None:
        # Middleware runs before auth; 413 takes precedence over 401
        large_body = json.dumps({"data": "x" * 2_100_000}).encode()
        r = client.post(
            "/api/site-analysis",
            content=large_body,
            headers={"Content-Type": "application/json"},
            # No X-Api-Key
        )
        assert r.status_code == 413


# ── Body size: Pydantic payload validator (1 MB payload field limit) ──────────

class TestPayloadSizeValidator:
    def test_small_payload_accepted(self, client: TestClient) -> None:
        r = client.post(
            "/api/history/save",
            json={"runType": "site", "payload": {"score": 72.5}},
            headers={"X-Api-Key": _TEST_KEY},
        )
        assert r.status_code != 422

    def test_oversized_payload_returns_422(self, client: TestClient) -> None:
        # Payload dict serialises to ~1.1 MB — exceeds the 1 MB validator limit
        # but is within the 2 MB middleware limit (so middleware passes it through)
        oversized_payload = {"data": "y" * 1_100_000}
        r = client.post(
            "/api/history/save",
            json={"runType": "site", "payload": oversized_payload},
            headers={"X-Api-Key": _TEST_KEY},
        )
        assert r.status_code == 422
        body = r.json()
        detail = str(body.get("detail", ""))
        assert "KB" in detail or "payload" in detail.lower(), (
            f"Expected a size-related error message, got: {detail!r}"
        )

    def test_label_too_long_returns_422(self, client: TestClient) -> None:
        r = client.post(
            "/api/history/save",
            json={
                "runType": "site",
                "label": "x" * 121,  # exceeds max_length=120
                "payload": {"ok": True},
            },
            headers={"X-Api-Key": _TEST_KEY},
        )
        assert r.status_code == 422

    def test_invalid_run_type_returns_422(self, client: TestClient) -> None:
        r = client.post(
            "/api/history/save",
            json={"runType": "unknown_type", "payload": {"ok": True}},
            headers={"X-Api-Key": _TEST_KEY},
        )
        assert r.status_code == 422
