"""
Evidence packet builder for CHITTA AI synthesis layer.

Converts deterministic analysis outputs into compact, grounded evidence packets
with stable IDs the LLM can reference in citations.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.api.schemas import (
    ProspectingResponse,
    SimulationResponse,
    SiteAnalysisResponse,
)


@dataclass
class EvidencePacket:
    evidenceId: str
    category: str
    label: str
    value: str
    unit: str | None
    source: str
    quality: str  # "measured" | "computed" | "estimated" | "unavailable"

    def to_dict(self) -> dict:
        return {
            "evidenceId": self.evidenceId,
            "category": self.category,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "quality": self.quality,
        }


def _fmt(v: float | None, decimals: int = 1) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}"


def _pkt(
    eid: str,
    cat: str,
    label: str,
    value: float | str | None,
    unit: str | None,
    source: str,
    quality: str,
    decimals: int = 1,
) -> EvidencePacket | None:
    if value is None:
        return None
    str_val = _fmt(value, decimals) if isinstance(value, float) else str(value)
    return EvidencePacket(
        evidenceId=eid,
        category=cat,
        label=label,
        value=str_val,
        unit=unit,
        source=source,
        quality=quality,
    )


def _site_packets(analysis: SiteAnalysisResponse) -> list[EvidencePacket]:
    m = analysis.metrics
    eco = analysis.economicMetrics
    ag = analysis.agentAnalysis
    packets: list[EvidencePacket | None] = []

    # ── Score evidence ─────────────────────────────────────────────────────────
    packets.append(_pkt(
        "score:total_suitability", "score", "Total suitability score",
        analysis.totalSuitabilityScore, "/100", "CHITTA v2.1", "computed", 1,
    ))
    packets.append(_pkt(
        "score:confidence", "score", "Data confidence score",
        m.confidenceScore, "/100", "CHITTA v2.1", "computed", 1,
    ))
    if ag:
        packets.append(_pkt(
            "score:decision", "score", "Coordinator decision",
            ag.coordinator.finalDecision, None, "CHITTA CoordinatorAgent", "computed",
        ))

    # ── Wind evidence ──────────────────────────────────────────────────────────
    packets.append(_pkt(
        "wind:score", "wind", "Wind suitability score",
        m.windScore, "/100", "NASA POWER", "computed", 1,
    ))
    packets.append(_pkt(
        "wind:speed_at_hub", "wind", "Mean wind speed at hub height",
        m.windSpeedAtHub, "m/s", "NASA POWER (WS50M/WS10M)", "measured", 2,
    ))

    # ── Terrain evidence ───────────────────────────────────────────────────────
    packets.append(_pkt(
        "terrain:score", "terrain", "Terrain suitability score",
        m.terrainScore, "/100", "OpenTopoData SRTM90m", "computed", 1,
    ))
    packets.append(_pkt(
        "terrain:elevation", "terrain", "Elevation",
        m.elevationM, "m", "OpenTopoData SRTM90m", "measured", 0,
    ))
    packets.append(_pkt(
        "terrain:slope", "terrain", "Slope",
        m.slopePct, "%", "OpenTopoData SRTM90m", "computed", 2,
    ))
    packets.append(_pkt(
        "terrain:ridge_score", "terrain", "Ridge score",
        m.ridgeScore, None, "OpenTopoData SRTM90m", "computed", 2,
    ))

    # ── Infrastructure evidence ────────────────────────────────────────────────
    packets.append(_pkt(
        "infra:score", "infra", "Infrastructure access score",
        m.infrastructureScore, "/100", "OpenStreetMap Overpass", "computed", 1,
    ))
    packets.append(_pkt(
        "infra:nearest_road", "infra", "Distance to nearest road",
        m.nearestRoadM, "m", "OpenStreetMap Overpass", "measured", 0,
    ))
    packets.append(_pkt(
        "infra:nearest_powerline", "infra", "Distance to nearest powerline",
        m.nearestPowerlineM, "m", "OpenStreetMap Overpass", "measured", 0,
    ))
    packets.append(_pkt(
        "infra:settlement_count", "infra", "Settlement count within 15 km",
        m.settlementCount15km, "settlements", "OpenStreetMap Overpass", "measured",
    ))

    # ── Environmental evidence ─────────────────────────────────────────────────
    packets.append(_pkt(
        "env:score", "env", "Environmental suitability score",
        m.environmentalScore, "/100", "CHITTA v2.1", "computed", 1,
    ))
    if m.landCoverClass is not None:
        packets.append(EvidencePacket(
            evidenceId="env:land_cover",
            category="env",
            label="Land cover class",
            value=m.landCoverClass,
            unit=None,
            source="ESA WorldCover (via CHITTA)",
            quality="estimated",
        ))
    packets.append(_pkt(
        "env:land_cover_score", "env", "Land cover score",
        m.landCoverScore, "/100", "CHITTA v2.1", "computed", 1,
    ))
    if m.protectedAreaRisk is not None:
        packets.append(EvidencePacket(
            evidenceId="env:protected_area_risk",
            category="env",
            label="Protected area risk",
            value=m.protectedAreaRisk,
            unit=None,
            source="CHITTA biodiversity heuristic",
            quality="estimated",
        ))
    packets.append(_pkt(
        "env:protected_area_score", "env", "Protected area score",
        m.protectedAreaScore, "/100", "CHITTA v2.1", "computed", 1,
    ))
    if m.inProtectedArea is not None:
        packets.append(EvidencePacket(
            evidenceId="env:in_protected_area",
            category="env",
            label="Inside protected area",
            value="yes" if m.inProtectedArea else "no",
            unit=None,
            source="CHITTA v2.1",
            quality="estimated",
        ))

    # ── Social / population evidence ───────────────────────────────────────────
    packets.append(_pkt(
        "social:population_score", "social", "Population / social friction score",
        m.populationScore, "/100", "OpenStreetMap settlements", "estimated", 1,
    ))

    # ── Economic evidence ──────────────────────────────────────────────────────
    if eco is not None:
        packets.append(_pkt(
            "economic:score", "economic", "Economic viability score",
            eco.economicScore, "/100", "CHITTA economics v1.0", "estimated", 1,
        ))
        packets.append(_pkt(
            "economic:lcoe", "economic", "Estimated LCOE",
            eco.lcoeUsdPerMwh, "USD/MWh", "CHITTA economics v1.0", "estimated", 1,
        ))
        packets.append(_pkt(
            "economic:payback", "economic", "Estimated payback period",
            eco.paybackYears, "years", "CHITTA economics v1.0", "estimated", 1,
        ))
        packets.append(_pkt(
            "economic:capacity_factor", "economic", "Capacity factor",
            eco.capacityFactor, None, "CHITTA economics v1.0", "estimated", 3,
        ))
        packets.append(_pkt(
            "economic:annual_energy", "economic", "Annual energy output",
            eco.annualEnergyMwh, "MWh/year", "CHITTA economics v1.0", "estimated", 0,
        ))
        packets.append(_pkt(
            "economic:capex", "economic", "Total CAPEX",
            eco.capexUsd, "USD", "CHITTA economics v1.0", "estimated", 0,
        ))
        a = eco.assumptions
        packets.append(EvidencePacket(
            evidenceId="economic:assumptions",
            category="economic",
            label="Economic assumptions",
            value=(
                f"{a.turbineCount} × {a.turbineRatingMw} MW turbines, "
                f"${a.electricityPriceUsdPerMwh}/MWh tariff, "
                f"${a.capexUsdPerMw:,.0f}/MW CAPEX, "
                f"{a.projectLifeYears} year life"
            ),
            unit=None,
            source="CHITTA economics v1.0 defaults",
            quality="estimated",
        ))

    # ── Agent evidence ─────────────────────────────────────────────────────────
    if ag is not None:
        for agent_out in ag.agents:
            safe_name = agent_out.agentName.lower().replace(" ", "_")
            eid = f"agent:{safe_name}"
            summary_parts = [agent_out.summary]
            if agent_out.findings:
                summary_parts.append("Findings: " + "; ".join(agent_out.findings[:2]))
            if agent_out.risks:
                summary_parts.append("Risks: " + "; ".join(agent_out.risks[:2]))
            packets.append(EvidencePacket(
                evidenceId=eid,
                category="agent",
                label=f"{agent_out.agentName} agent analysis",
                value=" | ".join(summary_parts),
                unit=None,
                source=f"CHITTA {agent_out.agentName}",
                quality="computed",
            ))
        coord = ag.coordinator
        packets.append(EvidencePacket(
            evidenceId="agent:coordinator",
            category="agent",
            label="Coordinator synthesis",
            value=(
                f"Decision: {coord.finalDecision} | "
                f"Strengths: {'; '.join(coord.topStrengths[:2])} | "
                f"Risks: {'; '.join(coord.topRisks[:2])}"
            ),
            unit=None,
            source="CHITTA CoordinatorAgent",
            quality="computed",
        ))

    # ── Development Risk evidence ──────────────────────────────────────────────
    do = analysis.developmentOutlook
    if do is not None:
        packets.append(_pkt(
            "risk:outlook", "risk", "Development outlook",
            do.developmentOutlook, None, "CHITTA Risk Engine", "computed",
        ))
        packets.append(_pkt(
            "risk:fatal_flaw_count", "risk", "Fatal flaw count",
            float(do.riskRegister.fatalFlawCount), None, "CHITTA Risk Engine", "computed", 0,
        ))
        packets.append(_pkt(
            "risk:critical_flaw_count", "risk", "Critical fatal flaw count",
            float(do.riskRegister.criticalFatalFlawCount), None, "CHITTA Risk Engine", "computed", 0,
        ))
        packets.append(_pkt(
            "risk:fitness_score", "risk", "Project fitness score",
            do.fitnessTest.fitnessScore, "/10", "CHITTA Fitness Engine", "computed", 1,
        ))
        packets.append(_pkt(
            "risk:fitness_band", "risk", "Project risk band",
            do.fitnessTest.riskBand, None, "CHITTA Fitness Engine", "computed",
        ))
        for item in do.riskRegister.categories:
            slug = item.category.lower().replace(" / ", "_").replace("/", "_").replace(" ", "_")
            packets.append(_pkt(
                f"risk:{slug}:level", "risk", f"{item.category} risk level",
                item.level, None, "CHITTA Risk Engine", "computed",
            ))

    # ── Evidence Quality packets ──────────────────────────────────────────────
    eq = analysis.evidenceQuality
    if eq is not None:
        packets.append(_pkt(
            "quality:overall", "quality", "Overall evidence quality",
            eq.overallQuality, None, "CHITTA Quality Engine", "computed",
        ))
        packets.append(_pkt(
            "quality:overall_confidence", "quality", "Overall data confidence",
            eq.overallConfidence, "/100", "CHITTA Quality Engine", "computed", 1,
        ))
        for item in eq.items:
            slug = item.dimension.lower()
            packets.append(_pkt(
                f"quality:{slug}:level", "quality", f"{item.dimension} data quality",
                item.quality, None, "CHITTA Quality Engine", "computed",
            ))
            packets.append(_pkt(
                f"quality:{slug}:confidence", "quality", f"{item.dimension} confidence",
                item.confidence, "/100", "CHITTA Quality Engine", "computed", 1,
            ))

    # ── Information Value packets ─────────────────────────────────────────────
    iv = analysis.informationValue
    if iv is not None:
        if iv.topPriority:
            packets.append(_pkt(
                "infovalue:top_priority", "infovalue", "Highest-value missing information",
                iv.topPriority, None, "CHITTA InfoValue Engine", "computed",
            ))
        for item in iv.items[:5]:
            slug = item.category.lower().replace(" ", "_").replace("/", "_").replace("&", "and")
            packets.append(_pkt(
                f"infovalue:{slug}:value", "infovalue", f"Information value: {item.category}",
                item.informationValue, "/10", "CHITTA InfoValue Engine", "computed", 1,
            ))

    return [p for p in packets if p is not None]


def _prospecting_packets(prospecting: ProspectingResponse) -> list[EvidencePacket]:
    packets: list[EvidencePacket] = []

    region = prospecting.region
    packets.append(EvidencePacket(
        evidenceId="prospecting:region",
        category="prospecting",
        label="Prospecting region",
        value=f"{region.get('name', 'Custom')} — centre {region.get('centerLatitude', 0):.3f}°, {region.get('centerLongitude', 0):.3f}° — radius {region.get('radiusKm', 0):.0f} km",
        unit=None,
        source="CHITTA prospecting engine",
        quality="measured",
    ))
    packets.append(EvidencePacket(
        evidenceId="prospecting:candidate_count",
        category="prospecting",
        label="Candidate sites screened",
        value=str(prospecting.candidateCount),
        unit="sites",
        source="CHITTA two-pass prospecting",
        quality="measured",
    ))
    packets.append(EvidencePacket(
        evidenceId="prospecting:enriched_count",
        category="prospecting",
        label="Fully enriched candidates",
        value=str(prospecting.enrichedCount),
        unit="sites",
        source="CHITTA two-pass prospecting",
        quality="measured",
    ))

    for i, tc in enumerate(prospecting.topCandidates[:5]):
        rank = i + 1
        eid = f"prospecting:top_candidate:{rank}"
        eco_str = ""
        if tc.lcoeUsdPerMwh is not None:
            eco_str = f" | LCOE ${tc.lcoeUsdPerMwh:.0f}/MWh"
        if tc.paybackYears is not None:
            eco_str += f" | Payback {tc.paybackYears:.0f} yr"
        packets.append(EvidencePacket(
            evidenceId=eid,
            category="prospecting",
            label=f"Top candidate #{rank}",
            value=(
                f"Lat {tc.latitude:.3f}, Lon {tc.longitude:.3f} | "
                f"Score {tc.totalSuitability:.1f}/100 | "
                f"Decision: {tc.finalDecision}{eco_str}"
            ),
            unit=None,
            source="CHITTA two-pass prospecting",
            quality="computed",
        ))

    for cl in prospecting.clusters[:4]:
        eid = f"prospecting:cluster:{cl.id}"
        packets.append(EvidencePacket(
            evidenceId=eid,
            category="prospecting",
            label=f"Cluster: {cl.label}",
            value=(
                f"{cl.candidateCount} sites | avg score {cl.averageSuitability:.1f}/100 | "
                f"top decision: {cl.topDecision} | {cl.summary}"
            ),
            unit=None,
            source="CHITTA greedy clustering",
            quality="computed",
        ))

    if prospecting.topCandidates:
        scores = [c.totalSuitability for c in prospecting.topCandidates if c.totalSuitability is not None]
        if scores:
            avg = sum(scores) / len(scores)
            packets.append(EvidencePacket(
                evidenceId="prospecting:top_score_range",
                category="prospecting",
                label="Top candidate score range",
                value=f"Max {max(scores):.1f}, Min {min(scores):.1f}, Avg {avg:.1f}",
                unit="/100",
                source="CHITTA two-pass prospecting",
                quality="computed",
            ))

    return packets


def _simulation_packets(simulation: SimulationResponse) -> list[EvidencePacket]:
    packets: list[EvidencePacket] = []
    cfg = simulation.config

    packets.append(EvidencePacket(
        evidenceId="sim:config",
        category="simulation",
        label="Simulation configuration",
        value=(
            f"{cfg.turbineCount} × {cfg.turbineRatingMw} MW turbines | "
            f"${cfg.electricityPriceUsdPerMwh}/MWh | "
            f"${cfg.capexUsdPerMw:,.0f}/MW CAPEX | "
            f"{cfg.projectLifeYears} yr | "
            f"env={cfg.environmentalStrictness} | "
            f"infra={cfg.infrastructurePreference}"
        ),
        unit=None,
        source="CHITTA simulation engine sim-1.0",
        quality="computed",
    ))

    changes_up = [rc for rc in simulation.rankingChanges if rc.direction == "up"]
    changes_down = [rc for rc in simulation.rankingChanges if rc.direction == "down"]
    packets.append(EvidencePacket(
        evidenceId="sim:ranking_changes",
        category="simulation",
        label="Ranking changes summary",
        value=(
            f"{len(simulation.rankingChanges)} candidates re-ranked | "
            f"{len(changes_up)} moved up | {len(changes_down)} moved down"
        ),
        unit=None,
        source="CHITTA simulation engine sim-1.0",
        quality="computed",
    ))

    if simulation.strongestCandidate:
        s = simulation.strongestCandidate
        packets.append(EvidencePacket(
            evidenceId="sim:strongest_candidate",
            category="simulation",
            label="Strongest candidate post-simulation",
            value=f"Lat {s.latitude:.3f}, Lon {s.longitude:.3f} | Score {s.newTotalSuitability:.1f}/100 | Decision: {s.newDecision}",
            unit=None,
            source="CHITTA simulation engine sim-1.0",
            quality="computed",
        ))
    if simulation.weakestCandidate:
        w = simulation.weakestCandidate
        packets.append(EvidencePacket(
            evidenceId="sim:weakest_candidate",
            category="simulation",
            label="Weakest candidate post-simulation",
            value=f"Lat {w.latitude:.3f}, Lon {w.longitude:.3f} | Score {w.newTotalSuitability:.1f}/100 | Decision: {w.newDecision}",
            unit=None,
            source="CHITTA simulation engine sim-1.0",
            quality="computed",
        ))
    if simulation.mostImprovedCandidate:
        mi = simulation.mostImprovedCandidate
        packets.append(EvidencePacket(
            evidenceId="sim:most_improved",
            category="simulation",
            label="Most improved candidate",
            value=f"Lat {mi.latitude:.3f}, Lon {mi.longitude:.3f} | Delta {mi.suitabilityDelta:+.1f} pts",
            unit=None,
            source="CHITTA simulation engine sim-1.0",
            quality="computed",
        ))
    if simulation.mostSensitiveCandidate:
        ms = simulation.mostSensitiveCandidate
        packets.append(EvidencePacket(
            evidenceId="sim:most_sensitive",
            category="simulation",
            label="Most sensitive candidate (largest absolute delta)",
            value=f"Lat {ms.latitude:.3f}, Lon {ms.longitude:.3f} | |Delta| {abs(ms.suitabilityDelta or 0):.1f} pts",
            unit=None,
            source="CHITTA simulation engine sim-1.0",
            quality="computed",
        ))

    return packets


def build_evidence_packets(
    mode: str,
    site_analysis: SiteAnalysisResponse | None,
    prospecting: ProspectingResponse | None,
    simulation: SimulationResponse | None,
) -> list[EvidencePacket]:
    packets: list[EvidencePacket] = []

    if site_analysis is not None:
        packets.extend(_site_packets(site_analysis))

    if prospecting is not None:
        packets.extend(_prospecting_packets(prospecting))

    if simulation is not None:
        packets.extend(_simulation_packets(simulation))

    return packets
