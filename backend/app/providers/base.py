from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict


@dataclass(frozen=True)
class LatLng:
    latitude: float
    longitude: float


class WindTimeseries(TypedDict):
    resolution: Literal["hourly", "daily", "monthly"]
    periodStart: str
    periodEnd: str
    speeds_mps: list[float]
    directions_deg: list[float] | None
    mean_speed_mps: float


class ElevationSample(TypedDict):
    latitude: float
    longitude: float
    elevation_m: float | None


class WindProvider:
    async def get_wind_score(self, p: LatLng) -> tuple[float, dict[str, object]]:
        raise NotImplementedError

    async def get_wind_timeseries(
        self, p: LatLng
    ) -> tuple[WindTimeseries, dict[str, object]]:
        raise NotImplementedError


class ElevationProvider:
    async def get_elevation_m(self, p: LatLng) -> tuple[float, dict[str, object]]:
        raise NotImplementedError

    async def get_elevation_samples(
        self, p: LatLng, *, radius_m: float, sample_count: int
    ) -> tuple[list[ElevationSample], dict[str, object]]:
        raise NotImplementedError


class TerrainProvider:
    async def get_terrain_complexity(
        self, p: LatLng
    ) -> tuple[float, dict[str, object]]:
        raise NotImplementedError


class AccessibilityProvider:
    async def get_accessibility_score(
        self, p: LatLng
    ) -> tuple[float, dict[str, object]]:
        raise NotImplementedError

