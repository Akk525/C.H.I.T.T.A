from __future__ import annotations

import asyncio
import math
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.agents import (
    AgentContext,
    CoordinatorAgent,
    EnvironmentalAgent,
    InfrastructureAgent,
    SocialAgent,
    TerrainAgent,
    WindAgent,
)
from app.providers.base import LatLng
from app.services.analysis import analyze_site_enriched, analyze_site_realdata
from app.services.heatmap import generate_grid_points
from app.services.methodology import (
    SCORING_FORMULA_VERSION,
    generate_analysis_id,
    utc_now_iso,
)
from app.services.economics import EconomicAssumptions, compute_economic_metrics
from app.services.scoring import (
    apply_economic_nudge,
    compute_scores_from_enriched,
    total_suitability_optional,
)


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class ProspectingCandidate:
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
    topStrengths: list[str]
    topRisks: list[str]
    isFullyEnriched: bool
    providerStatus: dict[str, str]
    # Economic fields (populated for fully-enriched candidates only)
    economicScore: float | None = None
    lcoeUsdPerMwh: float | None = None
    annualEnergyMwh: float | None = None
    paybackYears: float | None = None
    capacityFactor: float | None = None
    error: str | None = None


@dataclass
class _ClusterState:
    members: list[ProspectingCandidate] = field(default_factory=list)
    sum_lat: float = 0.0
    sum_lng: float = 0.0

    def add(self, c: ProspectingCandidate) -> None:
        self.members.append(c)
        self.sum_lat += c.latitude
        self.sum_lng += c.longitude

    @property
    def centroid_lat(self) -> float:
        return self.sum_lat / len(self.members)

    @property
    def centroid_lng(self) -> float:
        return self.sum_lng / len(self.members)

    @property
    def avg_score(self) -> float:
        scores = [c.totalSuitability for c in self.members if c.totalSuitability is not None]
        return float(sum(scores) / len(scores)) if scores else 0.0

    @property
    def top_decision(self) -> str:
        decisions = [c.finalDecision for c in self.members if c.finalDecision]
        if not decisions:
            return "unknown"
        return max(set(decisions), key=decisions.count)


@dataclass
class ProspectingCluster:
    id: str
    label: str
    centroidLatitude: float
    centroidLongitude: float
    averageSuitability: float
    candidateCount: int
    topDecision: str
    summary: str


@dataclass
class ProspectingResult:
    prospectingId: str
    region: dict[str, Any]
    generatedAt: str
    candidateCount: int
    enrichedCount: int
    candidates: list[ProspectingCandidate]
    clusters: list[ProspectingCluster]
    topCandidates: list[ProspectingCandidate]
    methodology: dict[str, str]
    auditTrail: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2.0 * R * math.asin(math.sqrt(min(1.0, a)))


def _short_id() -> str:
    return str(uuid.uuid4())[:8]


# ── Pass 1: quick wind + terrain ──────────────────────────────────────────────

async def _quick_score(p: LatLng) -> ProspectingCandidate:
    try:
        metrics, _debug, choice = await analyze_site_realdata(p)
        wind_score = metrics.get("windScore")
        terrain_score = metrics.get("terrainScore")
        confidence_score = float(metrics.get("confidenceScore") or 0)
        total = total_suitability_optional(
            wind_score, terrain_score,
            accessibility_score=55.0,
            confidence_score=confidence_score,
        )
        return ProspectingCandidate(
            id=_short_id(),
            latitude=p.latitude,
            longitude=p.longitude,
            totalSuitability=round(total, 1) if total is not None else None,
            finalDecision=None,
            windScore=round(wind_score, 1) if wind_score is not None else None,
            terrainScore=round(terrain_score, 1) if terrain_score is not None else None,
            infrastructureScore=None,
            environmentalScore=None,
            populationScore=None,
            confidenceScore=round(confidence_score, 1),
            topStrengths=[],
            topRisks=[],
            isFullyEnriched=False,
            providerStatus={
                "wind": "REAL" if choice.wind not in {"unavailable", "mock"} else choice.wind.upper(),
                "elevation": "REAL" if choice.elevation not in {"unavailable", "mock"} else choice.elevation.upper(),
                "infrastructure": "UNAVAILABLE",
            },
        )
    except Exception as e:
        return ProspectingCandidate(
            id=_short_id(),
            latitude=p.latitude,
            longitude=p.longitude,
            totalSuitability=None,
            finalDecision=None,
            windScore=None, terrainScore=None, infrastructureScore=None,
            environmentalScore=None, populationScore=None,
            confidenceScore=0.0,
            topStrengths=[], topRisks=[],
            isFullyEnriched=False,
            providerStatus={"wind": "UNAVAILABLE", "elevation": "UNAVAILABLE", "infrastructure": "UNAVAILABLE"},
            error=str(e),
        )


# ── Pass 2: full enriched + agents ────────────────────────────────────────────

async def _deep_score(p: LatLng, quick: ProspectingCandidate) -> ProspectingCandidate:
    try:
        metrics, debug, choice, enriched = await analyze_site_enriched(p)
        sc = compute_scores_from_enriched(metrics, enriched)

        agent_ctx = AgentContext(
            metrics=metrics, enriched=enriched, debug=debug, choice=choice,
            wind_score=sc["wind_score"], terrain_score=sc["terrain_score"],
            infra_score=sc["infra_s"], env_score=sc["env_s"], pop_score=sc["pop_s"],
            lc_score=sc["lc_score"], pa_score=sc["pa_score"],
            total_score=sc["total"], confidence_score=sc["confidence_score"],
        )
        agents_out = [
            WindAgent().run(agent_ctx),
            TerrainAgent().run(agent_ctx),
            InfrastructureAgent().run(agent_ctx),
            EnvironmentalAgent().run(agent_ctx),
            SocialAgent().run(agent_ctx),
        ]
        coord = CoordinatorAgent().run(agents_out, agent_ctx)

        # Economics
        eco = compute_economic_metrics(
            mean_wind_mps=metrics.get("windSpeedAtHub"),
            wind_score=sc["wind_score"],
            terrain_score=sc["terrain_score"],
            infra_score=sc["infra_s"],
            assumptions=EconomicAssumptions(),
        )

        base_total = sc["total"]
        total = apply_economic_nudge(base_total, eco.economic_score)

        return ProspectingCandidate(
            id=quick.id,
            latitude=p.latitude,
            longitude=p.longitude,
            totalSuitability=round(total, 1) if total is not None else None,
            finalDecision=coord.finalDecision,
            windScore=round(sc["wind_score"], 1) if sc["wind_score"] is not None else None,
            terrainScore=round(sc["terrain_score"], 1) if sc["terrain_score"] is not None else None,
            infrastructureScore=round(sc["infra_s"], 1) if sc["infra_s"] is not None else None,
            environmentalScore=round(sc["env_s"], 1) if sc["env_s"] is not None else None,
            populationScore=round(sc["pop_s"], 1) if sc["pop_s"] is not None else None,
            confidenceScore=round(sc["confidence_score"], 1),
            topStrengths=coord.topStrengths[:3],
            topRisks=coord.topRisks[:3],
            isFullyEnriched=True,
            providerStatus={
                "wind": "REAL" if choice.wind not in {"unavailable", "mock"} else choice.wind.upper(),
                "elevation": "REAL" if choice.elevation not in {"unavailable", "mock"} else choice.elevation.upper(),
                "infrastructure": "REAL" if choice.infrastructure == "osm_overpass" else "UNAVAILABLE",
            },
            economicScore=round(eco.economic_score, 1),
            lcoeUsdPerMwh=round(eco.lcoe_usd_per_mwh, 1),
            annualEnergyMwh=round(eco.annual_energy_mwh, 0),
            paybackYears=eco.payback_years,
            capacityFactor=round(eco.capacity_factor, 3),
        )
    except Exception as e:
        quick.error = str(e)
        return quick


# ── Clustering ─────────────────────────────────────────────────────────────────

_CLUSTER_LABELS = ["Zone A", "Zone B", "Zone C", "Zone D", "Zone E"]


def _cluster_candidates(
    candidates: list[ProspectingCandidate],
    *,
    cluster_radius_km: float = 20.0,
    max_clusters: int = 5,
    min_score: float = 40.0,
) -> list[ProspectingCluster]:
    eligible = sorted(
        [c for c in candidates if c.totalSuitability is not None and c.totalSuitability >= min_score],
        key=lambda c: c.totalSuitability or 0,
        reverse=True,
    )
    cluster_radius_m = cluster_radius_km * 1000.0

    states: list[_ClusterState] = []
    for cand in eligible:
        nearest: _ClusterState | None = None
        nearest_d = float("inf")
        for st in states:
            d = _haversine_m(cand.latitude, cand.longitude, st.centroid_lat, st.centroid_lng)
            if d < nearest_d:
                nearest_d = d
                nearest = st
        if nearest is not None and nearest_d <= cluster_radius_m:
            nearest.add(cand)
        elif len(states) < max_clusters:
            new_st = _ClusterState()
            new_st.add(cand)
            states.append(new_st)

    clusters: list[ProspectingCluster] = []
    for i, st in enumerate(states):
        avg = round(st.avg_score, 1)
        label = _CLUSTER_LABELS[i] if i < len(_CLUSTER_LABELS) else f"Zone {chr(65 + i)}"
        n = len(st.members)
        decision = st.top_decision
        summary = (
            f"{n} candidate{'s' if n != 1 else ''}, avg score {avg}/100, "
            f"assessment: {decision}"
        )
        clusters.append(ProspectingCluster(
            id=f"zone_{chr(97 + i)}",
            label=label,
            centroidLatitude=round(st.centroid_lat, 5),
            centroidLongitude=round(st.centroid_lng, 5),
            averageSuitability=avg,
            candidateCount=n,
            topDecision=decision,
            summary=summary,
        ))

    return clusters


# ── Main entry point ───────────────────────────────────────────────────────────

async def run_prospecting(
    center: LatLng,
    *,
    region_name: str = "Custom Region",
    radius_km: float = 75.0,
    grid_size: int = 5,
    max_candidates: int = 25,
    deep_analysis_count: int = 10,
) -> ProspectingResult:
    generated_at = utc_now_iso()
    prospecting_id = generate_analysis_id()

    # Generate grid points; trim to max_candidates
    raw_points = generate_grid_points(center, radius_km=radius_km, grid_size=grid_size)
    points = [p for _, _, p in raw_points[:max_candidates]]
    n = len(points)

    # ── Pass 1: quick wind + terrain (concurrency 5) ──────────────────────────
    sem1 = asyncio.Semaphore(5)

    async def _run_quick(p: LatLng) -> ProspectingCandidate:
        async with sem1:
            return await _quick_score(p)

    quick_results: list[ProspectingCandidate] = list(
        await asyncio.gather(*[_run_quick(p) for p in points])
    )

    # ── Pass 2: full enriched analysis on top candidates (concurrency 3) ──────
    scored = [c for c in quick_results if c.totalSuitability is not None]
    scored.sort(key=lambda c: c.totalSuitability or 0, reverse=True)
    deep_target = scored[:min(deep_analysis_count, len(scored))]
    deep_coords = {(round(c.latitude, 5), round(c.longitude, 5)) for c in deep_target}

    sem2 = asyncio.Semaphore(3)

    async def _run_deep(c: ProspectingCandidate) -> ProspectingCandidate:
        async with sem2:
            p = LatLng(latitude=c.latitude, longitude=c.longitude)
            return await _deep_score(p, c)

    deep_results: list[ProspectingCandidate] = list(
        await asyncio.gather(*[_run_deep(c) for c in deep_target])
    )

    # Merge: replace quick results with deep where available
    deep_map = {(round(c.latitude, 5), round(c.longitude, 5)): c for c in deep_results}
    final_candidates: list[ProspectingCandidate] = []
    for c in quick_results:
        key = (round(c.latitude, 5), round(c.longitude, 5))
        final_candidates.append(deep_map.get(key, c))

    # Sort: enriched first, then by score
    final_candidates.sort(
        key=lambda c: (not c.isFullyEnriched, -(c.totalSuitability or 0))
    )

    enriched_count = sum(1 for c in final_candidates if c.isFullyEnriched)

    # ── Clustering ──────────────────────────────────────────────────────────────
    clusters = _cluster_candidates(final_candidates)

    # Top candidates = fully enriched sorted by score, then quick if not enough
    top = sorted(
        [c for c in final_candidates if c.isFullyEnriched],
        key=lambda c: c.totalSuitability or 0, reverse=True,
    )[:10]

    # ── Methodology & audit trail ──────────────────────────────────────────────
    real_wind = sum(1 for c in final_candidates if c.providerStatus.get("wind") == "REAL")
    real_elev = sum(1 for c in final_candidates if c.providerStatus.get("elevation") == "REAL")
    real_infra = sum(1 for c in final_candidates if c.providerStatus.get("infrastructure") == "REAL")

    methodology = {
        "scoringFormulaVersion": SCORING_FORMULA_VERSION,
        "windDataSource": "NASA POWER (WS10M/WS50M)",
        "elevationSource": "OpenTopoData (SRTM90m)",
        "infrastructureSource": "OpenStreetMap (Overpass API) — top candidates only",
        "passOneScope": f"Wind + terrain screening of all {n} candidates",
        "passTwoScope": f"Full enriched analysis of top {enriched_count} candidates",
        "clusteringMethod": f"Greedy geographic clustering (20km radius, max 5 zones)",
        "realWindData": f"{real_wind}/{n} candidates",
        "realElevationData": f"{real_elev}/{n} candidates",
        "realInfrastructureData": f"{real_infra}/{n} candidates",
        "generatedAt": generated_at,
    }

    audit_trail = [
        f"Region: {region_name} ({center.latitude:.4f}, {center.longitude:.4f}), {radius_km:.0f}km radius",
        f"Grid: {grid_size}×{grid_size} = {n} candidate points generated",
        f"Pass 1: quick wind+terrain screening of {n} candidates (concurrency 5)",
        f"Pass 2: full enriched analysis of top {enriched_count} candidates (concurrency 3)",
        f"Clustering: {len(clusters)} zone{'s' if len(clusters) != 1 else ''} identified from candidates scoring ≥40",
        f"Prospecting completed at {generated_at} (prospectingId: {prospecting_id})",
    ]

    return ProspectingResult(
        prospectingId=prospecting_id,
        region={
            "name": region_name,
            "centerLatitude": center.latitude,
            "centerLongitude": center.longitude,
            "radiusKm": radius_km,
            "gridSize": grid_size,
        },
        generatedAt=generated_at,
        candidateCount=n,
        enrichedCount=enriched_count,
        candidates=final_candidates,
        clusters=clusters,
        topCandidates=top,
        methodology=methodology,
        auditTrail=audit_trail,
    )
