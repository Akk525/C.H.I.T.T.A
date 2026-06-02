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
    total: float | None,
    wind: float | None,
    terrain: float | None,
    accessibility: float,
    confidence: float,
    elevation_m: float | None,
    terrain_complexity: float | None,
    data_sources: list[str] | None = None,
) -> dict[str, object]:
    wind_unavailable = wind is None
    terrain_unavailable = terrain is None

    if total is None:
        exec_summary = (
            "Primary wind and elevation data sources returned no usable data for this location. "
            "Scores are not computed until NASA POWER and OpenTopoData respond successfully. "
            "Accessibility remains a mock proxy until OSM integration is enabled."
        )
    else:
        overall = _band(total)
        wind_band = _band(wind) if wind is not None else "unavailable"
        terrain_band = _band(terrain) if terrain is not None else "unavailable"
        exec_summary = (
            f"This candidate site screens as {overall} for early-stage wind development. "
            f"Wind potential is {wind_band}, terrain buildability is {terrain_band}, "
            f"and accessibility is {_band(accessibility)}. "
            "These results are heuristic and intended to guide where to invest deeper analysis."
        )

    strengths: list[str] = []
    risks: list[str] = []
    recs: list[str] = []

    if wind_unavailable:
        risks.append("Wind data unavailable — NASA POWER did not return usable data for this coordinate.")
    elif wind >= 70:
        strengths.append("Wind score suggests favorable regional potential for generation.")
    else:
        risks.append("Wind signal is not yet strong; confirm with NASA POWER or on-site met data.")

    if terrain_unavailable:
        risks.append("Elevation data unavailable — OpenTopoData did not return usable samples for this coordinate.")
    elif terrain >= 70:
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
        "Confidence reflects which real data providers returned usable results.",
        "When wind or elevation is unavailable, composite suitability is not computed.",
    ]
    if elevation_m is not None and terrain_complexity is not None:
        conf_notes.append(
            f"Current heuristics: elevation≈{elevation_m:.0f}m, terrainComplexity≈{terrain_complexity:.2f}."
        )
    conf_notes.append(f"Composite confidence score: {confidence:.0f}/100.")

    return {
        "executiveSummary": exec_summary,
        "siteStrengths": strengths or ["No strong positives detected under current heuristics."],
        "risks": risks or ["No major red flags detected under current heuristics."],
        "recommendations": recs,
        "confidenceNotes": conf_notes,
        "dataSources": data_sources
        or [
            "Wind: NASA POWER",
            "Elevation: OpenTopoData (SRTM90m)",
            "Accessibility: mock (OSM integration planned)",
        ],
    }
