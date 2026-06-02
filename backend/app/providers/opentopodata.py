from __future__ import annotations

import math
from typing import Any

import httpx

from app.providers.base import ElevationProvider, ElevationSample, LatLng
from app.services.cache import coord_cache_key, elevation_point_cache, elevation_samples_cache


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if s.lower() in {"nan", "none", ""}:
            return None
        return float(s)
    except Exception:
        return None


def _ring_points(p: LatLng, *, radius_m: float, sample_count: int) -> list[LatLng]:
    # Approx conversion meters->degrees (good enough for small radii).
    lat_deg_per_m = 1.0 / 111_320.0
    lon_deg_per_m = 1.0 / (111_320.0 * max(0.2, math.cos(math.radians(p.latitude))))

    pts: list[LatLng] = []
    n = max(4, sample_count)
    for i in range(n):
        theta = 2.0 * math.pi * (i / n)
        dlat = math.sin(theta) * radius_m * lat_deg_per_m
        dlon = math.cos(theta) * radius_m * lon_deg_per_m
        pts.append(LatLng(latitude=p.latitude + dlat, longitude=p.longitude + dlon))
    return pts


class OpenTopoDataElevationProvider(ElevationProvider):
    """
    OpenTopoData public API.

    Default dataset: `srtm90m` (global). Can be swapped later.
    """

    BASE_URL = "https://api.opentopodata.org/v1"

    def __init__(self, *, dataset: str = "srtm90m", timeout_s: float = 6.0):
        self._dataset = dataset
        self._timeout = httpx.Timeout(timeout_s, connect=timeout_s)

    async def get_elevation_m(self, p: LatLng) -> tuple[float, dict[str, object]]:
        cache_key = coord_cache_key(p.latitude, p.longitude)
        cached = elevation_point_cache.get(cache_key)
        if cached is not None:
            elev, dbg = cached
            return float(elev), {**dbg, "cacheHit": True}
        samples, dbg = await self.get_elevation_samples(p, radius_m=0, sample_count=1)
        elev = samples[0].get("elevation_m") if samples else None
        if elev is None:
            return 0.0, {**dbg, "warnings": ["No elevation for point"]}
        elevation_point_cache.set(cache_key, (float(elev), dbg))
        return float(elev), dbg

    async def get_elevation_samples(
        self, p: LatLng, *, radius_m: float, sample_count: int
    ) -> tuple[list[ElevationSample], dict[str, object]]:
        cache_key = f"{coord_cache_key(p.latitude, p.longitude)}:{radius_m}:{sample_count}"
        cached = elevation_samples_cache.get(cache_key)
        if cached is not None:
            samples, dbg = cached
            return samples, {**dbg, "cacheHit": True}  # type: ignore[misc]
        points = [p] if radius_m <= 0 else _ring_points(p, radius_m=radius_m, sample_count=sample_count)

        loc_str = "|".join(f"{pt.latitude:.6f},{pt.longitude:.6f}" for pt in points)
        url = f"{self.BASE_URL}/{self._dataset}"
        params = {"locations": loc_str}

        debug: dict[str, object] = {
            "provider": "opentopodata",
            "source": "opentopodata",
            "dataset": self._dataset,
            "radius_m": radius_m,
            "sample_count_requested": sample_count,
            "request": {"url": url, "params": {"locations": "…"}},
            "errors": [],
            "warnings": [],
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                res = await client.get(url, params=params)
                debug["httpStatus"] = res.status_code
                res.raise_for_status()
                payload = res.json()
            except Exception as e:
                debug["errors"] = [f"OpenTopoData request failed: {e!s}"]
                return [], debug

        results = payload.get("results")
        if not isinstance(results, list):
            debug["errors"] = ["OpenTopoData payload missing results[]"]
            return [], debug

        out: list[ElevationSample] = []
        for r in results:
            if not isinstance(r, dict):
                continue
            loc = r.get("location") or {}
            lat = _safe_float(loc.get("lat"))
            lng = _safe_float(loc.get("lng"))
            elev = _safe_float(r.get("elevation"))
            if lat is None or lng is None:
                continue
            out.append({"latitude": float(lat), "longitude": float(lng), "elevation_m": elev})

        debug["sampleCount"] = len(out)
        debug["elevations_m"] = [s["elevation_m"] for s in out]

        if not out:
            debug["warnings"] = ["No usable elevation samples; falling back to mock."]

        elevation_samples_cache.set(cache_key, (out, debug))
        return out, debug

