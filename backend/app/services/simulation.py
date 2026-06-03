"""
Deterministic scenario simulation engine for CHITTA.

Recomputes suitability scores and economic metrics from stored candidate data
using configurable weights and assumptions. No data providers are called.
Formula version: sim-1.0
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.economics import (
    compute_economic_score,
    estimate_capex_usd,
    estimate_lcoe,
)
from app.services.methodology import generate_analysis_id, utc_now_iso
from app.services.scoring import clamp100, total_suitability_weighted

_DISCOUNT_RATE = 0.08  # fixed; not exposed as simulation param


# ── Config & I/O dataclasses ───────────────────────────────────────────────────

@dataclass
class SimulationConfig:
    turbineCount: int = 10
    turbineRatingMw: float = 3.0
    electricityPriceUsdPerMwh: float = 55.0
    capexUsdPerMw: float = 1_300_000.0
    opexPercentOfCapex: float = 0.03
    projectLifeYears: int = 20
    # Raw weights — any positive numbers; normalised internally to sum=1.0
    windWeight: float = 35.0
    terrainWeight: float = 20.0
    infrastructureWeight: float = 15.0
    environmentalWeight: float = 10.0
    populationWeight: float = 10.0
    confidenceWeight: float = 5.0
    economicWeight: float = 5.0
    environmentalStrictness: str = "medium"    # "low" | "medium" | "high"
    infrastructurePreference: str = "balanced" # "remote" | "balanced" | "grid-connected"


@dataclass
class CandidateInput:
    id: str
    latitude: float
    longitude: float
    totalSuitability: float | None
    finalDecision: str | None
    windScore: float | None
    terrainScore: float | None
    infrastructureScore: float | None
    environmentalScore: float | None
    populationScore: float | None
    confidenceScore: float
    capacityFactor: float | None
    topStrengths: list[str] = field(default_factory=list)
    topRisks: list[str] = field(default_factory=list)


@dataclass
class SimulatedCandidate:
    id: str
    latitude: float
    longitude: float
    originalTotalSuitability: float | None
    newTotalSuitability: float | None
    suitabilityDelta: float | None
    originalDecision: str | None
    newDecision: str | None
    newEconomicScore: float | None
    newLcoeUsdPerMwh: float | None
    newAnnualEnergyMwh: float | None
    newPaybackYears: float | None
    newCapacityFactor: float | None
    topStrengths: list[str] = field(default_factory=list)
    topRisks: list[str] = field(default_factory=list)


@dataclass
class CandidateRankingChange:
    id: str
    latitude: float
    longitude: float
    originalRank: int
    newRank: int
    rankChange: int  # positive = moved up
    direction: str   # "up" | "down" | "unchanged"


@dataclass
class SimulationResult:
    simulationId: str
    config: SimulationConfig
    recomputedCandidates: list[SimulatedCandidate]
    rankingChanges: list[CandidateRankingChange]
    strongestCandidate: SimulatedCandidate | None
    weakestCandidate: SimulatedCandidate | None
    mostImprovedCandidate: SimulatedCandidate | None
    mostSensitiveCandidate: SimulatedCandidate | None
    methodology: dict[str, str]
    auditTrail: list[str]


# ── Internal helpers ───────────────────────────────────────────────────────────

_ENV_STRICTNESS_MULTIPLIERS: dict[str, float] = {
    "low": 1.25,
    "medium": 1.0,
    "high": 0.65,
}

_INFRA_PREFERENCE_MULTIPLIERS: dict[str, float] = {
    "remote": 0.75,
    "balanced": 1.0,
    "grid-connected": 1.30,
}

_DIMENSION_LABELS: dict[str, str] = {
    "wind": "Wind resource",
    "terrain": "Terrain buildability",
    "infrastructure": "Infrastructure access",
    "environmental": "Environmental conditions",
    "population": "Population / social friction",
    "confidence": "Data confidence",
    "economic": "Economic viability",
}


def _normalize_weights(config: SimulationConfig) -> dict[str, float]:
    raw = {
        "wind": max(0.0, config.windWeight),
        "terrain": max(0.0, config.terrainWeight),
        "infrastructure": max(0.0, config.infrastructureWeight),
        "environmental": max(0.0, config.environmentalWeight),
        "population": max(0.0, config.populationWeight),
        "confidence": max(0.0, config.confidenceWeight),
        "economic": max(0.0, config.economicWeight),
    }
    total = sum(raw.values())
    if total <= 0:
        return {
            "wind": 0.35, "terrain": 0.20, "infrastructure": 0.15,
            "environmental": 0.10, "population": 0.10,
            "confidence": 0.05, "economic": 0.05,
        }
    return {k: v / total for k, v in raw.items()}


def _recompute_economics(
    candidate: CandidateInput,
    config: SimulationConfig,
) -> dict[str, float | None] | None:
    if candidate.capacityFactor is None:
        return None

    cf = candidate.capacityFactor
    rated_mw = config.turbineCount * config.turbineRatingMw
    aep = cf * rated_mw * 8760.0

    capex = estimate_capex_usd(
        capacity_mw=rated_mw,
        terrain_score=candidate.terrainScore,
        infra_score=candidate.infrastructureScore,
        capex_per_mw=config.capexUsdPerMw,
    )
    opex = capex * config.opexPercentOfCapex
    revenue = aep * config.electricityPriceUsdPerMwh
    net_annual = revenue - opex
    payback: float | None = round(capex / net_annual, 1) if net_annual > 0 else None

    lcoe = estimate_lcoe(capex, opex, aep, _DISCOUNT_RATE, config.projectLifeYears)
    eco_score = compute_economic_score(cf, lcoe, payback)

    return {
        "capacityFactor": round(cf, 3),
        "annualEnergyMwh": round(aep, 0),
        "lcoeUsdPerMwh": round(lcoe, 2),
        "paybackYears": payback,
        "economicScore": round(eco_score, 1),
    }


def _coordinator_decision_from_score(score: float) -> str:
    if score >= 70:
        return "promising"
    if score >= 55:
        return "mixed"
    if score >= 40:
        return "caution"
    return "poor"


def _derive_strengths_risks(
    scores: dict[str, float],
    weights: dict[str, float],
) -> tuple[list[str], list[str]]:
    ranked = sorted(
        scores.items(),
        key=lambda kv: kv[1] * weights.get(kv[0], 0.0),
        reverse=True,
    )
    strengths = [
        f"{_DIMENSION_LABELS.get(k, k)} (score: {v:.0f})"
        for k, v in ranked[:2]
        if v >= 55
    ]
    risks = [
        f"{_DIMENSION_LABELS.get(k, k)} (score: {v:.0f})"
        for k, v in ranked[-2:]
        if v < 55
    ]
    return strengths, risks


def _build_methodology(
    config: SimulationConfig,
    normalized_weights: dict[str, float],
) -> dict[str, str]:
    weight_str = ", ".join(
        f"{_DIMENSION_LABELS.get(k, k)}: {v * 100:.1f}%"
        for k, v in normalized_weights.items()
    )
    env_mult = _ENV_STRICTNESS_MULTIPLIERS.get(config.environmentalStrictness, 1.0)
    infra_mult = _INFRA_PREFERENCE_MULTIPLIERS.get(config.infrastructurePreference, 1.0)
    return {
        "formulaVersion": "sim-1.0",
        "description": (
            "Deterministic simulation recomputing suitability and economics from stored "
            "candidate scores. No data providers are called."
        ),
        "scoringFormula": f"7-dimension weighted sum (normalised). Weights: {weight_str}",
        "economicNote": (
            "Economic score is a full weighted dimension — not the v2.1.0 ±8pt nudge. "
            "Capacity factor is preserved from the original analysis (site property)."
        ),
        "environmentalModifier": (
            f"strictness={config.environmentalStrictness} (multiplier: {env_mult})"
        ),
        "infrastructureModifier": (
            f"preference={config.infrastructurePreference} (multiplier: {infra_mult})"
        ),
    }


def _build_audit_trail(
    config: SimulationConfig,
    normalized_weights: dict[str, float],
    candidate_count: int,
    unenriched_count: int,
    generated_at: str,
    simulation_id: str,
) -> list[str]:
    env_mult = _ENV_STRICTNESS_MULTIPLIERS.get(config.environmentalStrictness, 1.0)
    infra_mult = _INFRA_PREFERENCE_MULTIPLIERS.get(config.infrastructurePreference, 1.0)
    return [
        f"Simulation ID: {simulation_id}",
        f"Generated at: {generated_at}",
        (
            f"Candidates processed: {candidate_count} total, "
            f"{unenriched_count} without economic data (econ recompute skipped)"
        ),
        "Formula: sim-1.0 — 7-dimension weighted sum with normalised weights",
        "Weights: " + ", ".join(
            f"{k}={v * 100:.1f}%" for k, v in normalized_weights.items()
        ),
        (
            f"Economic assumptions: {config.turbineCount} × {config.turbineRatingMw}MW, "
            f"${config.electricityPriceUsdPerMwh}/MWh, "
            f"${config.capexUsdPerMw:,.0f}/MW CAPEX, "
            f"{config.opexPercentOfCapex * 100:.1f}% OPEX, "
            f"{config.projectLifeYears}yr life"
        ),
        f"Environmental strictness: {config.environmentalStrictness} (score multiplier: {env_mult})",
        f"Infrastructure preference: {config.infrastructurePreference} (score multiplier: {infra_mult})",
        "Note: Rankings may differ from prospecting output — sim-1.0 uses economic as a full weight vs v2.1.0 nudge.",
    ]


# ── Public entry point ─────────────────────────────────────────────────────────

def run_simulation(
    candidates: list[CandidateInput],
    config: SimulationConfig,
) -> SimulationResult:
    simulation_id = generate_analysis_id()
    generated_at = utc_now_iso()
    weights = _normalize_weights(config)

    env_mult = _ENV_STRICTNESS_MULTIPLIERS.get(config.environmentalStrictness, 1.0)
    infra_mult = _INFRA_PREFERENCE_MULTIPLIERS.get(config.infrastructurePreference, 1.0)

    unenriched_count = sum(1 for c in candidates if c.capacityFactor is None)
    simulated: list[SimulatedCandidate] = []

    for cand in candidates:
        eco = _recompute_economics(cand, config)
        new_eco_score: float | None = eco["economicScore"] if eco else None  # type: ignore[assignment]

        adj_env = clamp100((cand.environmentalScore or 55.0) * env_mult)
        adj_infra = clamp100((cand.infrastructureScore or 50.0) * infra_mult)

        new_total = total_suitability_weighted(
            wind_score=cand.windScore,
            terrain_score=cand.terrainScore,
            infra_score=adj_infra,
            env_score=adj_env,
            pop_score=cand.populationScore,
            confidence_score=cand.confidenceScore,
            economic_score=new_eco_score,
            weights=weights,
        )

        new_decision = (
            _coordinator_decision_from_score(new_total)
            if new_total is not None else None
        )

        component_scores: dict[str, float] = {
            "wind": cand.windScore or 0.0,
            "terrain": cand.terrainScore or 0.0,
            "infrastructure": adj_infra,
            "environmental": adj_env,
            "population": cand.populationScore or 60.0,
            "confidence": cand.confidenceScore,
            "economic": new_eco_score or 50.0,
        }
        strengths, risks = _derive_strengths_risks(component_scores, weights)

        delta: float | None = None
        if new_total is not None and cand.totalSuitability is not None:
            delta = round(new_total - cand.totalSuitability, 1)

        simulated.append(SimulatedCandidate(
            id=cand.id,
            latitude=cand.latitude,
            longitude=cand.longitude,
            originalTotalSuitability=cand.totalSuitability,
            newTotalSuitability=round(new_total, 1) if new_total is not None else None,
            suitabilityDelta=delta,
            originalDecision=cand.finalDecision,
            newDecision=new_decision,
            newEconomicScore=eco["economicScore"] if eco else None,  # type: ignore[assignment]
            newLcoeUsdPerMwh=eco["lcoeUsdPerMwh"] if eco else None,  # type: ignore[assignment]
            newAnnualEnergyMwh=eco["annualEnergyMwh"] if eco else None,  # type: ignore[assignment]
            newPaybackYears=eco["paybackYears"] if eco else None,  # type: ignore[assignment]
            newCapacityFactor=eco["capacityFactor"] if eco else None,  # type: ignore[assignment]
            topStrengths=strengths,
            topRisks=risks,
        ))

    # Compute ranking changes
    orig_sorted = sorted(
        [c for c in candidates if c.totalSuitability is not None],
        key=lambda c: c.totalSuitability,  # type: ignore[arg-type]
        reverse=True,
    )
    orig_rank_map = {c.id: i + 1 for i, c in enumerate(orig_sorted)}

    new_sorted = sorted(
        [s for s in simulated if s.newTotalSuitability is not None],
        key=lambda s: s.newTotalSuitability,  # type: ignore[arg-type]
        reverse=True,
    )
    new_rank_map = {s.id: i + 1 for i, s in enumerate(new_sorted)}

    ranking_changes: list[CandidateRankingChange] = []
    for s in simulated:
        orig_rank = orig_rank_map.get(s.id, 0)
        new_rank = new_rank_map.get(s.id, 0)
        if orig_rank == 0 or new_rank == 0:
            continue
        change = orig_rank - new_rank
        direction = "up" if change > 0 else ("down" if change < 0 else "unchanged")
        ranking_changes.append(CandidateRankingChange(
            id=s.id,
            latitude=s.latitude,
            longitude=s.longitude,
            originalRank=orig_rank,
            newRank=new_rank,
            rankChange=change,
            direction=direction,
        ))

    enriched_sim = [s for s in simulated if s.newTotalSuitability is not None]
    strongest = max(enriched_sim, key=lambda s: s.newTotalSuitability, default=None)  # type: ignore[arg-type]
    weakest = min(enriched_sim, key=lambda s: s.newTotalSuitability, default=None)  # type: ignore[arg-type]

    with_delta = [s for s in simulated if s.suitabilityDelta is not None]
    most_improved = max(with_delta, key=lambda s: s.suitabilityDelta, default=None)  # type: ignore[arg-type]
    most_sensitive = max(with_delta, key=lambda s: abs(s.suitabilityDelta), default=None)  # type: ignore[arg-type]

    methodology = _build_methodology(config, weights)
    audit_trail = _build_audit_trail(
        config, weights, len(candidates), unenriched_count, generated_at, simulation_id,
    )

    return SimulationResult(
        simulationId=simulation_id,
        config=config,
        recomputedCandidates=simulated,
        rankingChanges=sorted(ranking_changes, key=lambda rc: rc.newRank),
        strongestCandidate=strongest,
        weakestCandidate=weakest,
        mostImprovedCandidate=most_improved,
        mostSensitiveCandidate=most_sensitive,
        methodology=methodology,
        auditTrail=audit_trail,
    )
