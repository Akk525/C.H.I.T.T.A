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
    hub_height_m: int  # height of the speeds_mps data (10, 50, or 100)


class MultiHeightWind(TypedDict):
    mean_10m_mps: float | None
    mean_50m_mps: float | None
    mean_100m_mps: float | None  # always None — WS100M not in RE/daily community
    power_density_w_m2: float | None  # derived at highest available height
    primary_height_m: int  # 50 when WS50M available, else 10


class ElevationSample(TypedDict):
    latitude: float
    longitude: float
    elevation_m: float | None


class InfrastructureData(TypedDict):
    nearest_road_m: float | None
    nearest_settlement_m: float | None
    nearest_powerline_m: float | None
    nearest_rail_m: float | None
    road_type: str | None  # highway tag value of the closest road
    settlement_count_15km: int  # proxy for population density


class LandCoverData(TypedDict):
    cover_class: str | None  # "forest"|"cropland"|"urban"|"wetland"|"barren"|"shrubland"|"grassland"
    permitting_risk: str  # "low"|"medium"|"high"
    source: str  # "osm"|"unknown"


class ProtectedAreaData(TypedDict):
    in_protected_area: bool
    nearest_pa_name: str | None
    nearest_pa_m: float | None
    biodiversity_risk: str  # "low"|"medium"|"high"


class WindProvider:
    async def get_wind_score(self, p: LatLng) -> tuple[float, dict[str, object]]:
        raise NotImplementedError

    async def get_wind_timeseries(
        self, p: LatLng
    ) -> tuple[WindTimeseries, dict[str, object]]:
        raise NotImplementedError

    async def get_multi_height_wind(
        self, p: LatLng
    ) -> tuple[MultiHeightWind, dict[str, object]]:
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


class InfrastructureProvider:
    async def get_infrastructure_data(
        self, p: LatLng
    ) -> tuple[InfrastructureData, dict[str, object]]:
        raise NotImplementedError


class LandCoverProvider:
    async def get_land_cover(
        self, p: LatLng
    ) -> tuple[LandCoverData, dict[str, object]]:
        raise NotImplementedError


class ProtectedAreaProvider:
    async def get_protected_area_risk(
        self, p: LatLng
    ) -> tuple[ProtectedAreaData, dict[str, object]]:
        raise NotImplementedError


class AccessibilityProvider:
    async def get_accessibility_score(
        self, p: LatLng
    ) -> tuple[float, dict[str, object]]:
        raise NotImplementedError

