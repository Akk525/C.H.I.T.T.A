from __future__ import annotations


def _band(v: float) -> str:
    if v >= 80:
        return "strong"
    if v >= 60:
        return "promising"
    if v >= 40:
        return "mixed"
    return "challenging"


def build_report(
    *,
    total: float,
    wind: float,
    terrain: float,
    accessibility: float,
    confidence: float,
    elevation_m: float,
    terrain_complexity: float,
    data_sources: list[str] | None = None,
) -> dict[str, object]:
    overall = _band(total)

    exec_summary = (
        f"This candidate site screens as {overall} for early-stage wind development. "
        f"Wind potential is {_band(wind)}, terrain buildability is {_band(terrain)}, "
        f"and accessibility is {_band(accessibility)}. "
        "These results are heuristic and intended to guide where to invest deeper analysis."
    )

    strengths: list[str] = []
    risks: list[str] = []
    recs: list[str] = []

    if wind >= 70:
        strengths.append("Wind score suggests favorable regional potential for generation.")
    else:
        risks.append("Wind signal is not yet strong; confirm with NASA POWER or on-site met data.")

    if terrain >= 70:
        strengths.append("Terrain appears reasonably buildable for access roads and foundations.")
    else:
        risks.append(
            "Terrain complexity may increase civil works cost; validate slope/roughness from elevation tiles."
        )

    if accessibility >= 65:
        strengths.append("Accessibility proxy suggests fewer logistics constraints.")
    else:
        risks.append("Accessibility may be constrained; validate road and grid proximity using OSM.")

    recs.extend(
        [
            "Pull a 10–20 year wind climatology from NASA POWER and compute seasonal variability.",
            "Fetch elevation + slope (OpenTopoData or local DEM tiles) and quantify grade constraints.",
            "Use OSM to estimate distance-to-road and distance-to-transmission, then rerun scoring.",
        ]
    )

    conf_notes = [
        "Confidence is limited because this MVP uses mock providers.",
        "When real providers are enabled, confidence should reflect data coverage, resolution, and recency.",
        f"Current heuristics: elevation≈{elevation_m:.0f}m, terrainComplexity≈{terrain_complexity:.2f}.",
        f"Composite confidence score: {confidence:.0f}/100.",
    ]

    return {
        "executiveSummary": exec_summary,
        "siteStrengths": strengths or ["No strong positives detected under current heuristics."],
        "risks": risks or ["No major red flags detected under current heuristics."],
        "recommendations": recs,
        "confidenceNotes": conf_notes,
        "dataSources": data_sources
        or [
            "Wind: NASA POWER (planned)",
            "Elevation: OpenTopoData (planned)",
            "Accessibility: OSM (planned)",
        ],
    }

