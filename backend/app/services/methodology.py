from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.analysis import ProviderChoice

SCORING_FORMULA_VERSION = "1.0.0"

TERRAIN_ROUGHNESS_METHOD = (
    "Sample 12 elevation points in a 1.5 km ring; compute standard deviation; "
    "map stdev to terrain complexity (0.15–2.0); invert to buildability score."
)

CONFIDENCE_CALCULATION_METHOD = (
    "Start at 35; add 30 if real wind data succeeds, 25 if real elevation succeeds, "
    "10 bonus if both succeed; subtract up to 15 for insufficient sample counts."
)

WIND_SCORE_FORMULA_PLAIN = (
    "Wind score = 70% mean-speed score (3–10 m/s → 0–100) + 30% consistency score "
    "(lower day-to-day variability yields a higher score)."
)

TOTAL_SUITABILITY_FORMULA_PLAIN = (
    "Total suitability = 40% wind + 25% terrain + 20% accessibility + 15% confidence."
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_analysis_id() -> str:
    return str(uuid.uuid4())


def _provider_label(name: str) -> str:
    labels = {
        "nasa_power": "NASA POWER",
        "opentopodata": "OpenTopoData (SRTM90m)",
        "mock": "Mock (accessibility proxy)",
        "unavailable": "Unavailable",
    }
    return labels.get(name, name)


def _wind_date_range(sources_debug: dict[str, object]) -> str:
    wind = (sources_debug.get("sources") or {}).get("wind") if isinstance(sources_debug.get("sources"), dict) else None
    if not isinstance(wind, dict):
        return "Unknown"
    dbg = wind.get("debug")
    if isinstance(dbg, dict):
        start = dbg.get("periodStart")
        end = dbg.get("periodEnd")
        if start and end:
            return f"{start} to {end} (daily WS10M)"
    return "Last 365 days (daily WS10M, NASA POWER target)"


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

    return {
        "windDataSource": _provider_label(choice.wind),
        "windDateRange": _wind_date_range(sources_debug),
        "elevationSource": _provider_label(choice.elevation),
        "scoringFormulaVersion": SCORING_FORMULA_VERSION,
        "terrainRoughnessMethod": TERRAIN_ROUGHNESS_METHOD,
        "confidenceCalculationMethod": CONFIDENCE_CALCULATION_METHOD,
        "fallbackStatus": _fallback_status(used),
        "generatedAt": generated_at or utc_now_iso(),
    }


def build_site_audit_trail(
    *,
    latitude: float,
    longitude: float,
    choice: ProviderChoice,
    generated_at: str,
    analysis_id: str,
) -> list[str]:
    wind_status = (
        "UNAVAILABLE"
        if choice.wind == "unavailable"
        else "REAL"
        if choice.wind != "mock"
        else "MOCK"
    )
    elev_status = (
        "UNAVAILABLE"
        if choice.elevation == "unavailable"
        else "REAL"
        if choice.elevation != "mock"
        else "MOCK"
    )
    return [
        f"Coordinate received: {latitude:.5f}, {longitude:.5f}",
        f"Wind provider queried: {_provider_label(choice.wind)} [{wind_status}]",
        f"Elevation provider queried: {_provider_label(choice.elevation)} [{elev_status}]",
        f"Scores computed using formula v{SCORING_FORMULA_VERSION}",
        f"Report generated at {generated_at} (analysisId: {analysis_id})",
    ]


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
