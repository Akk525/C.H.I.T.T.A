from __future__ import annotations

import math

from app.providers.base import (
    AccessibilityProvider,
    ElevationProvider,
    ElevationSample,
    LatLng,
    TerrainProvider,
    WindTimeseries,
    WindProvider,
)


def _hash01(lat: float, lng: float, salt: float) -> float:
    # Deterministic pseudo-random in [0,1) from lat/lng; stable for a point.
    x = math.sin((lat + 90.0) * 12.9898 + (lng + 180.0) * 78.233 + salt) * 43758.5453
    return x - math.floor(x)


class MockWindProvider(WindProvider):
    async def get_wind_score(self, p: LatLng) -> tuple[float, dict[str, object]]:
        # Higher in mid-latitudes + a bit of structured noise.
        lat_factor = 1.0 - abs(p.latitude) / 90.0
        mid_lat_boost = 1.0 - abs(lat_factor - 0.55) / 0.55
        noise = _hash01(p.latitude, p.longitude, 1.0)
        score = 45 + 45 * max(0.0, mid_lat_boost) + 10 * (noise - 0.5)
        return float(max(0.0, min(100.0, score))), {"source": "mock", "noise": noise}

    async def get_wind_timeseries(self, p: LatLng) -> tuple[WindTimeseries, dict[str, object]]:
        # Make a deterministic pseudo-series (daily, 365 samples).
        base_noise = _hash01(p.latitude, p.longitude, 10.0)
        mean = 4.5 + 4.5 * base_noise  # 4.5–9.0 m/s

        speeds: list[float] = []
        for day in range(365):
            n = _hash01(p.latitude + day * 0.01, p.longitude - day * 0.01, 11.0)
            speeds.append(max(0.1, mean + 2.0 * (n - 0.5)))

        ts: WindTimeseries = {
            "resolution": "daily",
            "periodStart": "mock-1y-start",
            "periodEnd": "mock-1y-end",
            "speeds_mps": speeds,
            "directions_deg": None,
            "mean_speed_mps": float(sum(speeds) / len(speeds)),
            "hub_height_m": 10,
        }
        return ts, {"source": "mock", "mean_speed_mps": ts["mean_speed_mps"], "count": len(speeds)}


class MockElevationProvider(ElevationProvider):
    async def get_elevation_m(self, p: LatLng) -> tuple[float, dict[str, object]]:
        noise = _hash01(p.latitude, p.longitude, 2.0)
        # Roughly 0–3200m. (Just a plausible range for MVP.)
        elev = 40 + 3200 * (noise**1.35)
        return float(elev), {"source": "mock", "noise": noise}

    async def get_elevation_samples(
        self, p: LatLng, *, radius_m: float, sample_count: int
    ) -> tuple[list[ElevationSample], dict[str, object]]:
        # Deterministic ring samples around the point; no geo-accurate conversion needed for mock.
        samples: list[ElevationSample] = []
        for i in range(max(4, sample_count)):
            n = _hash01(p.latitude, p.longitude, 20.0 + i)
            samples.append(
                {
                    "latitude": p.latitude + (n - 0.5) * 0.01,
                    "longitude": p.longitude + (_hash01(p.latitude, p.longitude, 30.0 + i) - 0.5) * 0.01,
                    "elevation_m": 40 + 3200 * (n**1.35),
                }
            )
        return samples, {
            "source": "mock",
            "radius_m": radius_m,
            "sample_count": len(samples),
        }


class MockTerrainProvider(TerrainProvider):
    async def get_terrain_complexity(self, p: LatLng) -> tuple[float, dict[str, object]]:
        n1 = _hash01(p.latitude, p.longitude, 3.1)
        n2 = _hash01(p.latitude, p.longitude, 3.9)
        complexity = 0.15 + 1.85 * abs(n1 - n2)  # ~0.15–2.0
        return float(complexity), {"source": "mock", "n1": n1, "n2": n2}


class MockAccessibilityProvider(AccessibilityProvider):
    async def get_accessibility_score(self, p: LatLng) -> tuple[float, dict[str, object]]:
        # Penalize very rugged / very high lat a bit; add deterministic noise.
        lat_penalty = abs(p.latitude) / 90.0
        noise = _hash01(p.latitude, p.longitude, 4.2)
        score = 70 - 25 * lat_penalty + 20 * (noise - 0.5)
        return float(max(0.0, min(100.0, score))), {"source": "mock", "noise": noise}

