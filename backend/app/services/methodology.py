from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.analysis import ProviderChoice

SCORING_FORMULA_VERSION = "2.1.0"

TERRAIN_ROUGHNESS_METHOD = (
    "Sample 12 elevation points in a 1.5 km ring; compute standard deviation; "
    "map stdev to terrain complexity (0.15–2.0); invert to buildability score. "
    "Also computes slope (elevation range / 2×radius) and ridge score (stdev of first differences)."
)

CONFIDENCE_CALCULATION_METHOD = (
    "Start at 20; add 25 for real wind, 20 for real elevation, 15 for real OSM infrastructure, "
    "10 for land cover data, 10 for protected area data; +5 bonus if wind+elevation+infra all real; "
    "subtract up to 15 for insufficient sample counts."
)

WIND_SCORE_FORMULA_PLAIN = (
    "Wind score = 70% mean-speed score (3–10 m/s → 0–100) + 30% consistency score "
    "(lower day-to-day variability yields a higher score). "
    "Uses highest available NASA POWER height: WS100M preferred, then WS50M, then WS10M."
)

TOTAL_SUITABILITY_FORMULA_PLAIN = (
    "Total suitability v2 = 35% wind + 20% terrain + 15% infrastructure + "
    "10% environmental (land cover + protected areas) + 10% population proxy + 10% confidence. "
    "Falls back to legacy 40/25/20/15 when OSM data is unavailable."
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_analysis_id() -> str:
    return str(uuid.uuid4())


def _provider_label(name: str) -> str:
    labels = {
        "nasa_power": "NASA POWER (WS10M/WS50M/WS100M)",
        "opentopodata": "OpenTopoData (SRTM90m)",
        "osm_overpass": "OpenStreetMap (Overpass API)",
        "mock": "Mock (fallback proxy)",
        "unavailable": "Unavailable",
    }
    return labels.get(name, name)


def _wind_date_range(sources_debug: dict[str, object]) -> str:
    wind_src = (sources_debug.get("sources") or {}).get("wind") if isinstance(sources_debug.get("sources"), dict) else None
    if not isinstance(wind_src, dict):
        return "Unknown"
    dbg = wind_src.get("debug")
    if not isinstance(dbg, dict):
        return "Unknown"

    start = dbg.get("requestedStartDate") or dbg.get("periodStart")
    end = dbg.get("requestedEndDate") or dbg.get("periodEnd")
    latest = dbg.get("latestCompletedDate")
    days = dbg.get("daysReturned")
    params_used = dbg.get("parametersUsed")
    height = dbg.get("primary_height_m")

    if not start or not end:
        return "Last 365 days (NASA POWER target)"

    height_label = f"WS{height}M" if height else "WS10M"
    if params_used and params_used != "none":
        height_label = params_used.split(" ")[0]  # "WS100M", "WS50M", or "WS10M"

    base = f"{start} to {end} (daily {height_label}, NASA POWER)"
    if latest:
        base += f" — latest data: {latest}"
    if days:
        base += f", {days} days returned"
    return base


def _fallback_status(used: list[str]) -> str:
    if not used:
        return "none — all primary providers succeeded"
    return "data unavailable for: " + ", ".join(used)


def build_methodology(
    sources_debug: dict[str, object],
    choice: ProviderChoice,
    *,
    generated_at: str | None = None,
) -> dict[str, str]:
    used = []
    quality = sources_debug.get("quality")
    if isinstance(quality, dict) and isinstance(quality.get("usedFallbacks"), list):
        used = [str(x) for x in quality["usedFallbacks"]]
    if hasattr(choice, "infrastructure") and choice.infrastructure == "unavailable":
        used.append("infrastructure")

    return {
        "windDataSource": _provider_label(choice.wind),
        "windDateRange": _wind_date_range(sources_debug),
        "elevationSource": _provider_label(choice.elevation),
        "infrastructureSource": _provider_label(getattr(choice, "infrastructure", "unavailable")),
        "scoringFormulaVersion": SCORING_FORMULA_VERSION,
        "terrainRoughnessMethod": TERRAIN_ROUGHNESS_METHOD,
        "confidenceCalculationMethod": CONFIDENCE_CALCULATION_METHOD,
        "fallbackStatus": _fallback_status(used),
        "generatedAt": generated_at or utc_now_iso(),
    }


def _status_label(name: str) -> str:
    if name == "unavailable":
        return "UNAVAILABLE"
    if name == "mock":
        return "MOCK"
    return "REAL"


def build_site_audit_trail(
    *,
    latitude: float,
    longitude: float,
    choice: ProviderChoice,
    generated_at: str,
    analysis_id: str,
) -> list[str]:
    infra_name = getattr(choice, "infrastructure", "unavailable")
    trail = [
        f"Coordinate received: {latitude:.5f}, {longitude:.5f}",
        f"Wind provider queried: {_provider_label(choice.wind)} [{_status_label(choice.wind)}]",
        f"Elevation provider queried: {_provider_label(choice.elevation)} [{_status_label(choice.elevation)}]",
        f"Infrastructure provider queried: {_provider_label(infra_name)} [{_status_label(infra_name)}]",
        f"Scores computed using formula v{SCORING_FORMULA_VERSION}",
        f"Report generated at {generated_at} (analysisId: {analysis_id})",
    ]
    return trail


def build_heatmap_methodology(
    *,
    generated_at: str,
    radius_km: float,
    grid_size: int,
    cells: list[dict[str, Any]],
) -> dict[str, str]:
    unavail_wind = sum(
        1 for c in cells if (c.get("providerStatus") or {}).get("wind") == "UNAVAILABLE"
    )
    unavail_elev = sum(
        1 for c in cells if (c.get("providerStatus") or {}).get("elevation") == "UNAVAILABLE"
    )
    total = len(cells) or 1
    unavailable_parts = []
    if unavail_wind:
        unavailable_parts.append(f"wind ({unavail_wind}/{total} cells)")
    if unavail_elev:
        unavailable_parts.append(f"elevation ({unavail_elev}/{total} cells)")

    fallback_status = (
        "none — all primary providers succeeded for all cells"
        if not unavailable_parts
        else "data unavailable for: " + ", ".join(unavailable_parts)
    )

    return {
        "windDataSource": "NASA POWER (per grid cell)",
        "windDateRange": "Last 365 days (daily WS10M, NASA POWER target)",
        "elevationSource": "OpenTopoData SRTM90m (per grid cell)",
        "scoringFormulaVersion": SCORING_FORMULA_VERSION,
        "terrainRoughnessMethod": TERRAIN_ROUGHNESS_METHOD,
        "confidenceCalculationMethod": CONFIDENCE_CALCULATION_METHOD,
        "fallbackStatus": fallback_status,
        "generatedAt": generated_at,
    }


def build_heatmap_audit_trail(
    *,
    latitude: float,
    longitude: float,
    radius_km: float,
    grid_size: int,
    cell_count: int,
    generated_at: str,
    analysis_id: str,
) -> list[str]:
    return [
        f"Coordinate received: {latitude:.5f}, {longitude:.5f}",
        f"Grid generated: {grid_size}×{grid_size} over {radius_km:.0f} km radius",
        "Wind provider queried per cell: NASA POWER (unavailable when API fails)",
        "Elevation provider queried per cell: OpenTopoData (unavailable when API fails)",
        f"Scores computed for {cell_count} cells using formula v{SCORING_FORMULA_VERSION}",
        f"Heatmap ranked and returned at {generated_at} (analysisId: {analysis_id})",
    ]
