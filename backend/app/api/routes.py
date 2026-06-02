from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from fastapi.responses import Response

from app.agents import (
    AgentContext,
    CoordinatorAgent,
    EconomicAgent,
    EnvironmentalAgent,
    InfrastructureAgent,
    SocialAgent,
    TerrainAgent,
    WindAgent,
)
from app.agents.base import AgentEvidence as _AgentEvidence, AgentOutput as _AgentOutput
from app.api.schemas import (
    AgentAnalysis,
    AgentEvidence,
    AgentOutput,
    CoordinatorOutput,
    EconomicAssumptionsSchema,
    EconomicMetricsSchema,
    ProspectingCandidateSchema,
    ProspectingClusterSchema,
    ProspectingRequest,
    ProspectingResponse,
    SiteAnalysisRequest,
    SiteAnalysisResponse,
    SiteHeatmapRequest,
    SiteHeatmapResponse,
    SiteReportExportRequest,
)
from app.providers.base import LatLng
from app.services.analysis import analyze_site_enriched
from app.services.heatmap import build_heatmap
from app.services.economics import EconomicAssumptions, compute_economic_metrics
from app.services.prospecting import ProspectingCandidate, run_prospecting
from app.services.scoring import apply_economic_nudge
from app.services.methodology import (
    build_methodology,
    build_site_audit_trail,
    generate_analysis_id,
    utc_now_iso,
)
from app.services.pdf_export import generate_site_report_pdf
from app.services.report import build_report
from app.services.scoring import (
    environmental_score,
    infrastructure_score,
    land_cover_score,
    population_score,
    protected_area_score,
    total_suitability_v2,
)

router = APIRouter()


def _eco_to_schema(eco: "object") -> EconomicMetricsSchema:
    from app.services.economics import EconomicMetrics as _EcoMetrics
    e: _EcoMetrics = eco  # type: ignore[assignment]
    a = e.assumptions
    return EconomicMetricsSchema(
        capacityFactor=e.capacity_factor,
        annualEnergyMwh=e.annual_energy_mwh,
        capexUsd=e.capex_usd,
        opexUsdPerYear=e.opex_usd_per_year,
        annualRevenueUsd=e.annual_revenue_usd,
        paybackYears=e.payback_years,
        lcoeUsdPerMwh=e.lcoe_usd_per_mwh,
        economicScore=e.economic_score,
        windAvailable=e.wind_available,
        assumptions=EconomicAssumptionsSchema(
            turbineRatingMw=a.turbine_rating_mw,
            turbineCount=a.turbine_count,
            electricityPriceUsdPerMwh=a.electricity_price_usd_per_mwh,
            capexUsdPerMw=a.capex_usd_per_mw,
            opexPctOfCapex=a.opex_pct_of_capex,
            projectLifeYears=a.project_life_years,
            discountRate=a.discount_rate,
        ),
        limitations=e.limitations,
    )


def _to_pydantic_agent(out: _AgentOutput) -> AgentOutput:
    return AgentOutput(
        agentName=out.agentName,
        status=out.status,
        confidence=out.confidence,
        summary=out.summary,
        findings=out.findings,
        risks=out.risks,
        recommendations=out.recommendations,
        evidence=[AgentEvidence(label=e.label, value=e.value, source=e.source) for e in out.evidence],
    )


@router.post("/api/site-analysis", response_model=SiteAnalysisResponse)
async def site_analysis(req: SiteAnalysisRequest) -> SiteAnalysisResponse:
    p = LatLng(latitude=req.latitude, longitude=req.longitude)

    metrics_fragment, sources_debug, choice, enriched = await analyze_site_enriched(p)

    wind_score = metrics_fragment["windScore"]
    terrain_score = metrics_fragment["terrainScore"]
    confidence_score = float(metrics_fragment["confidenceScore"])
    elevation_m = metrics_fragment["elevationM"]
    terrain_complexity = metrics_fragment["terrainComplexity"]
    slope_pct = metrics_fragment.get("slopePct")
    ridge_score = metrics_fragment.get("ridgeScore")
    wind_speed_at_hub = metrics_fragment.get("windSpeedAtHub")

    infra_data = enriched["infrastructure"]
    lc_data = enriched["land_cover"]
    pa_data = enriched["protected_area"]

    infra_s: float | None = None
    nearest_road: float | None = None
    nearest_power: float | None = None
    settlement_count: int | None = None
    if infra_data is not None:
        nearest_road = infra_data.get("nearest_road_m")
        nearest_power = infra_data.get("nearest_powerline_m")
        settlement_count = infra_data.get("settlement_count_15km")
        infra_s = infrastructure_score(nearest_road, nearest_power)

    lc_score: float | None = None
    lc_class: str | None = None
    if lc_data is not None:
        lc_class = lc_data.get("cover_class")
        lc_score = land_cover_score(lc_class)

    pa_score: float | None = None
    pa_risk: str | None = None
    in_pa: bool | None = None
    nearest_pa_m: float | None = None
    if pa_data is not None:
        in_pa = pa_data.get("in_protected_area", False)
        nearest_pa_m = pa_data.get("nearest_pa_m")
        pa_score = protected_area_score(in_pa, nearest_pa_m)
        pa_risk = pa_data.get("biodiversity_risk")

    env_s: float | None = None
    if lc_score is not None and pa_score is not None:
        env_s = environmental_score(lc_score, pa_score)
    elif lc_score is not None:
        env_s = lc_score
    elif pa_score is not None:
        env_s = pa_score

    pop_s: float | None = None
    if settlement_count is not None:
        pop_s = population_score(settlement_count)

    base_total = total_suitability_v2(
        wind_score=wind_score,
        terrain_score=terrain_score,
        infra_score=infra_s,
        env_score=env_s,
        pop_score=pop_s,
        confidence_score=confidence_score,
    )

    # ── Economic metrics ──────────────────────────────────────────────────────
    eco = compute_economic_metrics(
        mean_wind_mps=wind_speed_at_hub,
        wind_score=wind_score,
        terrain_score=terrain_score,
        infra_score=infra_s,
        assumptions=EconomicAssumptions(),
    )
    total = apply_economic_nudge(base_total, eco.economic_score)

    # ── Agent analysis ────────────────────────────────────────────────────────
    agent_ctx = AgentContext(
        metrics=metrics_fragment,
        enriched=enriched,
        debug=sources_debug,
        choice=choice,
        wind_score=wind_score,
        terrain_score=terrain_score,
        infra_score=infra_s,
        env_score=env_s,
        pop_score=pop_s,
        lc_score=lc_score,
        pa_score=pa_score,
        total_score=total,
        confidence_score=confidence_score,
        economic_metrics=eco,
    )
    agents_out = [
        WindAgent().run(agent_ctx),
        TerrainAgent().run(agent_ctx),
        InfrastructureAgent().run(agent_ctx),
        EnvironmentalAgent().run(agent_ctx),
        SocialAgent().run(agent_ctx),
        EconomicAgent().run(agent_ctx),
    ]
    coordinator_out = CoordinatorAgent().run(agents_out, agent_ctx)

    agent_analysis = AgentAnalysis(
        agents=[_to_pydantic_agent(a) for a in agents_out],
        coordinator=CoordinatorOutput(
            finalDecision=coordinator_out.finalDecision,
            topStrengths=coordinator_out.topStrengths,
            topRisks=coordinator_out.topRisks,
            nextSteps=coordinator_out.nextSteps,
            confidenceSummary=coordinator_out.confidenceSummary,
            contradictionNotes=coordinator_out.contradictionNotes,
        ),
    )

    data_sources = [
        "Wind: NASA POWER (WS10M/WS50M/WS100M)",
        "Elevation: OpenTopoData (SRTM90m)",
    ]
    if choice.infrastructure == "osm_overpass":
        data_sources.append("Infrastructure: OpenStreetMap (Overpass API)")
    else:
        data_sources.append("Infrastructure: unavailable (OSM timeout or no data)")

    report = build_report(
        total=total,
        wind=wind_score,
        terrain=terrain_score,
        confidence=confidence_score,
        elevation_m=elevation_m,
        terrain_complexity=terrain_complexity,
        infra_score=infra_s,
        lc_class=lc_class,
        pa_risk=pa_risk,
        in_pa=in_pa,
        pop_score=pop_s,
        data_sources=data_sources,
        coordinator_decision=coordinator_out.finalDecision,
    )

    generated_at = utc_now_iso()
    analysis_id = generate_analysis_id()
    methodology = build_methodology(sources_debug, choice, generated_at=generated_at)
    audit_trail = build_site_audit_trail(
        latitude=req.latitude,
        longitude=req.longitude,
        choice=choice,
        generated_at=generated_at,
        analysis_id=analysis_id,
    )

    return SiteAnalysisResponse(
        analysisId=analysis_id,
        methodology=methodology,  # type: ignore[arg-type]
        auditTrail=audit_trail,
        inputs=req,
        metrics={
            "windScore": wind_score,
            "terrainScore": terrain_score,
            "confidenceScore": confidence_score,
            "elevationM": elevation_m,
            "terrainComplexity": terrain_complexity,
            "slopePct": slope_pct,
            "ridgeScore": ridge_score,
            "windSpeedAtHub": wind_speed_at_hub,
            "infrastructureScore": infra_s,
            "nearestRoadM": nearest_road,
            "nearestPowerlineM": nearest_power,
            "settlementCount15km": settlement_count,
            "environmentalScore": env_s,
            "landCoverClass": lc_class,
            "landCoverScore": lc_score,
            "protectedAreaRisk": pa_risk,
            "protectedAreaScore": pa_score,
            "inProtectedArea": in_pa,
            "populationScore": pop_s,
            "accessibilityScore": infra_s if infra_s is not None else 50.0,
        },
        totalSuitabilityScore=total,
        report=report,  # type: ignore[arg-type]
        agentAnalysis=agent_analysis,
        economicMetrics=_eco_to_schema(eco),
        debug={**sources_debug},
    )


@router.post("/api/site-heatmap", response_model=SiteHeatmapResponse)
async def site_heatmap(req: SiteHeatmapRequest) -> SiteHeatmapResponse:
    center = LatLng(latitude=req.latitude, longitude=req.longitude)
    result = await build_heatmap(
        center,
        radius_km=req.radiusKm,
        grid_size=req.gridSize,
    )
    return SiteHeatmapResponse(**result)  # type: ignore[arg-type]


@router.post("/api/site-report/export")
async def export_site_report(req: SiteReportExportRequest) -> Response:
    pdf_bytes = generate_site_report_pdf(req.analysis, req.heatmap)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="chitta-site-assessment.pdf"'
        },
    )


def _candidate_to_schema(c: ProspectingCandidate) -> ProspectingCandidateSchema:
    return ProspectingCandidateSchema(
        id=c.id,
        latitude=c.latitude,
        longitude=c.longitude,
        totalSuitability=c.totalSuitability,
        finalDecision=c.finalDecision,
        windScore=c.windScore,
        terrainScore=c.terrainScore,
        infrastructureScore=c.infrastructureScore,
        environmentalScore=c.environmentalScore,
        populationScore=c.populationScore,
        confidenceScore=c.confidenceScore,
        topStrengths=c.topStrengths,
        topRisks=c.topRisks,
        isFullyEnriched=c.isFullyEnriched,
        providerStatus=c.providerStatus,
        economicScore=c.economicScore,
        lcoeUsdPerMwh=c.lcoeUsdPerMwh,
        annualEnergyMwh=c.annualEnergyMwh,
        paybackYears=c.paybackYears,
        capacityFactor=c.capacityFactor,
        error=c.error,
    )


@router.post("/api/prospecting/run", response_model=ProspectingResponse)
async def run_prospecting_endpoint(req: ProspectingRequest) -> ProspectingResponse:
    center = LatLng(latitude=req.centerLatitude, longitude=req.centerLongitude)
    result = await run_prospecting(
        center,
        region_name=req.regionName,
        radius_km=req.radiusKm,
        grid_size=req.gridSize,
        max_candidates=req.maxCandidates,
    )
    return ProspectingResponse(
        prospectingId=result.prospectingId,
        region=result.region,  # type: ignore[arg-type]
        generatedAt=result.generatedAt,
        candidateCount=result.candidateCount,
        enrichedCount=result.enrichedCount,
        candidates=[_candidate_to_schema(c) for c in result.candidates],
        clusters=[
            ProspectingClusterSchema(
                id=cl.id, label=cl.label,
                centroidLatitude=cl.centroidLatitude, centroidLongitude=cl.centroidLongitude,
                averageSuitability=cl.averageSuitability, candidateCount=cl.candidateCount,
                topDecision=cl.topDecision, summary=cl.summary,
            )
            for cl in result.clusters
        ],
        topCandidates=[_candidate_to_schema(c) for c in result.topCandidates],
        methodology=result.methodology,  # type: ignore[arg-type]
        auditTrail=result.auditTrail,
    )
