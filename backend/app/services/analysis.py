from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from app.providers.base import ElevationProvider, LatLng, WindProvider
from app.providers.mock import MockElevationProvider, MockWindProvider
from app.providers.nasa_power import NasaPowerWindProvider
from app.providers.opentopodata import OpenTopoDataElevationProvider
from app.services.scoring import clamp100, terrain_score_from_complexity


@dataclass(frozen=True)
class ProviderChoice:
    wind: str  # "nasa_power" | "mock"
    elevation: str  # "opentopodata" | "mock"


def mean_wind_speed_score(mean_mps: float) -> float:
    # Simple tunable curve: 0 at 3 m/s, 100 at 10 m/s.
    if mean_mps <= 3.0:
        return 0.0
    if mean_mps >= 10.0:
        return 100.0
    return clamp100((mean_mps - 3.0) / (10.0 - 3.0) * 100.0)


def wind_consistency_score(speeds_mps: list[float]) -> float:
    # Based on coefficient of variation (CV = stdev/mean). Lower CV => higher score.
    if len(speeds_mps) < 10:
        return 45.0
    mean = statistics.fmean(speeds_mps)
    if mean <= 0.01:
        return 0.0
    stdev = statistics.pstdev(speeds_mps)
    cv = stdev / mean
    # Map CV 0.2 -> 90, CV 0.8 -> 20 (clamp).
    if cv <= 0.2:
        return 90.0
    if cv >= 0.8:
        return 20.0
    t = (cv - 0.2) / (0.8 - 0.2)
    return clamp100(90.0 - 70.0 * t)


def terrain_roughness_from_samples(elevations_m: list[float]) -> tuple[float, float]:
    """
    Returns: (terrain_complexity_scalar, roughness_score_0_100)

    Complexity is a scalar similar to previous mock (roughly 0.15..2.0).
    We estimate roughness via stdev of elevations in the sample ring.
    """
    if len(elevations_m) < 4:
        return 1.0, 50.0
    stdev = statistics.pstdev(elevations_m)
    # Convert stdev meters into complexity scalar; 0m => 0.15, 200m => ~2.0.
    complexity = 0.15 + min(1.85, (stdev / 200.0) * 1.85)
    # Convert complexity to buildability score using existing mapping.
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

    if wind_sample_count < 100:
        score -= 10.0
    if elev_sample_count < 6:
        score -= 5.0

    return clamp100(score)


async def analyze_site_realdata(
    p: LatLng,
    *,
    wind_provider: WindProvider | None = None,
    elevation_provider: ElevationProvider | None = None,
    elevation_radius_m: float = 1500.0,
    elevation_samples: int = 12,
) -> tuple[dict[str, float], dict[str, object], ProviderChoice]:
    """
    Returns (metrics_fragment, debug, providerChoice)
    """
    wind_provider = wind_provider or NasaPowerWindProvider()
    elevation_provider = elevation_provider or OpenTopoDataElevationProvider()

    used_fallbacks: list[str] = []

    # WIND (prefer real)
    wind_dbg: dict[str, object]
    wind_provider_name = "nasa_power"
    try:
        wind_ts, wind_dbg = await wind_provider.get_wind_timeseries(p)
        speeds = list(wind_ts.get("speeds_mps") or [])
    except Exception as e:
        wind_ts = {"resolution": "daily", "periodStart": "", "periodEnd": "", "speeds_mps": [], "directions_deg": None, "mean_speed_mps": 0.0}
        wind_dbg = {"provider": "nasa_power", "source": "nasa_power", "errors": [f"wind provider exception: {e!s}"]}
        speeds = []

    if not speeds:
        used_fallbacks.append("wind")
        wind_provider_name = "mock"
        mock = MockWindProvider()
        wind_ts, wind_dbg = await mock.get_wind_timeseries(p)
        speeds = list(wind_ts.get("speeds_mps") or [])

    mean_speed = float(wind_ts.get("mean_speed_mps") or (sum(speeds) / len(speeds) if speeds else 0.0))
    mean_score = mean_wind_speed_score(mean_speed)
    consistency = wind_consistency_score(speeds)
    wind_score = clamp100(0.7 * mean_score + 0.3 * consistency)

    # ELEVATION (prefer real)
    elev_provider_name = "opentopodata"
    try:
        elev_m, elev_dbg_point = await elevation_provider.get_elevation_m(p)
    except Exception as e:
        elev_m, elev_dbg_point = 0.0, {"provider": "opentopodata", "source": "opentopodata", "errors": [f"elevation point exception: {e!s}"]}

    try:
        samples, elev_dbg_samples = await elevation_provider.get_elevation_samples(
            p, radius_m=elevation_radius_m, sample_count=elevation_samples
        )
    except Exception as e:
        samples, elev_dbg_samples = [], {"provider": "opentopodata", "source": "opentopodata", "errors": [f"elevation samples exception: {e!s}"]}

    elev_list = [s["elevation_m"] for s in samples if s.get("elevation_m") is not None]  # type: ignore[index]

    if not samples or (samples and not elev_list):
        used_fallbacks.append("elevation")
        elev_provider_name = "mock"
        mock_e = MockElevationProvider()
        elev_m, elev_dbg_point = await mock_e.get_elevation_m(p)
        samples, elev_dbg_samples = await mock_e.get_elevation_samples(
            p, radius_m=elevation_radius_m, sample_count=elevation_samples
        )
        elev_list = [s["elevation_m"] for s in samples if s.get("elevation_m") is not None]  # type: ignore[index]

    terrain_complexity, terrain_score = terrain_roughness_from_samples([float(x) for x in elev_list])  # type: ignore[arg-type]

    conf = confidence_score(
        wind_used_real=(wind_provider_name != "mock"),
        elev_used_real=(elev_provider_name != "mock"),
        wind_sample_count=len(speeds),
        elev_sample_count=len(elev_list),
    )

    debug = {
        "sources": {
            "wind": {
                "provider": wind_provider_name,
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
                "raw": {
                    "elevationM": elev_m,
                    "sample_count": len(samples),
                    "samples": samples[:50],
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
            "usedFallbacks": used_fallbacks,
        },
    }

    metrics_fragment = {
        "windScore": wind_score,
        "elevationM": float(elev_m),
        "terrainComplexity": float(terrain_complexity),
        "terrainScore": float(terrain_score),
        "confidenceScore": float(conf),
    }

    choice = ProviderChoice(wind=wind_provider_name, elevation=elev_provider_name)
    return metrics_fragment, debug, choice

