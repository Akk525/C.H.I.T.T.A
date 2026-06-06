"""
Risk Register Engine for CHITTA.

Deterministic rules that map existing site metrics to a structured risk register.
Missing data raises uncertainty — it does not silently pass.
No LLM calls. No external API calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.services.economics import EconomicMetrics
    from app.services.fitness import FitnessResult


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class RiskEvidence:
    label: str
    value: str
    source: str


@dataclass
class RiskItem:
    category: str
    level: Literal["low", "medium", "high", "unknown"]
    confidence: float
    knowledgeClass: Literal["known_known", "known_unknown", "unknown_known", "unknown_unknown"]
    summary: str
    evidence: list[RiskEvidence]
    potentialFatalFlaw: bool
    recommendedNextStep: str


@dataclass
class FatalFlaw:
    id: str
    category: str
    severity: Literal["warning", "critical"]
    description: str
    evidence: str
    nextStep: str


@dataclass
class RiskRegisterResult:
    categories: list[RiskItem]
    fatalFlaws: list[FatalFlaw]
    fatalFlawCount: int
    criticalFatalFlawCount: int


@dataclass
class DevelopmentOutlookResult:
    developmentOutlook: Literal["promising", "fragile", "high_risk", "not_recommended"]
    narrativeSummary: str
    nextInvestigationPriorities: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ev(label: str, value: str, source: str) -> RiskEvidence:
    return RiskEvidence(label=label, value=value, source=source)


def _fmt(v: float | None, decimals: int = 1, suffix: str = "") -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}{suffix}"


# ── Nine risk category functions ──────────────────────────────────────────────

def _wind_resource_risk(
    wind_score: float | None,
    wind_speed_at_hub: float | None,
    confidence_score: float,
) -> RiskItem:
    evidence: list[RiskEvidence] = [
        _ev("Wind score", _fmt(wind_score, 1, "/100"), "CHITTA v2.1"),
        _ev("Mean speed at hub", _fmt(wind_speed_at_hub, 2, " m/s"), "NASA POWER"),
        _ev("Data confidence", _fmt(confidence_score, 1, "/100"), "CHITTA v2.1"),
    ]

    if wind_speed_at_hub is None:
        return RiskItem(
            category="Wind Resource",
            level="unknown",
            confidence=30.0,
            knowledgeClass="known_unknown",
            summary="Wind speed data unavailable — viability cannot be assessed.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Commission a preliminary wind resource assessment or obtain nearest meteorological station data.",
        )

    if wind_speed_at_hub < 5.0:
        return RiskItem(
            category="Wind Resource",
            level="high",
            confidence=85.0,
            knowledgeClass="known_known",
            summary=f"Wind speed {wind_speed_at_hub:.2f} m/s is below the commercial viability threshold of 5.0 m/s.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Verify with on-site measurements. This site is likely unviable for commercial wind.",
        )

    if wind_speed_at_hub < 6.5:
        return RiskItem(
            category="Wind Resource",
            level="medium",
            confidence=75.0 if confidence_score >= 60 else 55.0,
            knowledgeClass="known_known" if confidence_score >= 60 else "unknown_known",
            summary=f"Wind speed {wind_speed_at_hub:.2f} m/s is marginal — economics will be sensitive to resource uncertainty.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Obtain at least 12 months of on-site wind data before committing to further development.",
        )

    return RiskItem(
        category="Wind Resource",
        level="low",
        confidence=85.0 if confidence_score >= 70 else 65.0,
        knowledgeClass="known_known",
        summary=f"Wind speed {wind_speed_at_hub:.2f} m/s indicates a commercially viable resource.",
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep="Validate resource estimate with on-site measurement campaign before bankable assessment.",
    )


def _grid_connection_risk(nearest_powerline_m: float | None) -> RiskItem:
    evidence: list[RiskEvidence] = [
        _ev("Distance to nearest powerline", _fmt(nearest_powerline_m, 0, " m"), "OpenStreetMap Overpass"),
    ]

    if nearest_powerline_m is None:
        return RiskItem(
            category="Grid Connection",
            level="unknown",
            confidence=20.0,
            knowledgeClass="known_unknown",
            summary="Grid infrastructure data unavailable — connection cost and feasibility unknown.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Contact the regional transmission operator (RTO/DSO) to determine nearest connection point and capacity.",
        )

    km = nearest_powerline_m / 1000.0

    if nearest_powerline_m > 50_000:
        return RiskItem(
            category="Grid Connection",
            level="high",
            confidence=85.0,
            knowledgeClass="known_known",
            summary=f"Nearest powerline {km:.1f} km away — connection cost likely prohibitive without new transmission infrastructure.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Obtain grid connection study from RTO. Consider whether a grid extension is economically justified.",
        )

    if nearest_powerline_m > 20_000:
        return RiskItem(
            category="Grid Connection",
            level="high",
            confidence=80.0,
            knowledgeClass="known_known",
            summary=f"Grid connection {km:.1f} km away — significant connection cost expected.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Commission a grid connection study to quantify cost and timeline before progressing.",
        )

    if nearest_powerline_m > 10_000:
        return RiskItem(
            category="Grid Connection",
            level="medium",
            confidence=75.0,
            knowledgeClass="known_known",
            summary=f"Grid connection {km:.1f} km away — moderate connection cost likely but potentially manageable.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Confirm grid capacity and connection point with the network operator.",
        )

    return RiskItem(
        category="Grid Connection",
        level="low",
        confidence=80.0,
        knowledgeClass="known_known",
        summary=f"Grid infrastructure {km:.1f} km away — connection appears accessible.",
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep="Confirm grid capacity availability with the local distribution network operator.",
    )


def _land_access_risk(
    nearest_road_m: float | None,
    land_cover_class: str | None,
    in_protected_area: bool | None,
) -> RiskItem:
    evidence: list[RiskEvidence] = [
        _ev("Distance to nearest road", _fmt(nearest_road_m, 0, " m"), "OpenStreetMap Overpass"),
        _ev("Land cover class", land_cover_class or "N/A", "ESA WorldCover"),
        _ev("Inside protected area", ("yes" if in_protected_area else "no") if in_protected_area is not None else "N/A", "CHITTA v2.1"),
    ]

    # Start with road-based level
    if nearest_road_m is None:
        level: Literal["low", "medium", "high", "unknown"] = "unknown"
        kc: Literal["known_known", "known_unknown", "unknown_known", "unknown_unknown"] = "known_unknown"
        summary = "Road access data unavailable — construction and O&M logistics cannot be assessed."
        step = "Assess road access using satellite imagery and local authority records before site visit."
    elif nearest_road_m > 30_000:
        level = "high"
        kc = "known_known"
        summary = f"Nearest road {nearest_road_m/1000:.1f} km away — significant access infrastructure required."
        step = "Evaluate cost of access road construction; this may add 10–25% to CAPEX."
    elif nearest_road_m > 10_000:
        level = "medium"
        kc = "known_known"
        summary = f"Nearest road {nearest_road_m/1000:.1f} km — access road upgrade or extension likely needed."
        step = "Survey existing tracks and assess heavy vehicle access requirements for construction phase."
    else:
        level = "low"
        kc = "known_known"
        summary = f"Road access {nearest_road_m/1000:.1f} km — reasonable for construction logistics."
        step = "Confirm road capacity and weight limits for heavy turbine component delivery."

    # Bump up if land cover is problematic
    if land_cover_class in ("forest", "urban") and level in ("low", "medium"):
        level = "high" if level == "medium" else "medium"
        summary += f" Land cover ({land_cover_class}) adds additional access complexity."

    if in_protected_area:
        level = "high"
        summary += " Protected area status restricts land access and likely requires special permits."

    return RiskItem(
        category="Land Access",
        level=level,
        confidence=70.0 if nearest_road_m is not None else 25.0,
        knowledgeClass=kc,
        summary=summary,
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep=step,
    )


def _environmental_risk(
    env_score: float | None,
    land_cover_class: str | None,
    protected_area_risk: str | None,
    in_protected_area: bool | None,
) -> RiskItem:
    evidence: list[RiskEvidence] = [
        _ev("Environmental score", _fmt(env_score, 1, "/100"), "CHITTA v2.1"),
        _ev("Land cover class", land_cover_class or "N/A", "ESA WorldCover"),
        _ev("Protected area risk", protected_area_risk or "N/A", "CHITTA biodiversity heuristic"),
        _ev("Inside protected area", ("yes" if in_protected_area else "no") if in_protected_area is not None else "N/A", "CHITTA v2.1"),
    ]

    if in_protected_area:
        return RiskItem(
            category="Environmental Constraints",
            level="high",
            confidence=90.0,
            knowledgeClass="known_known",
            summary="Site is inside a designated protected area — development is likely prohibited.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Obtain legal opinion on permitted uses. Expect this to be a project-stopper without legal exception.",
        )

    if protected_area_risk == "high":
        return RiskItem(
            category="Environmental Constraints",
            level="high",
            confidence=80.0,
            knowledgeClass="known_known",
            summary="High proximity to protected areas — environmental impact assessment will face significant scrutiny.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Commission an Environmental Impact Assessment (EIA) early. Engage with conservation authorities.",
        )

    if land_cover_class == "wetland":
        return RiskItem(
            category="Environmental Constraints",
            level="high",
            confidence=80.0,
            knowledgeClass="known_known",
            summary="Wetland land cover — strict environmental protections likely apply.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Consult environmental legislation for wetland development restrictions before proceeding.",
        )

    if env_score is not None and env_score < 20:
        return RiskItem(
            category="Environmental Constraints",
            level="high",
            confidence=75.0,
            knowledgeClass="known_known",
            summary=f"Environmental score {env_score:.0f}/100 — multiple environmental constraints present.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Environmental constraints appear severe. Conduct detailed habitat and biodiversity survey.",
        )

    if env_score is not None and env_score < 40:
        return RiskItem(
            category="Environmental Constraints",
            level="medium",
            confidence=70.0,
            knowledgeClass="known_known",
            summary=f"Environmental score {env_score:.0f}/100 — moderate constraints present.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Commission habitat survey and review local environmental planning policy.",
        )

    if env_score is None:
        return RiskItem(
            category="Environmental Constraints",
            level="unknown",
            confidence=20.0,
            knowledgeClass="unknown_unknown",
            summary="Environmental data unavailable — constraint level cannot be determined.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Commission desktop environmental review using satellite imagery and national biodiversity datasets.",
        )

    return RiskItem(
        category="Environmental Constraints",
        level="low",
        confidence=70.0,
        knowledgeClass="known_known",
        summary=f"Environmental score {env_score:.0f}/100 — no major environmental constraints identified from public data.",
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep="Confirm with site visit and consult local biodiversity records before EIA scoping.",
    )


def _community_risk(settlement_count_15km: int | None) -> RiskItem:
    evidence: list[RiskEvidence] = [
        _ev("Settlements within 15 km", str(settlement_count_15km) if settlement_count_15km is not None else "N/A", "OpenStreetMap Overpass"),
    ]

    if settlement_count_15km is None:
        return RiskItem(
            category="Community / Social Acceptance",
            level="unknown",
            confidence=15.0,
            knowledgeClass="unknown_unknown",
            summary="Settlement data unavailable — community acceptance risk cannot be assessed from public data.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Conduct desktop study of local population centres and existing wind development history in the region.",
        )

    if settlement_count_15km > 10:
        return RiskItem(
            category="Community / Social Acceptance",
            level="high",
            confidence=65.0,
            knowledgeClass="unknown_known",
            summary=f"{settlement_count_15km} settlements within 15 km — high community interface; organised opposition is a known risk.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Initiate stakeholder mapping and early community engagement. Consider a community benefit fund.",
        )

    if settlement_count_15km > 5:
        return RiskItem(
            category="Community / Social Acceptance",
            level="medium",
            confidence=60.0,
            knowledgeClass="unknown_known",
            summary=f"{settlement_count_15km} settlements within 15 km — moderate community interface expected.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Conduct early stakeholder engagement and noise/shadow flicker pre-assessment.",
        )

    return RiskItem(
        category="Community / Social Acceptance",
        level="low",
        confidence=60.0,
        knowledgeClass="unknown_known",
        summary=f"Low settlement density ({settlement_count_15km} within 15 km) — community opposition risk appears low.",
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep="Confirm with local authority consultation and check for any known objections in planning records.",
    )


def _permitting_risk(
    in_protected_area: bool | None,
    land_cover_class: str | None,
    protected_area_risk: str | None,
) -> RiskItem:
    evidence: list[RiskEvidence] = [
        _ev("Inside protected area", ("yes" if in_protected_area else "no") if in_protected_area is not None else "N/A", "CHITTA v2.1"),
        _ev("Land cover class", land_cover_class or "N/A", "ESA WorldCover"),
        _ev("Protected area risk", protected_area_risk or "N/A", "CHITTA biodiversity heuristic"),
    ]

    if in_protected_area:
        return RiskItem(
            category="Permitting / Regulatory",
            level="high",
            confidence=90.0,
            knowledgeClass="known_known",
            summary="Protected area status — wind energy development is likely legally prohibited or severely restricted.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Obtain legal opinion on development rights. Consult with the protected area authority.",
        )

    if land_cover_class == "urban":
        return RiskItem(
            category="Permitting / Regulatory",
            level="high",
            confidence=85.0,
            knowledgeClass="known_known",
            summary="Urban land cover — planning consent for wind energy in or near urban areas is typically very difficult.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Consult local planning policy. Wind energy in urban zones almost always requires a policy exception.",
        )

    if protected_area_risk == "high":
        return RiskItem(
            category="Permitting / Regulatory",
            level="high",
            confidence=75.0,
            knowledgeClass="known_known",
            summary="High proximity to protected areas creates significant permitting risk.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Engage with planning authority early for pre-application advice. EIA screening likely required.",
        )

    if in_protected_area is None and protected_area_risk is None:
        return RiskItem(
            category="Permitting / Regulatory",
            level="unknown",
            confidence=20.0,
            knowledgeClass="known_unknown",
            summary="Protected area and land designation data unavailable — permitting risk unknown.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Review national and regional planning policy maps for wind energy designations.",
        )

    return RiskItem(
        category="Permitting / Regulatory",
        level="medium",
        confidence=55.0,
        knowledgeClass="unknown_known",
        summary="No critical designation identified from public data, but permitting pathway must be confirmed.",
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep="Submit pre-application consultation to the local planning authority to confirm policy position.",
    )


def _economics_risk(eco: "EconomicMetrics | None") -> RiskItem:
    if eco is None:
        return RiskItem(
            category="Economics",
            level="unknown",
            confidence=15.0,
            knowledgeClass="known_unknown",
            summary="Economic assessment could not be computed — wind resource data insufficient.",
            evidence=[_ev("Economic score", "N/A", "CHITTA economics v1.0")],
            potentialFatalFlaw=True,
            recommendedNextStep="Obtain wind resource data to enable a preliminary economic screening.",
        )

    evidence: list[RiskEvidence] = [
        _ev("Economic score", _fmt(eco.economic_score, 1, "/100"), "CHITTA economics v1.0"),
        _ev("Estimated LCOE", _fmt(eco.lcoe_usd_per_mwh, 1, " USD/MWh"), "CHITTA economics v1.0"),
        _ev("Estimated payback", _fmt(eco.payback_years, 1, " years") if eco.payback_years else "Negative NPV", "CHITTA economics v1.0"),
        _ev("Capacity factor", _fmt(eco.capacity_factor * 100, 1, "%"), "CHITTA economics v1.0"),
    ]

    if eco.payback_years is None:
        return RiskItem(
            category="Economics",
            level="high",
            confidence=75.0,
            knowledgeClass="known_known",
            summary="Project shows negative net present value under current assumptions — not economically viable.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Review electricity price assumptions or consider smaller project scale. Verify wind resource.",
        )

    if eco.economic_score < 20:
        return RiskItem(
            category="Economics",
            level="high",
            confidence=75.0,
            knowledgeClass="known_known",
            summary=f"Economic score {eco.economic_score:.0f}/100 — LCOE {eco.lcoe_usd_per_mwh:.1f} USD/MWh and payback {eco.payback_years:.1f} years are very poor.",
            evidence=evidence,
            potentialFatalFlaw=True,
            recommendedNextStep="Economics indicate this site is not commercially viable under standard assumptions.",
        )

    if eco.economic_score < 40:
        return RiskItem(
            category="Economics",
            level="high",
            confidence=70.0,
            knowledgeClass="known_known",
            summary=f"Economic score {eco.economic_score:.0f}/100 — project economics are marginal and highly sensitive to assumption changes.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Explore subsidy availability and electricity offtake options. Economics need significant improvement.",
        )

    if eco.economic_score < 55:
        return RiskItem(
            category="Economics",
            level="medium",
            confidence=65.0,
            knowledgeClass="known_known",
            summary=f"Economic score {eco.economic_score:.0f}/100 — viable but sensitive to wind resource and price assumptions.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Conduct sensitivity analysis on electricity price, CAPEX, and capacity factor assumptions.",
        )

    return RiskItem(
        category="Economics",
        level="low",
        confidence=65.0,
        knowledgeClass="known_known",
        summary=f"Economic score {eco.economic_score:.0f}/100 — preliminary economics appear favourable.",
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep="Commission a bankable financial model once wind resource is confirmed by measurement campaign.",
    )


def _constructability_risk(
    terrain_score: float | None,
    terrain_complexity: float | None,
    slope_pct: float | None,
    nearest_road_m: float | None,
) -> RiskItem:
    evidence: list[RiskEvidence] = [
        _ev("Terrain score", _fmt(terrain_score, 1, "/100"), "CHITTA v2.1"),
        _ev("Terrain complexity", _fmt(terrain_complexity, 2), "OpenTopoData SRTM90m"),
        _ev("Slope", _fmt(slope_pct, 1, "%"), "OpenTopoData SRTM90m"),
        _ev("Nearest road", _fmt(nearest_road_m, 0, " m"), "OpenStreetMap Overpass"),
    ]

    high_signals = 0
    if terrain_score is not None and terrain_score < 30:
        high_signals += 1
    if slope_pct is not None and slope_pct > 15:
        high_signals += 1
    if terrain_complexity is not None and terrain_complexity > 1.5:
        high_signals += 1
    if nearest_road_m is not None and nearest_road_m > 20_000:
        high_signals += 1

    if terrain_score is None and terrain_complexity is None:
        return RiskItem(
            category="Constructability",
            level="unknown",
            confidence=20.0,
            knowledgeClass="known_unknown",
            summary="Terrain data unavailable — constructability and civil works cost cannot be assessed.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Obtain terrain data and conduct a desktop constructability review.",
        )

    if high_signals >= 2:
        return RiskItem(
            category="Constructability",
            level="high",
            confidence=75.0,
            knowledgeClass="known_known",
            summary="Terrain complexity and/or access constraints indicate significant civil works challenges.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Commission geotechnical and civil engineering assessment. Expect CAPEX premium of 20–35%.",
        )

    if high_signals == 1:
        return RiskItem(
            category="Constructability",
            level="medium",
            confidence=70.0,
            knowledgeClass="known_known",
            summary="Some constructability challenges present — site is buildable but with additional cost.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Conduct desktop engineering review and include terrain risk in CAPEX contingency.",
        )

    return RiskItem(
        category="Constructability",
        level="low",
        confidence=70.0,
        knowledgeClass="known_known",
        summary="Terrain and access conditions appear suitable for standard wind turbine construction.",
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep="Confirm with desktop geotechnical review before committing to detailed design.",
    )


def _data_quality_risk(
    confidence_score: float,
    wind_speed_at_hub: float | None,
    nearest_powerline_m: float | None,
    nearest_road_m: float | None,
    settlement_count_15km: int | None,
) -> RiskItem:
    missing_count = sum([
        wind_speed_at_hub is None,
        nearest_powerline_m is None,
        nearest_road_m is None,
        settlement_count_15km is None,
    ])

    evidence: list[RiskEvidence] = [
        _ev("Overall confidence score", _fmt(confidence_score, 1, "/100"), "CHITTA v2.1"),
        _ev("Missing key datasets", str(missing_count), "CHITTA v2.1"),
    ]

    if confidence_score < 40 or missing_count >= 3:
        return RiskItem(
            category="Data Quality / Unknowns",
            level="high",
            confidence=90.0,
            knowledgeClass="known_unknown",
            summary=f"Confidence score {confidence_score:.0f}/100 — {missing_count} key datasets missing. Analysis has significant uncertainty.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Do not advance without improving data quality. Prioritise wind measurement and infrastructure surveys.",
        )

    if confidence_score < 60 or missing_count >= 2:
        return RiskItem(
            category="Data Quality / Unknowns",
            level="medium",
            confidence=85.0,
            knowledgeClass="known_unknown",
            summary=f"Confidence score {confidence_score:.0f}/100 — some key datasets missing or estimated. Results should be treated with caution.",
            evidence=evidence,
            potentialFatalFlaw=False,
            recommendedNextStep="Collect missing data before committing development resources. Check infrastructure data with RTO and local authority.",
        )

    return RiskItem(
        category="Data Quality / Unknowns",
        level="low",
        confidence=85.0,
        knowledgeClass="known_known",
        summary=f"Confidence score {confidence_score:.0f}/100 — key data sources available and used.",
        evidence=evidence,
        potentialFatalFlaw=False,
        recommendedNextStep="Validate public data assumptions with on-site measurements before detailed feasibility.",
    )


# ── Fatal flaw extraction ─────────────────────────────────────────────────────

def _extract_fatal_flaws(categories: list[RiskItem]) -> list[FatalFlaw]:
    flaws: list[FatalFlaw] = []
    for item in categories:
        if not item.potentialFatalFlaw:
            continue
        if item.level in ("high", "unknown"):
            severity: Literal["warning", "critical"] = "critical" if item.level == "high" else "warning"
            evidence_str = "; ".join(f"{e.label}: {e.value}" for e in item.evidence[:3])
            flaws.append(FatalFlaw(
                id=f"ff:{item.category.lower().replace(' / ', '_').replace('/', '_').replace(' ', '_')}",
                category=item.category,
                severity=severity,
                description=item.summary,
                evidence=evidence_str,
                nextStep=item.recommendedNextStep,
            ))
        elif item.level == "medium":
            evidence_str = "; ".join(f"{e.label}: {e.value}" for e in item.evidence[:3])
            flaws.append(FatalFlaw(
                id=f"ff:{item.category.lower().replace(' / ', '_').replace('/', '_').replace(' ', '_')}",
                category=item.category,
                severity="warning",
                description=item.summary,
                evidence=evidence_str,
                nextStep=item.recommendedNextStep,
            ))
    return flaws


# ── Main public function ──────────────────────────────────────────────────────

def compute_risk_register(
    wind_score: float | None,
    wind_speed_at_hub: float | None,
    confidence_score: float,
    terrain_score: float | None,
    terrain_complexity: float | None,
    slope_pct: float | None,
    infra_score: float | None,
    nearest_road_m: float | None,
    nearest_powerline_m: float | None,
    settlement_count_15km: int | None,
    env_score: float | None,
    land_cover_class: str | None,
    protected_area_risk: str | None,
    in_protected_area: bool | None,
    eco: "EconomicMetrics | None",
) -> RiskRegisterResult:
    categories = [
        _wind_resource_risk(wind_score, wind_speed_at_hub, confidence_score),
        _grid_connection_risk(nearest_powerline_m),
        _land_access_risk(nearest_road_m, land_cover_class, in_protected_area),
        _environmental_risk(env_score, land_cover_class, protected_area_risk, in_protected_area),
        _community_risk(settlement_count_15km),
        _permitting_risk(in_protected_area, land_cover_class, protected_area_risk),
        _economics_risk(eco),
        _constructability_risk(terrain_score, terrain_complexity, slope_pct, nearest_road_m),
        _data_quality_risk(confidence_score, wind_speed_at_hub, nearest_powerline_m, nearest_road_m, settlement_count_15km),
    ]

    fatal_flaws = _extract_fatal_flaws(categories)
    critical_count = sum(1 for f in fatal_flaws if f.severity == "critical")

    return RiskRegisterResult(
        categories=categories,
        fatalFlaws=fatal_flaws,
        fatalFlawCount=len(fatal_flaws),
        criticalFatalFlawCount=critical_count,
    )


# ── Development Outlook composer ──────────────────────────────────────────────

def compose_development_outlook(
    risk_register: RiskRegisterResult,
    fitness_result: "FitnessResult",
    total_suitability: float | None,
) -> DevelopmentOutlookResult:
    critical = risk_register.criticalFatalFlawCount
    ff_total = risk_register.fatalFlawCount
    high_risk_cats = sum(1 for r in risk_register.categories if r.level == "high")
    unknown_cats = sum(1 for r in risk_register.categories if r.level == "unknown")
    total = total_suitability or 0.0

    if critical > 0:
        outlook: Literal["promising", "fragile", "high_risk", "not_recommended"] = "not_recommended"
    elif fitness_result.testsPassed <= 3 or high_risk_cats >= 4:
        outlook = "high_risk"
    elif total >= 60 and (unknown_cats >= 3 or ff_total >= 2):
        outlook = "fragile"
    elif total >= 65 and ff_total <= 1 and fitness_result.testsPassed >= 7:
        outlook = "promising"
    else:
        outlook = "high_risk"

    # Build narrative
    fitness_str = f"{fitness_result.testsPassed}/{fitness_result.totalTests}"
    if outlook == "not_recommended":
        narrative = (
            f"This site has {critical} critical fatal flaw(s) that are likely to stop development. "
            f"It passed {fitness_str} project fitness tests. "
            "Investment in further development is not recommended without resolving the identified fatal flaws."
        )
    elif outlook == "high_risk":
        narrative = (
            f"This site carries high development risk: {high_risk_cats} high-risk categories and {ff_total} potential fatal flaw(s) identified. "
            f"It passed {fitness_str} project fitness tests. "
            "Significant investigation and de-risking work is required before this site can be considered viable."
        )
    elif outlook == "fragile":
        narrative = (
            f"This site shows reasonable suitability (score: {total:.0f}/100) but has {unknown_cats} unknown risk categories and {ff_total} potential concern(s). "
            f"It passed {fitness_str} project fitness tests. "
            "The project is fragile — additional data collection is needed before assessing true viability."
        )
    else:
        narrative = (
            f"This site shows a promising development outlook: suitability score {total:.0f}/100, {ff_total} minor concern(s), "
            f"and it passed {fitness_str} project fitness tests. "
            "Subject to on-site measurement and permitting confirmation, this warrants further development investment."
        )

    # Next investigation priorities from high/unknown risk categories
    seen: set[str] = set()
    priorities: list[str] = []
    for item in sorted(risk_register.categories, key=lambda x: {"high": 0, "unknown": 1, "medium": 2, "low": 3}[x.level]):
        if item.level in ("high", "unknown") and item.recommendedNextStep not in seen:
            seen.add(item.recommendedNextStep)
            priorities.append(item.recommendedNextStep)
    for item in risk_register.categories:
        if item.level == "medium" and item.recommendedNextStep not in seen and len(priorities) < 6:
            seen.add(item.recommendedNextStep)
            priorities.append(item.recommendedNextStep)

    return DevelopmentOutlookResult(
        developmentOutlook=outlook,
        narrativeSummary=narrative,
        nextInvestigationPriorities=priorities[:6],
    )
