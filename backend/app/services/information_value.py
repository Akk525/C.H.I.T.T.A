"""
Information Value Engine for CHITTA.

Ranks the most valuable missing information gaps a developer should close next.
Formula: informationValue = round(impact × uncertainty / 10, 1), range 0–10.

All scoring is deterministic. No LLM calls. No external API calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.evidence_quality import EvidenceQualityReport
    from app.services.risk import RiskRegisterResult
    from app.services.economics import EconomicMetrics


@dataclass
class InformationValueItem:
    category: str
    informationGap: str
    impact: float        # 0–10: how much knowing this changes the go/no-go decision
    uncertainty: float   # 0–10: how unknown this is right now
    informationValue: float  # impact × uncertainty / 10
    recommendedAction: str


@dataclass
class InformationValueReport:
    items: list[InformationValueItem]
    topPriority: str | None


def _iv(impact: float, uncertainty: float) -> float:
    return round(impact * uncertainty / 10.0, 1)


def _item(
    category: str,
    gap: str,
    impact: float,
    uncertainty: float,
    action: str,
) -> InformationValueItem:
    return InformationValueItem(
        category=category,
        informationGap=gap,
        impact=impact,
        uncertainty=uncertainty,
        informationValue=_iv(impact, uncertainty),
        recommendedAction=action,
    )


def compute_information_value(
    evidence_quality: "EvidenceQualityReport",
    risk_register: "RiskRegisterResult",
    wind_speed_at_hub: float | None,
    nearest_powerline_m: float | None,
    nearest_road_m: float | None,
    settlement_count_15km: int | None,
    env_score: float | None,
    land_cover_class: str | None,
    in_protected_area: bool | None,
    terrain_score: float | None,
    slope_pct: float | None,
    eco: "EconomicMetrics | None",
    confidence_score: float,
) -> InformationValueReport:

    # Convenience lookups
    in_pa = bool(in_protected_area)
    pa_risk_high = _risk_cat_level(risk_register, "Environmental") in ("high",)
    eco_score = eco.economic_score if eco is not None else None
    lc = (land_cover_class or "").lower()

    # ── 1. On-site Wind Measurement ──────────────────────────────────────────
    impact_wind = 9.0
    if wind_speed_at_hub is None:
        uncertainty_wind = 10.0
    elif confidence_score < 50:
        uncertainty_wind = 9.0
    elif confidence_score < 70:
        uncertainty_wind = 7.0
    else:
        uncertainty_wind = 5.0

    gap1 = _item(
        "Wind Measurement",
        "No on-site wind measurement — all estimates from satellite/reanalysis data",
        impact_wind,
        uncertainty_wind,
        "Commission a met mast or lidar campaign (minimum 12 months) to bankable standard",
    )

    # ── 2. Grid Connection Study ─────────────────────────────────────────────
    pl = nearest_powerline_m
    if pl is None or pl > 20_000:
        impact_grid = 9.0
    elif pl > 10_000:
        impact_grid = 7.0
    else:
        impact_grid = 5.0
    uncertainty_grid = 9.0  # grid capacity never in OSM

    gap2 = _item(
        "Grid Connection Study",
        "Grid capacity and connection costs unknown — OSM shows line proximity only",
        impact_grid,
        uncertainty_grid,
        "Request a formal grid connection study from the local network operator",
    )

    # ── 3. Environmental Impact Assessment ───────────────────────────────────
    if in_pa:
        impact_env = 10.0
    elif env_score is not None and env_score < 30:
        impact_env = 9.0
    elif pa_risk_high:
        impact_env = 8.0
    else:
        impact_env = 5.0

    if env_score is None:
        uncertainty_env = 9.0
    elif env_score < 50:
        uncertainty_env = 7.0
    else:
        uncertainty_env = 6.0

    gap3 = _item(
        "Environmental Survey",
        "EIA not conducted — land cover and PA proximity are screening proxies only",
        impact_env,
        uncertainty_env,
        "Engage an ecologist for Phase 1 habitats survey and consult the statutory consultee list",
    )

    # ── 4. Ecological / Biodiversity Survey ──────────────────────────────────
    sensitive_lc = lc in ("wetland", "forest", "shrubland", "grassland")
    if in_pa or sensitive_lc:
        impact_eco = 8.0
    elif pa_risk_high:
        impact_eco = 7.0
    else:
        impact_eco = 4.0
    uncertainty_eco = 8.0  # biodiversity never in public screening data

    gap4 = _item(
        "Ecological / Biodiversity Survey",
        "Bird/bat flight paths and habitat quality unknown",
        impact_eco,
        uncertainty_eco,
        "Commission vantage point surveys and bat activity transects aligned with planning guidelines",
    )

    # ── 5. Community Sentiment ───────────────────────────────────────────────
    sc = settlement_count_15km
    if sc is not None and sc > 5:
        impact_com = 7.0
    elif sc is not None and sc > 0:
        impact_com = 5.0
    else:
        impact_com = 3.0
    uncertainty_com = 8.0  # no public sentiment data

    gap5 = _item(
        "Community Sentiment",
        "No community sentiment data — settlement count is a coarse proximity proxy",
        impact_com,
        uncertainty_com,
        "Conduct early public engagement and informal consultation with local stakeholders",
    )

    # ── 6. Planning Pre-Application ──────────────────────────────────────────
    if in_pa:
        impact_plan = 9.0
        uncertainty_plan = 9.0
    elif pa_risk_high:
        impact_plan = 8.0
        uncertainty_plan = 7.0
    else:
        impact_plan = 6.0
        uncertainty_plan = 5.0

    gap6 = _item(
        "Planning Pre-Application",
        "Local planning policy position for wind energy not confirmed",
        impact_plan,
        uncertainty_plan,
        "Request a pre-application meeting with the local planning authority to identify policy blockers",
    )

    # ── 7. Geotechnical Assessment ───────────────────────────────────────────
    if terrain_score is not None and terrain_score < 40:
        impact_geo = 8.0
    elif slope_pct is not None and slope_pct > 15:
        impact_geo = 8.0
    elif terrain_score is not None and terrain_score < 60:
        impact_geo = 6.0
    else:
        impact_geo = 4.0

    if terrain_score is None:
        uncertainty_geo = 9.0
    elif terrain_score < 50:
        uncertainty_geo = 7.0
    else:
        uncertainty_geo = 5.0

    gap7 = _item(
        "Geotechnical Assessment",
        "Ground conditions unknown — terrain complexity derived from coarse DEM only",
        impact_geo,
        uncertainty_geo,
        "Commission a desk study and then intrusive ground investigation to assess foundation requirements",
    )

    # ── 8. Land Rights Confirmation ──────────────────────────────────────────
    if in_pa:
        impact_land = 9.0
        uncertainty_land = 9.0
    elif nearest_road_m is not None and nearest_road_m > 30_000:
        impact_land = 7.0
        uncertainty_land = 7.0
    else:
        impact_land = 5.0
        uncertainty_land = 5.0

    gap8 = _item(
        "Land Rights Confirmation",
        "Land ownership and access rights not established",
        impact_land,
        uncertainty_land,
        "Identify landowners via title registry and initiate option agreement or heads of terms",
    )

    # ── 9. Noise & Shadow Flicker Assessment ─────────────────────────────────
    if sc is not None and sc > 5:
        impact_noise = 8.0
        uncertainty_noise = 7.0
    elif sc is not None and sc > 0:
        impact_noise = 6.0
        uncertainty_noise = 5.0
    else:
        impact_noise = 3.0
        uncertainty_noise = sc is None and 7.0 or 5.0

    gap9 = _item(
        "Noise & Shadow Flicker",
        "Noise and visual impact not modelled — required for planning in most jurisdictions",
        impact_noise,
        float(uncertainty_noise),
        "Commission noise and shadow flicker modelling using a representative turbine specification",
    )

    # ── 10. Bankable Financial Model ─────────────────────────────────────────
    if eco is None:
        impact_fin = 9.0
        uncertainty_fin = 9.0
    elif eco_score is not None and eco_score < 30:
        impact_fin = 8.0
        uncertainty_fin = eco is None and 9.0 or (wind_speed_at_hub is None and 9.0 or (confidence_score < 60 and 7.0 or 6.0))
    elif eco_score is not None and eco_score < 55:
        impact_fin = 6.0
        uncertainty_fin = wind_speed_at_hub is None and 9.0 or (confidence_score < 60 and 7.0 or 6.0)
    else:
        impact_fin = 5.0
        uncertainty_fin = wind_speed_at_hub is None and 9.0 or (confidence_score < 60 and 7.0 or 6.0)

    gap10 = _item(
        "Bankable Financial Model",
        "Economics are order-of-magnitude estimates only (±30–50% accuracy)",
        impact_fin,
        float(uncertainty_fin),
        "Build a full financial model with measured wind data, site-specific CAPEX, and financing structure",
    )

    items = sorted(
        [gap1, gap2, gap3, gap4, gap5, gap6, gap7, gap8, gap9, gap10],
        key=lambda x: x.informationValue,
        reverse=True,
    )

    return InformationValueReport(
        items=items,
        topPriority=items[0].category if items else None,
    )


def _risk_cat_level(risk_register: "RiskRegisterResult", name_fragment: str) -> str:
    for cat in risk_register.categories:
        if name_fragment.lower() in cat.category.lower():
            return cat.level
    return "unknown"
