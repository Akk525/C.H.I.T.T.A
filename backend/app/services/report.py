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
    confidence: float,
    elevation_m: float | None,
    terrain_complexity: float | None,
    infra_score: float | None = None,
    lc_class: str | None = None,
    pa_risk: str | None = None,
    in_pa: bool | None = None,
    pop_score: float | None = None,
    data_sources: list[str] | None = None,
    coordinator_decision: str | None = None,
    # Legacy compat
    accessibility: float | None = None,
) -> dict[str, object]:
    wind_unavailable = wind is None
    terrain_unavailable = terrain is None

    # Use coordinator finalDecision if available, else fall back to score-band
    decision_label = coordinator_decision or (_band(total) if total is not None else None)

    if total is None and decision_label in {None, "caution", "poor"}:
        exec_summary = (
            "Primary wind and elevation data returned no usable results for this location. "
            "Scores are withheld until NASA POWER and OpenTopoData respond successfully. "
            "OSM infrastructure and environmental data may still be available."
        )
    else:
        wind_band = _band(wind) if wind is not None else "unavailable"
        terrain_band = _band(terrain) if terrain is not None else "unavailable"
        infra_band = _band(infra_score) if infra_score is not None else None
        label = decision_label or _band(total)  # type: ignore[arg-type]
        exec_summary = (
            f"This candidate site screens as {label} for early-stage wind development. "
            f"Wind potential is {wind_band}, terrain buildability is {terrain_band}"
        )
        if infra_band:
            exec_summary += f", and infrastructure access is {infra_band}"
        exec_summary += ". These results are heuristic and intended to guide where to invest deeper analysis."

    strengths: list[str] = []
    risks: list[str] = []
    recs: list[str] = []

    # Wind
    if wind_unavailable:
        risks.append("Wind data unavailable — NASA POWER did not return usable data for this coordinate.")
    elif wind >= 70:  # type: ignore[operator]
        strengths.append(f"Wind potential is strong (score {wind:.0f}/100) — favourable for generation.")
    elif wind >= 50:  # type: ignore[operator]
        strengths.append(f"Wind signal is moderate (score {wind:.0f}/100) — viable with detailed climatology.")
    else:
        risks.append("Wind signal is below typical commercial thresholds; confirm with on-site met data.")

    # Terrain
    if terrain_unavailable:
        risks.append("Elevation data unavailable — OpenTopoData did not return usable samples.")
    elif terrain >= 70:  # type: ignore[operator]
        strengths.append("Terrain appears buildable — low slope and roughness reduce civil works cost.")
    else:
        risks.append("Terrain complexity may increase civil works cost; validate slope from elevation tiles.")

    # Infrastructure
    if infra_score is not None:
        if infra_score >= 70:
            strengths.append(f"Road and grid access is good (score {infra_score:.0f}/100) — logistics look manageable.")
        elif infra_score >= 45:
            risks.append("Road or transmission access is moderate; road upgrade or line extension may be needed.")
        else:
            risks.append("Infrastructure access is poor — significant road build or grid extension likely required.")
    else:
        recs.append("Use OSM to estimate distance-to-road and distance-to-transmission, then rerun scoring.")

    # Environmental / land cover
    if lc_class is not None:
        lc_label = lc_class.replace("_", " ").title()
        if lc_class in {"barren", "grassland", "shrubland"}:
            strengths.append(f"Land cover ({lc_label}) is favourable — lower permitting friction expected.")
        elif lc_class in {"cropland"}:
            risks.append(f"Land cover is {lc_label} — land acquisition and compensation agreements needed.")
        elif lc_class in {"forest", "wetland"}:
            risks.append(f"Land cover is {lc_label} — high permitting sensitivity; ecological impact assessment required.")
        elif lc_class == "urban":
            risks.append("Urban land cover detected — wind development highly constrained.")

    # Protected areas
    if in_pa is True:
        risks.append("Site appears to overlap a mapped protected area — development almost certainly prohibited.")
    elif pa_risk == "high":
        risks.append("A protected area is within 5 km — heightened regulatory and ecological scrutiny expected.")
    elif pa_risk == "medium":
        risks.append("A protected area is within 15 km — include buffer zone analysis in the feasibility study.")
    elif pa_risk == "low" and infra_score is not None:
        strengths.append("No protected areas detected within 25 km — lower ecological constraint.")

    # Population proxy
    if pop_score is not None:
        if pop_score >= 75:
            strengths.append("Low settlement density — reduced social friction and noise/visual impact risk.")
        elif pop_score <= 45:
            risks.append("Multiple settlements within 15 km — community engagement and noise studies required.")

    # Recommendations
    recs.extend([
        "Pull a 10–20 year wind climatology from NASA POWER (WS100M) and compute seasonal variability.",
        "Fetch high-resolution slope data (OpenTopoData or local DEM) and validate grade constraints.",
    ])
    if infra_score is None:
        recs.append("Use OSM Overpass to verify road and transmission proximity before committing resources.")
    if pa_risk in {"high", "medium"}:
        recs.append("Obtain WDPA protected area boundaries and verify setback compliance.")
    recs.append("Commission a met mast or use satellite-derived wind resource data for bankable assessment.")

    conf_notes = [
        "Confidence reflects which real data providers returned usable results (v2.0.0 formula).",
        "When wind or elevation is unavailable, composite suitability is not computed.",
    ]
    if elevation_m is not None and terrain_complexity is not None:
        conf_notes.append(
            f"Terrain heuristics: elevation≈{elevation_m:.0f}m, complexity≈{terrain_complexity:.2f}."
        )
    conf_notes.append(f"Composite confidence score: {confidence:.0f}/100.")

    return {
        "executiveSummary": exec_summary,
        "siteStrengths": strengths or ["No strong positives detected under current heuristics."],
        "risks": risks or ["No major red flags detected under current heuristics."],
        "recommendations": recs,
        "confidenceNotes": conf_notes,
        "dataSources": data_sources or [
            "Wind: NASA POWER (WS10M/WS50M/WS100M)",
            "Elevation: OpenTopoData (SRTM90m)",
            "Infrastructure: OpenStreetMap (Overpass API)",
        ],
    }
