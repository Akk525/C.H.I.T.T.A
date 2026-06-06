"""
Project Fitness Test Engine for CHITTA.

Runs 10 deterministic stress tests against a site's economic and physical assumptions.
All tests reuse compute_economic_metrics() — no new models or external calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from app.services.economics import (
    EconomicAssumptions,
    EconomicMetrics,
    compute_economic_metrics,
    compute_economic_score,
    estimate_capacity_factor,
)

if TYPE_CHECKING:
    pass

_DEFAULT_ASSUMPTIONS = EconomicAssumptions()


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class FitnessTestResult:
    testName: str
    passed: bool
    impactSummary: str
    beforeMetrics: dict
    afterMetrics: dict
    failureReason: str | None = None


@dataclass
class FitnessResult:
    tests: list[FitnessTestResult]
    testsPassed: int
    totalTests: int
    fitnessScore: float       # testsPassed / totalTests as float (0.0–1.0)
    riskBand: Literal["low", "medium", "high", "very_high"]
    mostVulnerableAssumptions: list[str]
    interpretation: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _before_metrics(eco: EconomicMetrics) -> dict:
    return {
        "capacityFactor": round(eco.capacity_factor, 3),
        "lcoeUsdPerMwh": round(eco.lcoe_usd_per_mwh, 1),
        "paybackYears": round(eco.payback_years, 1) if eco.payback_years else None,
        "economicScore": round(eco.economic_score, 1),
        "annualEnergyMwh": round(eco.annual_energy_mwh, 0),
    }


def _after_metrics(eco: EconomicMetrics) -> dict:
    return _before_metrics(eco)


def _eco(
    wind: float | None,
    terrain: float | None,
    infra: float | None,
    assumptions: EconomicAssumptions | None = None,
) -> EconomicMetrics:
    return compute_economic_metrics(
        mean_wind_mps=wind,
        wind_score=None,
        terrain_score=terrain,
        infra_score=infra,
        assumptions=assumptions,
    )


def _base_wind(wind_speed_at_hub: float | None) -> float:
    """Return a usable base wind speed, falling back to the economics module default."""
    return wind_speed_at_hub if wind_speed_at_hub is not None else 0.0


# ── Ten stress tests ──────────────────────────────────────────────────────────

def _test_wind_minus_05(
    wind: float | None, terrain: float | None, infra: float | None, before: dict
) -> FitnessTestResult:
    stressed_wind = max(0.0, _base_wind(wind) - 0.5) if wind is not None else None
    after_eco = _eco(stressed_wind, terrain, infra)
    passed = after_eco.economic_score >= 35
    return FitnessTestResult(
        testName="Wind resource −0.5 m/s",
        passed=passed,
        impactSummary=f"Economic score: {before['economicScore']:.0f} → {after_eco.economic_score:.0f}",
        beforeMetrics=before,
        afterMetrics=_after_metrics(after_eco),
        failureReason=None if passed else f"Economic score fell to {after_eco.economic_score:.0f} (threshold: 35)",
    )


def _test_wind_minus_10(
    wind: float | None, terrain: float | None, infra: float | None, before: dict
) -> FitnessTestResult:
    stressed_wind = max(0.0, _base_wind(wind) - 1.0) if wind is not None else None
    after_eco = _eco(stressed_wind, terrain, infra)
    passed = after_eco.economic_score >= 25
    return FitnessTestResult(
        testName="Wind resource −1.0 m/s",
        passed=passed,
        impactSummary=f"Economic score: {before['economicScore']:.0f} → {after_eco.economic_score:.0f}",
        beforeMetrics=before,
        afterMetrics=_after_metrics(after_eco),
        failureReason=None if passed else f"Economic score fell to {after_eco.economic_score:.0f} (threshold: 25)",
    )


def _test_price_minus_20(
    wind: float | None, terrain: float | None, infra: float | None, before: dict
) -> FitnessTestResult:
    assumptions = EconomicAssumptions(
        electricity_price_usd_per_mwh=_DEFAULT_ASSUMPTIONS.electricity_price_usd_per_mwh * 0.80,
    )
    after_eco = _eco(wind, terrain, infra, assumptions)
    payback_ok = after_eco.payback_years is not None and after_eco.payback_years <= 22
    passed = payback_ok
    payback_str = f"{after_eco.payback_years:.1f} yr" if after_eco.payback_years else "Neg. NPV"
    return FitnessTestResult(
        testName="Electricity price −20%",
        passed=passed,
        impactSummary=f"Payback: {before['paybackYears']} → {payback_str}",
        beforeMetrics=before,
        afterMetrics=_after_metrics(after_eco),
        failureReason=None if passed else f"Payback {payback_str} exceeds 22-year threshold or NPV negative",
    )


def _test_capex_plus_20(
    wind: float | None, terrain: float | None, infra: float | None, before: dict
) -> FitnessTestResult:
    assumptions = EconomicAssumptions(
        capex_usd_per_mw=_DEFAULT_ASSUMPTIONS.capex_usd_per_mw * 1.20,
    )
    after_eco = _eco(wind, terrain, infra, assumptions)
    passed = after_eco.lcoe_usd_per_mwh <= 80.0
    return FitnessTestResult(
        testName="CAPEX +20%",
        passed=passed,
        impactSummary=f"LCOE: {before['lcoeUsdPerMwh']:.1f} → {after_eco.lcoe_usd_per_mwh:.1f} USD/MWh",
        beforeMetrics=before,
        afterMetrics=_after_metrics(after_eco),
        failureReason=None if passed else f"LCOE {after_eco.lcoe_usd_per_mwh:.1f} USD/MWh exceeds 80 USD/MWh threshold",
    )


def _test_turbines_minus_20(before: dict) -> FitnessTestResult:
    remaining = max(1, int(_DEFAULT_ASSUMPTIONS.turbine_count * 0.80))
    passed = remaining >= 5
    return FitnessTestResult(
        testName="Turbine locations −20%",
        passed=passed,
        impactSummary=f"Turbines: {_DEFAULT_ASSUMPTIONS.turbine_count} → {remaining}",
        beforeMetrics=before,
        afterMetrics={**before, "turbineCount": remaining, "annualEnergyMwh": round(before["annualEnergyMwh"] * 0.80, 0)},
        failureReason=None if passed else f"Only {remaining} turbine sites remain (minimum viable: 5)",
    )


def _test_area_minus_20(
    wind: float | None, terrain: float | None, infra: float | None, before: dict
) -> FitnessTestResult:
    # Model area loss as proportional reduction in usable capacity
    reduced_count = max(1, int(_DEFAULT_ASSUMPTIONS.turbine_count * 0.80))
    assumptions = EconomicAssumptions(turbine_count=reduced_count)
    after_eco = _eco(wind, terrain, infra, assumptions)
    passed = after_eco.economic_score >= 25
    return FitnessTestResult(
        testName="Environmental constraints remove best 20% of area",
        passed=passed,
        impactSummary=f"Economic score: {before['economicScore']:.0f} → {after_eco.economic_score:.0f} ({reduced_count} turbines remain)",
        beforeMetrics=before,
        afterMetrics=_after_metrics(after_eco),
        failureReason=None if passed else f"Economic score fell to {after_eco.economic_score:.0f} after area reduction (threshold: 25)",
    )


def _test_grid_constrained(
    wind: float | None, terrain: float | None, before: dict
) -> FitnessTestResult:
    # Third-choice grid connection: model as poor infra score (20) to apply maximum infra CAPEX premium
    assumed_infra = 20.0
    after_eco = _eco(wind, terrain, assumed_infra)
    passed = after_eco.economic_score >= 30
    return FitnessTestResult(
        testName="Grid connection constrained (third-choice connection)",
        passed=passed,
        impactSummary=f"Economic score: {before['economicScore']:.0f} → {after_eco.economic_score:.0f} (CAPEX premium applied)",
        beforeMetrics=before,
        afterMetrics=_after_metrics(after_eco),
        failureReason=None if passed else f"Economic score fell to {after_eco.economic_score:.0f} under poor grid scenario (threshold: 30)",
    )


def _test_setbacks_double(before: dict) -> FitnessTestResult:
    remaining = max(1, int(_DEFAULT_ASSUMPTIONS.turbine_count * 0.70))
    passed = remaining >= 6
    return FitnessTestResult(
        testName="Setback assumptions double",
        passed=passed,
        impactSummary=f"Turbines after doubled setbacks: {_DEFAULT_ASSUMPTIONS.turbine_count} → {remaining}",
        beforeMetrics=before,
        afterMetrics={**before, "turbineCount": remaining, "annualEnergyMwh": round(before["annualEnergyMwh"] * 0.70, 0)},
        failureReason=None if passed else f"Only {remaining} turbine positions remain after doubled setbacks (minimum: 6)",
    )


def _test_loss_factors_plus_5pp(
    wind: float | None, terrain: float | None, infra: float | None, before: dict
) -> FitnessTestResult:
    # Increase losses by 5pp: model as wind speed penalty equivalent (~0.3 m/s reduction for typical site)
    # More directly: reduce CF by 0.05 by computing with adjusted wind speed
    base_cf_before = before["capacityFactor"]
    stressed_cf = max(0.01, base_cf_before - 0.05)
    passed = stressed_cf >= 0.18
    eco_after_score = compute_economic_score(
        stressed_cf,
        before["lcoeUsdPerMwh"] * (base_cf_before / stressed_cf) if stressed_cf > 0 else 9999,
        before["paybackYears"],
    )
    return FitnessTestResult(
        testName="Loss factors +5 percentage points",
        passed=passed,
        impactSummary=f"Capacity factor: {base_cf_before:.3f} → {stressed_cf:.3f}",
        beforeMetrics=before,
        afterMetrics={**before, "capacityFactor": round(stressed_cf, 3), "economicScore": round(eco_after_score, 1)},
        failureReason=None if passed else f"Stressed CF {stressed_cf:.3f} falls below minimum commercial threshold of 0.18",
    )


def _test_data_quality_penalty(
    wind: float | None,
    terrain: float | None,
    infra: float | None,
    confidence_score: float,
    before: dict,
) -> FitnessTestResult:
    if confidence_score >= 70 or wind is None:
        # High confidence or no wind data → test passes trivially if eco score ok
        passed = before["economicScore"] >= 35
        return FitnessTestResult(
            testName="Data quality penalty (confidence < 70%)",
            passed=passed,
            impactSummary="Confidence ≥ 70% — no penalty applied." if confidence_score >= 70 else "Wind data missing — conservative default used.",
            beforeMetrics=before,
            afterMetrics=before,
            failureReason=None if passed else "Economic score below threshold even without penalty.",
        )

    # Apply wind speed penalty proportional to low confidence
    penalty_mps = (70.0 - confidence_score) / 100.0  # e.g. conf=50 → -0.20 m/s
    penalised_wind = max(0.0, wind - penalty_mps)
    after_eco = _eco(penalised_wind, terrain, infra)
    passed = after_eco.economic_score >= 35
    return FitnessTestResult(
        testName="Data quality penalty (confidence < 70%)",
        passed=passed,
        impactSummary=f"Wind adjusted {wind:.2f} → {penalised_wind:.2f} m/s (confidence {confidence_score:.0f}/100). Economic score: {before['economicScore']:.0f} → {after_eco.economic_score:.0f}",
        beforeMetrics=before,
        afterMetrics=_after_metrics(after_eco),
        failureReason=None if passed else f"Economic score fell to {after_eco.economic_score:.0f} under data quality penalty (threshold: 35)",
    )


# ── Risk band and interpretation ──────────────────────────────────────────────

def _risk_band(tests_passed: int) -> Literal["low", "medium", "high", "very_high"]:
    if tests_passed <= 3:
        return "very_high"
    if tests_passed <= 6:
        return "high"
    if tests_passed <= 9:
        return "medium"
    return "low"


def _interpretation(tests_passed: int, band: str) -> str:
    if band == "very_high":
        return (
            f"Only {tests_passed}/10 stress tests passed. "
            "The project is highly fragile — it fails under mild adverse conditions. "
            "Major assumptions need validation before any further development investment."
        )
    if band == "high":
        return (
            f"{tests_passed}/10 stress tests passed. "
            "The project survives some stress but fails under several plausible scenarios. "
            "Key assumptions should be de-risked before committing to a development programme."
        )
    if band == "medium":
        return (
            f"{tests_passed}/10 stress tests passed. "
            "The project is reasonably robust but has identifiable vulnerabilities. "
            "Sensitivity analysis on the failing assumptions is recommended."
        )
    return (
        "All 10 stress tests passed. "
        "The project demonstrates strong robustness across modelled scenarios. "
        "Proceed to resource measurement and detailed feasibility with confidence."
    )


# ── Main public function ──────────────────────────────────────────────────────

def run_fitness_test(
    wind_speed_at_hub: float | None,
    terrain_score: float | None,
    infra_score: float | None,
    eco: EconomicMetrics | None,
    confidence_score: float = 70.0,
) -> FitnessResult:
    # Compute baseline economics if not provided
    if eco is None:
        base_eco = _eco(wind_speed_at_hub, terrain_score, infra_score)
    else:
        base_eco = eco

    before = _before_metrics(base_eco)
    w = wind_speed_at_hub
    t = terrain_score
    i = infra_score

    tests: list[FitnessTestResult] = [
        _test_wind_minus_05(w, t, i, before),
        _test_wind_minus_10(w, t, i, before),
        _test_price_minus_20(w, t, i, before),
        _test_capex_plus_20(w, t, i, before),
        _test_turbines_minus_20(before),
        _test_area_minus_20(w, t, i, before),
        _test_grid_constrained(w, t, before),
        _test_setbacks_double(before),
        _test_loss_factors_plus_5pp(w, t, i, before),
        _test_data_quality_penalty(w, t, i, confidence_score, before),
    ]

    passed_count = sum(1 for r in tests if r.passed)
    band = _risk_band(passed_count)

    vulnerable = [r.testName for r in tests if not r.passed][:3]

    return FitnessResult(
        tests=tests,
        testsPassed=passed_count,
        totalTests=10,
        fitnessScore=round(passed_count / 10.0, 1),
        riskBand=band,
        mostVulnerableAssumptions=vulnerable,
        interpretation=_interpretation(passed_count, band),
    )
