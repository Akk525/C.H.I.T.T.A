from __future__ import annotations

import asyncio
import math
import statistics
from dataclasses import dataclass
from typing import TypedDict

from app.providers.base import (
    ElevationProvider,
    InfrastructureData,
    LatLng,
    LandCoverData,
    ProtectedAreaData,
    WindProvider,
)
from app.providers.nasa_power import NasaPowerWindProvider
from app.providers.opentopodata import OpenTopoDataElevationProvider
from app.providers.osm_overpass import OSMOverpassProvider
from app.services.scoring import clamp100, terrain_score_from_complexity


@dataclass(frozen=True)
class ProviderChoice:
    wind: str       # "nasa_power" | "unavailable"
    elevation: str  # "opentopodata" | "unavailable"
    infrastructure: str  # "osm_overpass" | "unavailable"


class EnrichedData(TypedDict):
    infrastructure: InfrastructureData | None
    land_cover: LandCoverData | None
    protected_area: ProtectedAreaData | None
    infra_debug: dict
    landcover_debug: dict
    pa_debug: dict


def mean_wind_speed_score(mean_mps: float) -> float:
    if mean_mps <= 3.0:
        return 0.0
    if mean_mps >= 10.0:
        return 100.0
    return clamp100((mean_mps - 3.0) / (10.0 - 3.0) * 100.0)


def wind_consistency_score(speeds_mps: list[float]) -> float:
    if len(speeds_mps) < 10:
        return 45.0
    mean = statistics.fmean(speeds_mps)
    if mean <= 0.01:
        return 0.0
    stdev = statistics.pstdev(speeds_mps)
    cv = stdev / mean
    if cv <= 0.2:
        return 90.0
    if cv >= 0.8:
        return 20.0
    t = (cv - 0.2) / (0.8 - 0.2)
    return clamp100(90.0 - 70.0 * t)


def terrain_roughness_from_samples(elevations_m: list[float]) -> tuple[float, float]:
    if len(elevations_m) < 4:
        return 1.0, 50.0
    stdev = statistics.pstdev(elevations_m)
    complexity = 0.15 + min(1.85, (stdev / 200.0) * 1.85)
    score = terrain_score_from_complexity(complexity)
    return float(complexity), float(score)


def compute_slope_pct(elevations_m: list[float], radius_m: float) -> float:
    """
    Approximate mean slope from a ring of elevation samples.
    Uses the elevation range divided by the chord length across the ring.
    """
    if len(elevations_m) < 4 or radius_m <= 0:
        return 0.0
    elev_range = max(elevations_m) - min(elevations_m)
    # Chord across ring ≈ 2 * radius as upper bound for rise/run
    return clamp100((elev_range / (2.0 * radius_m)) * 100.0)


def compute_ridge_score(elevations_m: list[float]) -> float:
    """
    Measures ridge/valley contrast as std-dev of first differences.
    Higher = more abrupt terrain transitions.
    Returns 0.0 (smooth) to 1.0 (very jagged).
    """
    if len(elevations_m) < 4:
        return 0.0
    diffs = [abs(elevations_m[i + 1] - elevations_m[i]) for i in range(len(elevations_m) - 1)]
    stdev = statistics.pstdev(diffs)
    return float(min(1.0, stdev / 50.0))  # 50m diff stdev ≈ very rugged


def confidence_score(
    *,
    wind_used_real: bool,
    elev_used_real: bool,
    wind_sample_count: int,
    elev_sample_count: int,
    infra_used_real: bool = False,
    landcover_available: bool = False,
    pa_available: bool = False,
) -> float:
    score = 20.0
    if wind_used_real:
        score += 25.0
    if elev_used_real:
        score += 20.0
    if infra_used_real:
        score += 15.0
    if landcover_available:
        score += 10.0
    if pa_available:
        score += 10.0
    # All five sources bonus
    if wind_used_real and elev_used_real and infra_used_real:
        score += 5.0
    # Penalties for sparse data
    if wind_sample_count < 100 and wind_used_real:
        score -= 10.0
    if elev_sample_count < 6 and elev_used_real:
        score -= 5.0
    return clamp100(score)


async def analyze_site_realdata(
    p: LatLng,
    *,
    wind_provider: WindProvider | None = None,
    elevation_provider: ElevationProvider | None = None,
    elevation_radius_m: float = 1500.0,
    elevation_samples: int = 12,
) -> tuple[dict[str, float | None], dict[str, object], ProviderChoice]:
    """
    Core wind + terrain analysis. Used by both single-site route and heatmap.
    Does NOT call OSM or enriched providers — use analyze_site_enriched for that.
    """
    wind_provider = wind_provider or NasaPowerWindProvider()
    elevation_provider = elevation_provider or OpenTopoDataElevationProvider()

    unavailable: list[str] = []

    wind_provider_name = "nasa_power"
    wind_score: float | None = None
    mean_speed: float | None = None
    mean_score: float | None = None
    consistency: float | None = None
    wind_dbg: dict[str, object] = {}
    speeds: list[float] = []
    wind_speed_at_hub: float | None = None  # mean speed at primary hub height (50m or 10m)

    try:
        wind_ts, wind_dbg = await wind_provider.get_wind_timeseries(p)
        speeds = list(wind_ts.get("speeds_mps") or [])
        hub_height = wind_ts.get("hub_height_m", 10)
        # Use highest available height mean speed for economic/hub-height reporting
        for _key in ("mean_50m_mps", "mean_10m_mps"):
            _v = wind_dbg.get(_key)
            if isinstance(_v, (int, float)) and float(_v) > 0:
                wind_speed_at_hub = float(_v)  # type: ignore[arg-type]
                break
    except Exception as e:
        wind_dbg = {
            "provider": "nasa_power",
            "source": "nasa_power",
            "errors": [f"wind provider exception: {e!s}"],
        }
        speeds = []
        hub_height = 10

    if not speeds:
        unavailable.append("wind")
        wind_provider_name = "unavailable"
    else:
        mean_speed = float(
            wind_ts.get("mean_speed_mps") or (sum(speeds) / len(speeds))
        )
        mean_score = mean_wind_speed_score(mean_speed)
        consistency = wind_consistency_score(speeds)
        wind_score = clamp100(0.7 * mean_score + 0.3 * consistency)
        # Fall back to timeseries mean if individual height keys unavailable
        if wind_speed_at_hub is None and mean_speed and mean_speed > 0:
            wind_speed_at_hub = mean_speed

    elev_provider_name = "opentopodata"
    elev_m: float | None = None
    terrain_complexity: float | None = None
    terrain_score: float | None = None
    slope_pct: float | None = None
    ridge_score: float | None = None
    elev_dbg_point: dict[str, object] = {}
    elev_dbg_samples: dict[str, object] = {}
    samples: list[object] = []
    elev_list: list[float] = []

    try:
        elev_m, elev_dbg_point = await elevation_provider.get_elevation_m(p)
    except Exception as e:
        elev_m = None
        elev_dbg_point = {
            "provider": "opentopodata",
            "source": "opentopodata",
            "errors": [f"elevation point exception: {e!s}"],
        }

    try:
        samples, elev_dbg_samples = await elevation_provider.get_elevation_samples(
            p, radius_m=elevation_radius_m, sample_count=elevation_samples
        )
    except Exception as e:
        samples = []
        elev_dbg_samples = {
            "provider": "opentopodata",
            "source": "opentopodata",
            "errors": [f"elevation samples exception: {e!s}"],
        }

    elev_list = [
        float(s["elevation_m"])  # type: ignore[index]
        for s in samples
        if isinstance(s, dict) and s.get("elevation_m") is not None
    ]

    if not elev_list:
        unavailable.append("elevation")
        elev_provider_name = "unavailable"
        elev_m = None
        terrain_complexity = None
        terrain_score = None
        slope_pct = None
        ridge_score = None
    else:
        terrain_complexity, terrain_score = terrain_roughness_from_samples(elev_list)
        slope_pct = compute_slope_pct(elev_list, elevation_radius_m)
        ridge_score = compute_ridge_score(elev_list)
        if elev_m is None and elev_list:
            elev_m = elev_list[0]

    conf = confidence_score(
        wind_used_real=(wind_provider_name == "nasa_power"),
        elev_used_real=(elev_provider_name == "opentopodata"),
        wind_sample_count=len(speeds),
        elev_sample_count=len(elev_list),
    )

    debug = {
        "sources": {
            "wind": {
                "provider": wind_provider_name,
                "status": "unavailable" if wind_provider_name == "unavailable" else "available",
                "raw": {
                    "mean_speed_mps": mean_speed,
                    "wind_speed_at_hub_mps": wind_speed_at_hub,
                    "sample_count": len(speeds),
                    "hub_height_m": hub_height if speeds else None,
                },
                "derived": {
                    "meanWindSpeedScore": mean_score,
                    "windConsistencyScore": consistency,
                    "windScoreBlended": wind_score,
                },
                "debug": wind_dbg,
            },
            "elevation": {
                "provider": elev_provider_name,
                "status": "unavailable" if elev_provider_name == "unavailable" else "available",
                "raw": {
                    "elevationM": elev_m,
                    "sample_count": len(samples),
                    "samples": samples[:50] if isinstance(samples, list) else [],
                },
                "derived": {
                    "terrainRoughnessScore": terrain_score,
                    "terrainComplexity": terrain_complexity,
                    "slopePct": slope_pct,
                    "ridgeScore": ridge_score,
                },
                "debug_point": elev_dbg_point,
                "debug_samples": elev_dbg_samples,
            },
        },
        "quality": {
            "unavailable": unavailable,
            "usedFallbacks": unavailable,
        },
    }

    metrics_fragment: dict[str, float | None] = {
        "windScore": wind_score,
        "windSpeedAtHub": wind_speed_at_hub,
        "elevationM": float(elev_m) if elev_m is not None else None,
        "terrainComplexity": terrain_complexity,
        "terrainScore": terrain_score,
        "slopePct": slope_pct,
        "ridgeScore": ridge_score,
        "confidenceScore": float(conf),
    }

    choice = ProviderChoice(wind=wind_provider_name, elevation=elev_provider_name, infrastructure="unavailable")
    return metrics_fragment, debug, choice


async def analyze_site_enriched(
    p: LatLng,
    *,
    wind_provider: WindProvider | None = None,
    elevation_provider: ElevationProvider | None = None,
    osm_provider: OSMOverpassProvider | None = None,
    elevation_radius_m: float = 1500.0,
    elevation_samples: int = 12,
) -> tuple[dict[str, float | None], dict[str, object], ProviderChoice, EnrichedData]:
    """
    Full site analysis: wind + terrain (parallel) + OSM infrastructure/land cover/PA.
    Returns extended metrics and enriched data for Phase 1+ scoring.
    """
    osm_provider = osm_provider or OSMOverpassProvider()

    # Run wind+terrain and OSM fetch in parallel
    base_task = analyze_site_realdata(
        p,
        wind_provider=wind_provider,
        elevation_provider=elevation_provider,
        elevation_radius_m=elevation_radius_m,
        elevation_samples=elevation_samples,
    )
    infra_task = osm_provider.get_infrastructure_data(p)
    lc_task = osm_provider.get_land_cover(p)
    pa_task = osm_provider.get_protected_area_risk(p)

    (base_metrics, base_debug, base_choice), infra_result, lc_result, pa_result = (
        await asyncio.gather(base_task, infra_task, lc_task, pa_task, return_exceptions=False)
    )

    infra_data: InfrastructureData | None
    infra_debug: dict
    if isinstance(infra_result, Exception):
        infra_data = None
        infra_debug = {"error": str(infra_result)}
    else:
        infra_data, infra_debug = infra_result

    lc_data: LandCoverData | None
    lc_debug: dict
    if isinstance(lc_result, Exception):
        lc_data = None
        lc_debug = {"error": str(lc_result)}
    else:
        lc_data, lc_debug = lc_result

    pa_data: ProtectedAreaData | None
    pa_debug: dict
    if isinstance(pa_result, Exception):
        pa_data = None
        pa_debug = {"error": str(pa_result)}
    else:
        pa_data, pa_debug = pa_result

    infra_used = infra_data is not None and infra_debug.get("error") is None
    infra_provider_name = "osm_overpass" if infra_used else "unavailable"

    # Recompute confidence with enriched sources
    wind_used = base_choice.wind == "nasa_power"
    elev_used = base_choice.elevation == "opentopodata"
    wind_samples = len(base_metrics.get("windScore") and [] or [])
    # Re-derive wind sample count from debug
    wind_src = (base_debug.get("sources") or {}).get("wind") or {}
    wind_samples = int((wind_src.get("raw") or {}).get("sample_count") or 0)  # type: ignore[arg-type]
    elev_src = (base_debug.get("sources") or {}).get("elevation") or {}
    elev_samples = int((elev_src.get("raw") or {}).get("sample_count") or 0)  # type: ignore[arg-type]

    enriched_conf = confidence_score(
        wind_used_real=wind_used,
        elev_used_real=elev_used,
        wind_sample_count=wind_samples,
        elev_sample_count=elev_samples,
        infra_used_real=infra_used,
        landcover_available=lc_data is not None and lc_data.get("cover_class") is not None,
        pa_available=pa_data is not None,
    )

    # Merge metrics
    metrics = dict(base_metrics)
    metrics["confidenceScore"] = float(enriched_conf)

    enriched: EnrichedData = {
        "infrastructure": infra_data,
        "land_cover": lc_data,
        "protected_area": pa_data,
        "infra_debug": infra_debug,
        "landcover_debug": lc_debug,
        "pa_debug": pa_debug,
    }

    choice = ProviderChoice(
        wind=base_choice.wind,
        elevation=base_choice.elevation,
        infrastructure=infra_provider_name,
    )

    # Add OSM debug to top-level debug
    base_debug["sources"]["infrastructure"] = {  # type: ignore[index]
        "provider": infra_provider_name,
        "status": "available" if infra_used else "unavailable",
        "debug": infra_debug,
    }
    base_debug["sources"]["land_cover"] = {  # type: ignore[index]
        "provider": infra_provider_name,
        "status": "available" if lc_data is not None else "unavailable",
        "cover_class": lc_data.get("cover_class") if lc_data else None,
        "debug": lc_debug,
    }
    base_debug["sources"]["protected_area"] = {  # type: ignore[index]
        "provider": infra_provider_name,
        "status": "available" if pa_data is not None else "unavailable",
        "debug": pa_debug,
    }

    return metrics, base_debug, choice, enriched
