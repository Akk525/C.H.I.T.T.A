"""
Preliminary economic feasibility functions for CHITTA.

All outputs are order-of-magnitude estimates for early-stage screening.
They are NOT bankable, investment-grade, or suitable for financial decisions.
Accuracy: CAPEX ±30–50%, LCOE ±20–35%, capacity factor ±5–8 percentage points.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── Defaults ──────────────────────────────────────────────────────────────────

@dataclass
class EconomicAssumptions:
    turbine_rating_mw: float = 3.0
    turbine_count: int = 10
    electricity_price_usd_per_mwh: float = 55.0
    capex_usd_per_mw: float = 1_300_000.0
    opex_pct_of_capex: float = 0.03
    project_life_years: int = 20
    discount_rate: float = 0.08


@dataclass
class EconomicMetrics:
    capacity_factor: float
    annual_energy_mwh: float
    capex_usd: float
    opex_usd_per_year: float
    annual_revenue_usd: float
    payback_years: float | None   # None if net_annual_revenue ≤ 0
    lcoe_usd_per_mwh: float
    economic_score: float         # 0–100 composite
    wind_available: bool          # False → CF estimated at conservative default
    assumptions: EconomicAssumptions = field(default_factory=EconomicAssumptions)
    limitations: list[str] = field(default_factory=list)


# ── Core functions ────────────────────────────────────────────────────────────

# Empirical breakpoints: (wind_speed_m_s, capacity_factor)
# Derived from typical IEC Class II onshore turbine power curves.
_CF_BREAKPOINTS: list[tuple[float, float]] = [
    (3.0, 0.05), (4.0, 0.12), (5.0, 0.21), (6.0, 0.31),
    (7.0, 0.38), (8.0, 0.43), (9.0, 0.47), (12.0, 0.50),
]


def estimate_capacity_factor(mean_wind_mps: float) -> float:
    """Piecewise linear CF from mean wind speed at hub height."""
    if mean_wind_mps <= _CF_BREAKPOINTS[0][0]:
        return _CF_BREAKPOINTS[0][1]
    for i in range(len(_CF_BREAKPOINTS) - 1):
        v1, cf1 = _CF_BREAKPOINTS[i]
        v2, cf2 = _CF_BREAKPOINTS[i + 1]
        if v1 <= mean_wind_mps <= v2:
            t = (mean_wind_mps - v1) / (v2 - v1)
            return cf1 + t * (cf2 - cf1)
    return _CF_BREAKPOINTS[-1][1]


def _adjusted_cf(base_cf: float, terrain_score: float | None) -> float:
    """Apply terrain turbulence penalty to capacity factor (up to −8%)."""
    if terrain_score is not None and terrain_score < 70:
        penalty = (70 - terrain_score) / 70.0 * 0.08
        return max(0.05, base_cf - penalty)
    return base_cf


def estimate_capex_usd(
    capacity_mw: float,
    terrain_score: float | None,
    infra_score: float | None,
    capex_per_mw: float,
) -> float:
    """
    CAPEX = capacity × base_rate × (1 + terrain_premium + infra_premium).
    Terrain premium: up to +20% for rugged terrain (civil works, foundations).
    Infra premium: up to +15% for remote sites (road build, grid extension).
    """
    base = capacity_mw * capex_per_mw

    t_score = terrain_score if terrain_score is not None else 60.0
    terrain_premium = 0.0 if t_score >= 70 else (70 - t_score) / 70.0 * 0.20

    i_score = infra_score if infra_score is not None else 60.0
    infra_premium = 0.0 if i_score >= 70 else (70 - i_score) / 70.0 * 0.15

    return base * (1 + terrain_premium + infra_premium)


def _crf(rate: float, years: int) -> float:
    """Capital Recovery Factor."""
    if rate <= 0:
        return 1.0 / max(1, years)
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)


def estimate_lcoe(
    capex_usd: float,
    opex_usd_per_year: float,
    annual_energy_mwh: float,
    discount_rate: float,
    project_life_years: int,
) -> float:
    """
    Levelised Cost of Energy [USD/MWh].
    LCOE = (CAPEX × CRF + OPEX) / AEP
    """
    if annual_energy_mwh <= 0:
        return 9999.0  # degenerate case
    annual_capex_service = capex_usd * _crf(discount_rate, project_life_years)
    return (annual_capex_service + opex_usd_per_year) / annual_energy_mwh


def compute_economic_score(
    capacity_factor: float,
    lcoe_usd_per_mwh: float,
    payback_years: float | None,
) -> float:
    """
    Composite economic score 0–100.
    CF weight 40%, LCOE weight 35%, payback weight 25%.
    """
    cf_score = max(0.0, min(100.0, (capacity_factor - 0.15) / 0.30 * 100.0))
    lcoe_score = max(0.0, min(100.0, (75.0 - lcoe_usd_per_mwh) / 35.0 * 100.0))
    if payback_years is None or payback_years > 30:
        pay_score = 5.0
    else:
        pay_score = max(0.0, min(100.0, (20.0 - payback_years) / 12.0 * 100.0))
    return max(0.0, min(100.0, 0.40 * cf_score + 0.35 * lcoe_score + 0.25 * pay_score))


_STANDARD_LIMITATIONS = [
    "Preliminary screening only — not a bankable or investment-grade assessment.",
    "Capacity factor estimated from mean hub-height wind speed using empirical turbine power curves (±5–8 pp).",
    "CAPEX benchmark accuracy is ±30–50% at this stage of development.",
    "LCOE uses a constant 8% discount rate; excludes inflation, tax incentives, and financing structure.",
]


def compute_economic_metrics(
    mean_wind_mps: float | None,
    wind_score: float | None,
    terrain_score: float | None,
    infra_score: float | None,
    assumptions: EconomicAssumptions | None = None,
) -> EconomicMetrics:
    """
    Compute preliminary economic metrics from site scores.
    All values carry significant uncertainty — see limitations list.
    """
    if assumptions is None:
        assumptions = EconomicAssumptions()

    limitations = list(_STANDARD_LIMITATIONS)
    wind_available = mean_wind_mps is not None and mean_wind_mps > 0

    if wind_available:
        base_cf = estimate_capacity_factor(float(mean_wind_mps))  # type: ignore[arg-type]
    else:
        base_cf = 0.22  # conservative default
        limitations.append(
            "Wind speed unavailable — capacity factor assumed at conservative 22%. "
            "All financial metrics are highly uncertain."
        )

    cf = _adjusted_cf(base_cf, terrain_score)

    capacity_mw = assumptions.turbine_rating_mw * assumptions.turbine_count
    aep = capacity_mw * 8760.0 * cf  # MWh/year (gross)

    capex = estimate_capex_usd(capacity_mw, terrain_score, infra_score, assumptions.capex_usd_per_mw)

    if terrain_score is not None and terrain_score < 50:
        limitations.append(
            "Complex terrain detected — CAPEX estimate includes significant construction premium."
        )
    if infra_score is not None and infra_score < 50:
        limitations.append(
            "Poor infrastructure access — CAPEX includes road and/or grid extension premium."
        )

    opex = capex * assumptions.opex_pct_of_capex
    revenue = aep * assumptions.electricity_price_usd_per_mwh
    net_annual = revenue - opex
    payback = capex / net_annual if net_annual > 0 else None

    lcoe = estimate_lcoe(capex, opex, aep, assumptions.discount_rate, assumptions.project_life_years)
    eco_score = compute_economic_score(cf, lcoe, payback)

    return EconomicMetrics(
        capacity_factor=round(cf, 3),
        annual_energy_mwh=round(aep, 0),
        capex_usd=round(capex, 0),
        opex_usd_per_year=round(opex, 0),
        annual_revenue_usd=round(revenue, 0),
        payback_years=round(payback, 1) if payback is not None else None,
        lcoe_usd_per_mwh=round(lcoe, 2),
        economic_score=round(eco_score, 1),
        wind_available=wind_available,
        assumptions=assumptions,
        limitations=limitations,
    )
