from __future__ import annotations


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def clamp100(x: float) -> float:
    return max(0.0, min(100.0, x))


def terrain_score_from_complexity(terrain_complexity: float) -> float:
    # Complexity ~0.15..2.0 where lower is better buildability.
    # Convert to a score where 0.15 => ~90, 2.0 => ~20.
    t = clamp01((terrain_complexity - 0.15) / (2.0 - 0.15))
    return clamp100(90.0 - 70.0 * t)


def confidence_score_mock() -> float:
    # MVP mock: fairly conservative until real data providers wired.
    return 62.0


def total_suitability(
    wind_score: float,
    terrain_score: float,
    accessibility_score: float,
    confidence_score: float,
) -> float:
    # Weighted composite. Keep weights easy to tune later.
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
    """Return None when both wind and terrain scores are unavailable."""
    if wind_score is None and terrain_score is None:
        return None
    return total_suitability(
        wind_score if wind_score is not None else 0.0,
        terrain_score if terrain_score is not None else 0.0,
        accessibility_score=accessibility_score,
        confidence_score=confidence_score,
    )

