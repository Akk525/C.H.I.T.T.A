from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.analysis import EnrichedData


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def clamp100(x: float) -> float:
    return max(0.0, min(100.0, x))


def terrain_score_from_complexity(terrain_complexity: float) -> float:
    # Complexity ~0.15..2.0 where lower is better buildability.
    t = clamp01((terrain_complexity - 0.15) / (2.0 - 0.15))
    return clamp100(90.0 - 70.0 * t)


def infrastructure_score(
    nearest_road_m: float | None,
    nearest_powerline_m: float | None,
) -> float:
    """
    Combined road access + grid proximity score.
    Road weight 60%, powerline 40%.
    """
    if nearest_road_m is None:
        road_s = 40.0
    elif nearest_road_m <= 500:
        road_s = 100.0
    elif nearest_road_m <= 5_000:
        road_s = clamp100(100.0 - (nearest_road_m - 500) / 4_500 * 40.0)
    elif nearest_road_m <= 20_000:
        road_s = clamp100(60.0 - (nearest_road_m - 5_000) / 15_000 * 40.0)
    else:
        road_s = max(5.0, 20.0 - (nearest_road_m - 20_000) / 30_000 * 15.0)

    if nearest_powerline_m is None:
        power_s = 35.0
    elif nearest_powerline_m <= 1_000:
        power_s = 100.0
    elif nearest_powerline_m <= 10_000:
        power_s = clamp100(100.0 - (nearest_powerline_m - 1_000) / 9_000 * 50.0)
    elif nearest_powerline_m <= 50_000:
        power_s = clamp100(50.0 - (nearest_powerline_m - 10_000) / 40_000 * 40.0)
    else:
        power_s = 5.0

    return clamp100(0.6 * road_s + 0.4 * power_s)


_LAND_COVER_SCORES: dict[str, float] = {
    "barren": 92.0,
    "grassland": 88.0,
    "shrubland": 82.0,
    "cropland": 68.0,
    "forest": 32.0,
    "wetland": 15.0,
    "urban": 5.0,
}


def land_cover_score(cover_class: str | None) -> float:
    if cover_class is None:
        return 55.0
    return _LAND_COVER_SCORES.get(cover_class, 55.0)


def protected_area_score(in_pa: bool, nearest_pa_m: float | None) -> float:
    if in_pa:
        return 5.0
    if nearest_pa_m is None:
        return 82.0  # no PA found in query radius
    if nearest_pa_m < 1_000:
        return 18.0
    if nearest_pa_m < 5_000:
        return 42.0
    if nearest_pa_m < 15_000:
        return 65.0
    return 85.0


def population_score(settlement_count_15km: int) -> float:
    """Inverse proxy: fewer settlements = less social friction."""
    if settlement_count_15km == 0:
        return 90.0
    if settlement_count_15km <= 2:
        return 75.0
    if settlement_count_15km <= 5:
        return 60.0
    if settlement_count_15km <= 10:
        return 42.0
    return 22.0


def environmental_score(lc_score: float, pa_score: float) -> float:
    return clamp100(0.5 * lc_score + 0.5 * pa_score)


def total_suitability(
    wind_score: float,
    terrain_score: float,
    accessibility_score: float,
    confidence_score: float,
) -> float:
    """Legacy v1 formula — used by heatmap cells."""
    w_wind = 0.40
    w_terrain = 0.25
    w_access = 0.20
    w_conf = 0.15
    return clamp100(
        w_wind * wind_score
        + w_terrain * terrain_score
        + w_access * accessibility_score
        + w_conf * confidence_score
    )


def total_suitability_optional(
    wind_score: float | None,
    terrain_score: float | None,
    accessibility_score: float,
    confidence_score: float,
) -> float | None:
    """Legacy v1 — returns None when both wind and terrain are unavailable."""
    if wind_score is None and terrain_score is None:
        return None
    return total_suitability(
        wind_score if wind_score is not None else 0.0,
        terrain_score if terrain_score is not None else 0.0,
        accessibility_score=accessibility_score,
        confidence_score=confidence_score,
    )


def total_suitability_v2(
    wind_score: float | None,
    terrain_score: float | None,
    infra_score: float | None,
    env_score: float | None,
    pop_score: float | None,
    confidence_score: float,
) -> float | None:
    """
    v2 formula with 6 dimensions.
    Weights: 35% wind, 20% terrain, 15% infrastructure,
             10% environmental, 10% population, 10% confidence.
    Falls back to legacy formula when OSM data is unavailable.
    """
    if wind_score is None and terrain_score is None:
        return None

    if infra_score is None and env_score is None and pop_score is None:
        # No enriched data — fall back to legacy weights with neutral accessibility
        return total_suitability_optional(
            wind_score, terrain_score,
            accessibility_score=55.0,
            confidence_score=confidence_score,
        )

    ws = wind_score if wind_score is not None else 0.0
    ts = terrain_score if terrain_score is not None else 0.0
    is_ = infra_score if infra_score is not None else 50.0
    es = env_score if env_score is not None else 55.0
    ps = pop_score if pop_score is not None else 60.0

    return clamp100(
        0.35 * ws
        + 0.20 * ts
        + 0.15 * is_
        + 0.10 * es
        + 0.10 * ps
        + 0.10 * confidence_score
    )


def apply_economic_nudge(base_total: float | None, economic_score: float | None) -> float | None:
    """
    Adjust the composite suitability score by up to ±8 points based on economic viability.
    Economic score above 50 is a positive signal; below 50 is a drag.
    This is an additive modifier, not a weight replacement, preserving v2.0.0 semantics.
    Formula version 2.1.0.
    """
    if base_total is None or economic_score is None:
        return base_total
    eco_nudge = (economic_score - 50.0) / 50.0 * 8.0
    return clamp100(base_total + eco_nudge)


def total_suitability_weighted(
    wind_score: float | None,
    terrain_score: float | None,
    infra_score: float | None,
    env_score: float | None,
    pop_score: float | None,
    confidence_score: float,
    economic_score: float | None,
    weights: dict[str, float],
) -> float | None:
    """
    Simulation formula: 7-dimension weighted suitability with fully configurable weights.
    Weights must be pre-normalised (sum to 1.0). Economic is a proper weight, not a nudge.
    """
    if wind_score is None and terrain_score is None:
        return None

    ws = wind_score if wind_score is not None else 0.0
    ts = terrain_score if terrain_score is not None else 0.0
    is_ = infra_score if infra_score is not None else 50.0
    es = env_score if env_score is not None else 55.0
    ps = pop_score if pop_score is not None else 60.0
    eco = economic_score if economic_score is not None else 50.0

    return clamp100(
        weights.get("wind", 0.0) * ws
        + weights.get("terrain", 0.0) * ts
        + weights.get("infrastructure", 0.0) * is_
        + weights.get("environmental", 0.0) * es
        + weights.get("population", 0.0) * ps
        + weights.get("confidence", 0.0) * confidence_score
        + weights.get("economic", 0.0) * eco
    )


def compute_scores_from_enriched(
    metrics: dict[str, Any],
    enriched: "EnrichedData",
) -> dict[str, Any]:
    """
    Compute all derived scores from metrics_fragment + EnrichedData.
    Returns a flat dict with named score fields and intermediate values.
    Used by both the single-site route and the prospecting service.
    """
    wind_score: float | None = metrics.get("windScore")
    terrain_score: float | None = metrics.get("terrainScore")
    confidence_score: float = float(metrics.get("confidenceScore") or 0)

    infra_data = enriched.get("infrastructure")
    lc_data = enriched.get("land_cover")
    pa_data = enriched.get("protected_area")

    infra_s: float | None = None
    nearest_road: float | None = None
    nearest_power: float | None = None
    settlement_count: int | None = None
    if infra_data is not None:
        nearest_road = infra_data.get("nearest_road_m")
        nearest_power = infra_data.get("nearest_powerline_m")
        settlement_count = infra_data.get("settlement_count_15km")
        infra_s = infrastructure_score(nearest_road, nearest_power)

    lc_score: float | None = None
    lc_class: str | None = None
    if lc_data is not None:
        lc_class = lc_data.get("cover_class")
        lc_score = land_cover_score(lc_class)

    pa_score: float | None = None
    pa_risk: str | None = None
    in_pa: bool | None = None
    nearest_pa_m: float | None = None
    if pa_data is not None:
        in_pa = pa_data.get("in_protected_area", False)
        nearest_pa_m = pa_data.get("nearest_pa_m")
        pa_score = protected_area_score(in_pa, nearest_pa_m)
        pa_risk = pa_data.get("biodiversity_risk")

    env_s: float | None = None
    if lc_score is not None and pa_score is not None:
        env_s = environmental_score(lc_score, pa_score)
    elif lc_score is not None:
        env_s = lc_score
    elif pa_score is not None:
        env_s = pa_score

    pop_s: float | None = None
    if settlement_count is not None:
        pop_s = population_score(settlement_count)

    total = total_suitability_v2(
        wind_score=wind_score,
        terrain_score=terrain_score,
        infra_score=infra_s,
        env_score=env_s,
        pop_score=pop_s,
        confidence_score=confidence_score,
    )

    return {
        "wind_score": wind_score,
        "terrain_score": terrain_score,
        "confidence_score": confidence_score,
        "infra_s": infra_s,
        "lc_score": lc_score,
        "lc_class": lc_class,
        "pa_score": pa_score,
        "pa_risk": pa_risk,
        "in_pa": in_pa,
        "nearest_pa_m": nearest_pa_m,
        "env_s": env_s,
        "pop_s": pop_s,
        "total": total,
        "nearest_road": nearest_road,
        "nearest_power": nearest_power,
        "settlement_count": settlement_count,
    }
