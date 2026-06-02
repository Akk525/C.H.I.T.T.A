from __future__ import annotations

import math
from typing import Any

import httpx

from app.providers.base import (
    InfrastructureData,
    InfrastructureProvider,
    LatLng,
    LandCoverData,
    LandCoverProvider,
    ProtectedAreaData,
    ProtectedAreaProvider,
)
from app.services.cache import coord_cache_key, infrastructure_cache

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# OSM landuse/natural → our canonical cover class
_LANDUSE_MAP: dict[str, str] = {
    "forest": "forest",
    "farmland": "cropland",
    "farmyard": "cropland",
    "orchard": "cropland",
    "meadow": "grassland",
    "grass": "grassland",
    "heath": "shrubland",
    "scrub": "shrubland",
    "residential": "urban",
    "commercial": "urban",
    "industrial": "urban",
    "retail": "urban",
    "construction": "urban",
    "wetland": "wetland",
    "basin": "wetland",
    "quarry": "barren",
    "landfill": "barren",
    "brownfield": "barren",
    "bare_rock": "barren",
    "sand": "barren",
    "beach": "barren",
}

_NATURAL_MAP: dict[str, str] = {
    "wood": "forest",
    "scrub": "shrubland",
    "grassland": "grassland",
    "heath": "shrubland",
    "wetland": "wetland",
    "mud": "wetland",
    "bare_rock": "barren",
    "sand": "barren",
    "beach": "barren",
    "glacier": "barren",
}

_COVER_PERMITTING: dict[str, str] = {
    "barren": "low",
    "grassland": "low",
    "shrubland": "low",
    "cropland": "medium",
    "forest": "high",
    "wetland": "high",
    "urban": "high",
}


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2.0 * R * math.asin(math.sqrt(min(1.0, a)))


def _nearest_dist(p: LatLng, elements: list[dict[str, Any]]) -> tuple[float | None, str | None]:
    """Return (nearest_distance_m, tag_value) from a list of Overpass elements."""
    min_dist: float | None = None
    min_tag: str | None = None
    for el in elements:
        if "center" in el:
            lat = el["center"].get("lat")
            lng = el["center"].get("lon")
        else:
            lat = el.get("lat")
            lng = el.get("lon")
        if lat is None or lng is None:
            continue
        d = _haversine_m(p.latitude, p.longitude, float(lat), float(lng))
        if min_dist is None or d < min_dist:
            min_dist = d
            tags = el.get("tags") or {}
            min_tag = tags.get("highway") or tags.get("railway") or tags.get("power") or tags.get("place")
    return min_dist, min_tag


def _build_query(lat: float, lon: float) -> str:
    r_infra = 15000   # roads, rail, power, settlements within 15km
    r_land = 5000     # land use / natural within 5km (dominant class)
    r_pa = 25000      # protected areas within 25km
    return f"""
[out:json][timeout:30];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|track|service)$"](around:{r_infra},{lat},{lon});
  way["railway"](around:{r_infra},{lat},{lon});
  way["power"="line"](around:{r_infra},{lat},{lon});
  node["place"~"^(village|town|city|hamlet|suburb)$"](around:{r_infra},{lat},{lon});
  way["landuse"](around:{r_land},{lat},{lon});
  way["natural"~"^(wood|scrub|grassland|heath|wetland|mud|bare_rock|sand|beach|glacier)$"](around:{r_land},{lat},{lon});
  relation["boundary"="protected_area"](around:{r_pa},{lat},{lon});
  way["boundary"="protected_area"](around:{r_pa},{lat},{lon});
  node["boundary"="protected_area"](around:{r_pa},{lat},{lon});
);
out center tags;
"""


def _parse_raw(p: LatLng, elements: list[dict[str, Any]]) -> dict[str, Any]:
    roads, rails, powerlines, settlements = [], [], [], []
    landuse_elements: list[tuple[str, float]] = []  # (class, dist_m)
    pa_elements: list[tuple[str, float]] = []  # (name, dist_m)

    for el in elements:
        tags = el.get("tags") or {}
        el_type = el.get("type", "")

        if "highway" in tags:
            roads.append(el)
        if "railway" in tags:
            rails.append(el)
        if tags.get("power") == "line":
            powerlines.append(el)
        if "place" in tags and el_type == "node":
            settlements.append(el)

        if "landuse" in tags or "natural" in tags:
            raw_class = tags.get("landuse") or tags.get("natural", "")
            cover_class = _LANDUSE_MAP.get(raw_class) or _NATURAL_MAP.get(raw_class)
            if cover_class:
                ctr = el.get("center") or {}
                clat = ctr.get("lat") or el.get("lat")
                clon = ctr.get("lon") or el.get("lon")
                if clat is not None and clon is not None:
                    dist = _haversine_m(p.latitude, p.longitude, float(clat), float(clon))
                    landuse_elements.append((cover_class, dist))

        if tags.get("boundary") == "protected_area":
            ctr = el.get("center") or {}
            clat = ctr.get("lat") or el.get("lat")
            clon = ctr.get("lon") or el.get("lon")
            name = tags.get("name") or tags.get("int_name") or "Protected Area"
            if clat is not None and clon is not None:
                dist = _haversine_m(p.latitude, p.longitude, float(clat), float(clon))
                pa_elements.append((name, dist))

    # Infrastructure
    nearest_road, road_type = _nearest_dist(p, roads)
    nearest_rail, _ = _nearest_dist(p, rails)
    nearest_power, _ = _nearest_dist(p, powerlines)
    nearest_settle, _ = _nearest_dist(p, settlements)

    # Land cover: dominant class among nearest 3 OSM elements (weighted by proximity)
    cover_class: str | None = None
    if landuse_elements:
        landuse_elements.sort(key=lambda x: x[1])
        # Take the single closest element as the dominant class
        cover_class = landuse_elements[0][0]

    # Protected areas
    in_pa = False
    nearest_pa_name: str | None = None
    nearest_pa_m: float | None = None
    if pa_elements:
        pa_elements.sort(key=lambda x: x[1])
        nearest_pa_name, nearest_pa_m = pa_elements[0]
        in_pa = nearest_pa_m < 500  # treat as "inside" if centre <500m away

    return {
        "roads": roads,
        "rails": rails,
        "powerlines": powerlines,
        "settlements": settlements,
        "nearest_road_m": nearest_road,
        "road_type": road_type,
        "nearest_rail_m": nearest_rail,
        "nearest_powerline_m": nearest_power,
        "nearest_settlement_m": nearest_settle,
        "settlement_count": len(settlements),
        "cover_class": cover_class,
        "pa_in": in_pa,
        "pa_name": nearest_pa_name,
        "pa_m": nearest_pa_m,
    }


class OSMOverpassProvider(InfrastructureProvider, LandCoverProvider, ProtectedAreaProvider):
    """
    Single Overpass query covering infrastructure, land cover, and protected areas.
    Results are cached at 2-hour TTL.
    """

    def __init__(self, *, timeout_s: float = 35.0):
        self._timeout = httpx.Timeout(timeout_s, connect=15.0)

    async def _fetch(self, p: LatLng) -> dict[str, Any]:
        key = coord_cache_key(p.latitude, p.longitude)
        cached = infrastructure_cache.get(key)
        if cached is not None:
            data, _ = cached  # type: ignore[misc]
            return data  # type: ignore[return-value]

        query = _build_query(p.latitude, p.longitude)
        elements: list[dict[str, Any]] = []
        err: str | None = None

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    OVERPASS_URL,
                    data={"data": query},
                    headers={"User-Agent": "CHITTA-WindScreener/1.0 (renewable energy research)"},
                )
                resp.raise_for_status()
                payload = resp.json()
                elements = payload.get("elements") or []
        except Exception as e:
            err = str(e)

        parsed = _parse_raw(p, elements)
        parsed["_error"] = err
        parsed["_element_count"] = len(elements)

        # Cache with empty debug dict (debug built per-method)
        infrastructure_cache.set(key, (parsed, {}))
        return parsed

    async def get_infrastructure_data(
        self, p: LatLng
    ) -> tuple[InfrastructureData, dict[str, object]]:
        raw = await self._fetch(p)
        data = InfrastructureData(
            nearest_road_m=raw.get("nearest_road_m"),
            nearest_settlement_m=raw.get("nearest_settlement_m"),
            nearest_powerline_m=raw.get("nearest_powerline_m"),
            nearest_rail_m=raw.get("nearest_rail_m"),
            road_type=raw.get("road_type"),
            settlement_count_15km=int(raw.get("settlement_count") or 0),
        )
        debug: dict[str, object] = {
            "provider": "osm_overpass",
            "element_count": raw.get("_element_count"),
            "road_count": len(raw.get("roads") or []),
            "rail_count": len(raw.get("rails") or []),
            "powerline_count": len(raw.get("powerlines") or []),
            "settlement_count": raw.get("settlement_count"),
            "nearest_road_m": raw.get("nearest_road_m"),
            "nearest_powerline_m": raw.get("nearest_powerline_m"),
            "nearest_settlement_m": raw.get("nearest_settlement_m"),
        }
        if raw.get("_error"):
            debug["error"] = raw["_error"]
        return data, debug

    async def get_land_cover(
        self, p: LatLng
    ) -> tuple[LandCoverData, dict[str, object]]:
        raw = await self._fetch(p)
        cover_class: str | None = raw.get("cover_class")
        permitting = _COVER_PERMITTING.get(cover_class or "", "medium")
        data = LandCoverData(
            cover_class=cover_class,
            permitting_risk=permitting,
            source="osm",
        )
        debug: dict[str, object] = {
            "provider": "osm_overpass",
            "cover_class": cover_class,
            "permitting_risk": permitting,
        }
        if raw.get("_error"):
            debug["error"] = raw["_error"]
        return data, debug

    async def get_protected_area_risk(
        self, p: LatLng
    ) -> tuple[ProtectedAreaData, dict[str, object]]:
        raw = await self._fetch(p)
        in_pa: bool = bool(raw.get("pa_in", False))
        nearest_name: str | None = raw.get("pa_name")
        nearest_m_raw = raw.get("pa_m")
        nearest_m = float(nearest_m_raw) if nearest_m_raw is not None else None

        if in_pa:
            bio_risk = "high"
        elif nearest_m is not None and nearest_m < 5000:
            bio_risk = "high"
        elif nearest_m is not None and nearest_m < 15000:
            bio_risk = "medium"
        else:
            bio_risk = "low"

        data = ProtectedAreaData(
            in_protected_area=in_pa,
            nearest_pa_name=nearest_name,
            nearest_pa_m=nearest_m,
            biodiversity_risk=bio_risk,
        )
        debug: dict[str, object] = {
            "provider": "osm_overpass",
            "in_protected_area": in_pa,
            "nearest_pa_name": nearest_name,
            "nearest_pa_m": nearest_m,
            "biodiversity_risk": bio_risk,
        }
        if raw.get("_error"):
            debug["error"] = raw["_error"]
        return data, debug
