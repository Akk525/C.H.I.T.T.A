"""
Evidence Quality Layer for CHITTA.

Assesses the quality of data underlying each analysis dimension.
Higher quality means the metric can be trusted more; lower quality means
more unknowns and greater sensitivity to on-site measurement.

All rules are deterministic. No LLM calls. No external API calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.services.economics import EconomicMetrics


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class EvidenceQualityItem:
    dimension: str
    source: str
    quality: Literal["high", "medium", "low"]
    confidence: float          # 0–100
    limitations: list[str]
    potentialError: str


@dataclass
class EvidenceQualityReport:
    items: list[EvidenceQualityItem]
    overallQuality: Literal["high", "medium", "low"]
    overallConfidence: float


# ── Source extraction helpers ─────────────────────────────────────────────────

def _src(sources_debug: dict, key: str) -> dict:
    """Safely extract a source sub-dict."""
    return (sources_debug.get("sources") or {}).get(key) or {}


def _raw(sources_debug: dict, key: str) -> dict:
    return _src(sources_debug, key).get("raw") or {}


def _provider(sources_debug: dict, key: str) -> str:
    return str(_src(sources_debug, key).get("provider") or "unavailable").lower()


# ── Six dimension quality functions ──────────────────────────────────────────

def _wind_quality(
    wind_speed_at_hub: float | None,
    sources_debug: dict,
) -> EvidenceQualityItem:
    provider = _provider(sources_debug, "wind")
    raw = _raw(sources_debug, "wind")
    sample_count: int = int(raw.get("sample_count") or 0)
    hub_height_m: float | None = raw.get("hub_height_m")

    is_real = provider == "nasa_power" and wind_speed_at_hub is not None

    if is_real and sample_count >= 200 and hub_height_m is not None and hub_height_m >= 50.0:
        quality: Literal["high", "medium", "low"] = "high"
        confidence = min(90.0, 65.0 + sample_count / 100.0)
        source = f"NASA POWER ({hub_height_m:.0f}m hub height, {sample_count} daily observations)"
        limitations = [
            "Satellite/reanalysis data — not equivalent to on-site measurement.",
            "Temporal resolution is daily mean; diurnal and seasonal patterns may be smoothed.",
        ]
        potential_error = "±5–8 percentage points on capacity factor; ±15% on LCOE"
    elif is_real:
        quality = "medium"
        confidence = 55.0 + max(0, sample_count - 50) / 20.0
        source = f"NASA POWER ({hub_height_m or 10:.0f}m, {sample_count} observations)"
        limitations = [
            "Limited sample count or low hub height reduces estimate accuracy.",
            "Satellite/reanalysis data — not equivalent to on-site measurement.",
            f"Only {sample_count} daily observations used; ≥200 recommended for screening.",
        ]
        if hub_height_m is not None and hub_height_m < 50:
            limitations.append(
                f"Data at {hub_height_m:.0f}m only — hub height extrapolation adds uncertainty."
            )
        potential_error = "±10–15% on capacity factor; ±20–25% on LCOE"
    else:
        quality = "low"
        confidence = 20.0
        source = "NASA POWER (unavailable or mock)"
        limitations = [
            "Wind resource data unavailable — all wind-derived metrics are unreliable.",
            "Economic feasibility cannot be assessed without wind data.",
            "All capacity factor estimates use a conservative 22% default.",
        ]
        potential_error = "Wind resource unvalidated — all derived metrics highly uncertain"

    return EvidenceQualityItem(
        dimension="Wind",
        source=source,
        quality=quality,
        confidence=round(confidence, 1),
        limitations=limitations,
        potentialError=potential_error,
    )


def _terrain_quality(
    terrain_score: float | None,
    sources_debug: dict,
) -> EvidenceQualityItem:
    provider = _provider(sources_debug, "elevation")
    raw = _raw(sources_debug, "elevation")
    sample_count: int = int(raw.get("sample_count") or 0)

    is_real = provider == "opentopodata" and terrain_score is not None

    if is_real and sample_count >= 5:
        quality: Literal["high", "medium", "low"] = "high"
        confidence = 85.0
        source = f"OpenTopoData SRTM90m ({sample_count} elevation samples)"
        limitations = [
            "90m DEM resolution — fine-scale terrain features not captured.",
            "Slope and roughness estimates are derived, not measured on-site.",
        ]
        potential_error = "±10% on terrain complexity; slope estimate from 90m DEM resolution"
    elif is_real:
        quality = "medium"
        confidence = 65.0
        source = f"OpenTopoData SRTM90m ({sample_count} samples)"
        limitations = [
            f"Only {sample_count} elevation samples — terrain roughness estimate is approximate.",
            "90m DEM resolution may miss local terrain complexity.",
        ]
        potential_error = "±15–25% on terrain complexity with limited sampling"
    else:
        quality = "low"
        confidence = 20.0
        source = "Elevation data unavailable or mock"
        limitations = [
            "Terrain data unavailable — buildability and complexity cannot be assessed.",
            "Civil works cost estimates are unreliable without terrain data.",
        ]
        potential_error = "Terrain assessment not possible without elevation data"

    return EvidenceQualityItem(
        dimension="Terrain",
        source=source,
        quality=quality,
        confidence=round(confidence, 1),
        limitations=limitations,
        potentialError=potential_error,
    )


def _infrastructure_quality(
    nearest_road_m: float | None,
    nearest_powerline_m: float | None,
    settlement_count_15km: int | None,
    sources_debug: dict,
) -> EvidenceQualityItem:
    provider = _provider(sources_debug, "infrastructure")
    is_real = provider == "osm_overpass"
    all_present = all(v is not None for v in [nearest_road_m, nearest_powerline_m, settlement_count_15km])

    if is_real and all_present:
        quality: Literal["high", "medium", "low"] = "high"
        confidence = 78.0
        source = "OpenStreetMap Overpass API (road + powerline + settlements)"
        limitations = [
            "OSM data quality varies by region — rural areas may be under-mapped.",
            "Powerline presence confirmed; grid capacity and voltage class unknown.",
            "Road presence confirmed; weight limits and surface quality unknown.",
        ]
        potential_error = "OSM data may be incomplete — powerline/road coverage varies by region"
    elif is_real:
        quality = "medium"
        confidence = 55.0
        source = "OpenStreetMap Overpass API (partial data)"
        missing = []
        if nearest_road_m is None:
            missing.append("road distance")
        if nearest_powerline_m is None:
            missing.append("powerline distance")
        if settlement_count_15km is None:
            missing.append("settlement count")
        limitations = [
            f"Missing OSM fields: {', '.join(missing)}.",
            "OSM data quality varies by region — rural areas may be under-mapped.",
        ]
        potential_error = "Partial infrastructure data — connection and access cost estimates unreliable"
    else:
        quality = "low"
        confidence = 15.0
        source = "OpenStreetMap Overpass (unavailable)"
        limitations = [
            "Infrastructure data unavailable — OSM query timed out or returned no data.",
            "Road access, grid connection, and population proximity are all unknown.",
        ]
        potential_error = "Infrastructure distances unknown — connection and access costs cannot be estimated"

    return EvidenceQualityItem(
        dimension="Infrastructure",
        source=source,
        quality=quality,
        confidence=round(confidence, 1),
        limitations=limitations,
        potentialError=potential_error,
    )


def _environmental_quality(
    env_score: float | None,
    land_cover_class: str | None,
    in_protected_area: bool | None,
    sources_debug: dict,
) -> EvidenceQualityItem:
    lc_provider = _provider(sources_debug, "land_cover")
    pa_provider = _provider(sources_debug, "protected_area")

    lc_real = lc_provider not in ("unavailable", "mock", "")
    pa_real = pa_provider not in ("unavailable", "mock", "")

    # Environmental data is always a proxy — never "high" quality
    all_present = (
        lc_real and pa_real
        and land_cover_class is not None
        and in_protected_area is not None
    )

    if all_present:
        quality: Literal["high", "medium", "low"] = "medium"
        confidence = 65.0
        source = "ESA WorldCover + WDPA (via CHITTA heuristic)"
        limitations = [
            "Land cover classification at 100m resolution — fine-scale habitats not captured.",
            "Protected area proximity is a heuristic — actual legal boundary not queried.",
            "EIA-required data (habitat surveys, ecological assessments) not included.",
        ]
        potential_error = "Land cover and PA classifications are coarse (100-250m resolution); site surveys required"
    elif lc_real or pa_real:
        quality = "medium"
        confidence = 45.0
        missing = []
        if not lc_real or land_cover_class is None:
            missing.append("land cover class")
        if not pa_real or in_protected_area is None:
            missing.append("protected area status")
        source_parts = []
        if lc_real:
            source_parts.append("ESA WorldCover")
        if pa_real:
            source_parts.append("WDPA")
        source = ", ".join(source_parts) + " (partial)"
        limitations = [
            f"Missing environmental datasets: {', '.join(missing)}.",
            "Partial environmental assessment — risk rating has higher uncertainty.",
        ]
        potential_error = "Environmental constraints partially assessed — field survey essential"
    else:
        quality = "low"
        confidence = 15.0
        source = "Environmental data unavailable"
        limitations = [
            "Land cover and protected area data unavailable.",
            "Environmental constraints cannot be assessed — field survey required.",
        ]
        potential_error = "Environmental constraints unknown — field survey essential before any development commitment"

    return EvidenceQualityItem(
        dimension="Environmental",
        source=source,
        quality=quality,
        confidence=round(confidence, 1),
        limitations=limitations,
        potentialError=potential_error,
    )


def _population_quality(
    settlement_count_15km: int | None,
    sources_debug: dict,
) -> EvidenceQualityItem:
    provider = _provider(sources_debug, "infrastructure")
    is_real = provider == "osm_overpass" and settlement_count_15km is not None

    # Population is always a coarse proxy — never "high" quality for community assessment
    if is_real:
        quality: Literal["high", "medium", "low"] = "medium"
        confidence = 50.0
        source = f"OpenStreetMap settlements within 15 km (n={settlement_count_15km})"
        limitations = [
            "Settlement count is a distance proxy — community attitudes are not captured.",
            "OSM settlement data may be incomplete in rural or developing regions.",
            "Community opposition risk depends on local wind energy history and politics.",
        ]
    else:
        quality = "low"
        confidence = 10.0
        source = "Settlement data unavailable"
        limitations = [
            "No settlement proximity data — social acceptance risk is entirely unknown.",
            "Cannot assess community interface without population data.",
        ]

    return EvidenceQualityItem(
        dimension="Population",
        source=source,
        quality=quality,
        confidence=round(confidence, 1),
        limitations=limitations,
        potentialError="Settlement count is a 15km proximity proxy only — does not reflect community attitudes or opposition capacity",
    )


def _economics_quality(
    eco: "EconomicMetrics | None",
) -> EvidenceQualityItem:
    # Economics are always model estimates — never "high" quality
    if eco is not None and eco.wind_available:
        quality: Literal["high", "medium", "low"] = "medium"
        confidence = 55.0
        source = "CHITTA economics model v1.0 (wind-based CF estimate)"
        limitations = [
            "CAPEX estimates: ±30–50% accuracy at screening stage.",
            "Capacity factor from empirical power curve — not site-specific turbine selection.",
            "Electricity price, discount rate, and project life use fixed defaults.",
            "No financing structure, tax incentives, or grid access costs included.",
        ]
        potential_error = "All financial metrics carry ±30–50% uncertainty — screening only, not bankable"
    elif eco is not None:
        quality = "low"
        confidence = 30.0
        source = "CHITTA economics model v1.0 (conservative default CF)"
        limitations = [
            "Wind speed unavailable — capacity factor assumed at conservative 22%.",
            "All financial metrics are highly uncertain.",
            "CAPEX, LCOE, and payback should not be used for any investment decision.",
        ]
        potential_error = "Economics based on conservative default CF — wind resource must be measured before any financial assessment"
    else:
        quality = "low"
        confidence = 10.0
        source = "Economic assessment unavailable"
        limitations = [
            "Economic feasibility cannot be computed without wind resource data.",
            "All financial metrics are unavailable.",
        ]
        potential_error = "Economics cannot be estimated without wind resource data"

    return EvidenceQualityItem(
        dimension="Economics",
        source=source,
        quality=quality,
        confidence=round(confidence, 1),
        limitations=limitations,
        potentialError=potential_error,
    )


# ── Overall quality aggregation ───────────────────────────────────────────────

def _aggregate_quality(items: list[EvidenceQualityItem]) -> Literal["high", "medium", "low"]:
    levels = [i.quality for i in items]
    if "low" in levels:
        return "low"
    if "medium" in levels:
        return "medium"
    return "high"


def _aggregate_confidence(items: list[EvidenceQualityItem]) -> float:
    # Weighted average: wind 35%, terrain 20%, infra 20%, env 15%, pop 5%, econ 5%
    weights = {"Wind": 0.35, "Terrain": 0.20, "Infrastructure": 0.20,
               "Environmental": 0.15, "Population": 0.05, "Economics": 0.05}
    total_w = 0.0
    total_c = 0.0
    for item in items:
        w = weights.get(item.dimension, 0.0)
        total_w += w
        total_c += w * item.confidence
    if total_w <= 0:
        return 50.0
    return round(total_c / total_w, 1)


# ── Main public function ──────────────────────────────────────────────────────

def compute_evidence_quality(
    wind_speed_at_hub: float | None,
    terrain_score: float | None,
    nearest_road_m: float | None,
    nearest_powerline_m: float | None,
    settlement_count_15km: int | None,
    env_score: float | None,
    land_cover_class: str | None,
    in_protected_area: bool | None,
    eco: "EconomicMetrics | None",
    confidence_score: float,
    sources_debug: dict,
) -> EvidenceQualityReport:
    items = [
        _wind_quality(wind_speed_at_hub, sources_debug),
        _terrain_quality(terrain_score, sources_debug),
        _infrastructure_quality(nearest_road_m, nearest_powerline_m, settlement_count_15km, sources_debug),
        _environmental_quality(env_score, land_cover_class, in_protected_area, sources_debug),
        _population_quality(settlement_count_15km, sources_debug),
        _economics_quality(eco),
    ]

    return EvidenceQualityReport(
        items=items,
        overallQuality=_aggregate_quality(items),
        overallConfidence=_aggregate_confidence(items),
    )
