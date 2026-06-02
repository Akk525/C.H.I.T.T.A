from __future__ import annotations

import statistics
from dataclasses import dataclass

from app.providers.base import ElevationProvider, LatLng, WindProvider
from app.providers.nasa_power import NasaPowerWindProvider
from app.providers.opentopodata import OpenTopoDataElevationProvider
from app.services.scoring import clamp100, terrain_score_from_complexity


@dataclass(frozen=True)
class ProviderChoice:
    wind: str  # "nasa_power" | "unavailable"
    elevation: str  # "opentopodata" | "unavailable"


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


def confidence_score(
    *, wind_used_real: bool, elev_used_real: bool, wind_sample_count: int, elev_sample_count: int
) -> float:
    score = 35.0
    if wind_used_real:
        score += 30.0
    if elev_used_real:
        score += 25.0
    if wind_used_real and elev_used_real:
        score += 10.0
    if not wind_used_real and not elev_used_real:
        score = 15.0
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

    try:
        wind_ts, wind_dbg = await wind_provider.get_wind_timeseries(p)
        speeds = list(wind_ts.get("speeds_mps") or [])
    except Exception as e:
        wind_dbg = {
            "provider": "nasa_power",
            "source": "nasa_power",
            "errors": [f"wind provider exception: {e!s}"],
        }
        speeds = []

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

    elev_provider_name = "opentopodata"
    elev_m: float | None = None
    terrain_complexity: float | None = None
    terrain_score: float | None = None
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
    else:
        terrain_complexity, terrain_score = terrain_roughness_from_samples(elev_list)
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
                    "sample_count": len(speeds),
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
        "elevationM": float(elev_m) if elev_m is not None else None,
        "terrainComplexity": terrain_complexity,
        "terrainScore": terrain_score,
        "confidenceScore": float(conf),
    }

    choice = ProviderChoice(wind=wind_provider_name, elevation=elev_provider_name)
    return metrics_fragment, debug, choice
