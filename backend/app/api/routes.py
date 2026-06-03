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
    CandidateRankingChange,
    CoordinatorOutput,
    EconomicAssumptionsSchema,
    EconomicMetricsSchema,
    ProspectingCandidateSchema,
    ProspectingClusterSchema,
    ProspectingRequest,
    ProspectingResponse,
    SimulatedCandidateSchema,
    SimulationRequest,
    SimulationResponse,
    SiteAnalysisRequest,
    SiteAnalysisResponse,
    SiteHeatmapRequest,
    SiteHeatmapResponse,
    SiteReportExportRequest,
    LayoutAnalysisRequest,
    LayoutAnalysisResponse,
    ProspectingReportExportRequest,
    SynthesisRequest,
    SynthesisResponse,
    TurbinePositionSchema,
)
from app.providers.base import LatLng
from app.services.analysis import analyze_site_enriched
from app.services.heatmap import build_heatmap
from app.services.economics import EconomicAssumptions, compute_economic_metrics
from app.services.prospecting import ProspectingCandidate, run_prospecting
from app.services.simulation import (
    CandidateInput,
    CandidateRankingChange as _SvcRankingChange,
    SimulatedCandidate as _SvcSimCandidate,
    SimulationConfig,
    run_simulation,
)
from app.services.scoring import apply_economic_nudge
from app.services.methodology import (
    build_methodology,
    build_site_audit_trail,
    generate_analysis_id,
    utc_now_iso,
)
from app.services.pdf_export import generate_site_report_pdf
from app.services.prospecting_pdf import generate_prospecting_report_pdf
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


@router.post("/api/prospecting-report/export")
async def export_prospecting_report(req: ProspectingReportExportRequest) -> Response:
    pdf_bytes = generate_prospecting_report_pdf(
        req.prospecting,
        req.simulation,
        req.synthesis,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="chitta-prospecting-report.pdf"'
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


def _sim_candidate_to_schema(s: _SvcSimCandidate) -> SimulatedCandidateSchema:
    return SimulatedCandidateSchema(
        id=s.id,
        latitude=s.latitude,
        longitude=s.longitude,
        originalTotalSuitability=s.originalTotalSuitability,
        newTotalSuitability=s.newTotalSuitability,
        suitabilityDelta=s.suitabilityDelta,
        originalDecision=s.originalDecision,
        newDecision=s.newDecision,
        newEconomicScore=s.newEconomicScore,
        newLcoeUsdPerMwh=s.newLcoeUsdPerMwh,
        newAnnualEnergyMwh=s.newAnnualEnergyMwh,
        newPaybackYears=s.newPaybackYears,
        newCapacityFactor=s.newCapacityFactor,
        topStrengths=s.topStrengths,
        topRisks=s.topRisks,
    )


@router.post("/api/simulation/run", response_model=SimulationResponse)
async def run_simulation_endpoint(request: SimulationRequest) -> SimulationResponse:
    cfg_s = request.config
    config = SimulationConfig(
        turbineCount=cfg_s.turbineCount,
        turbineRatingMw=cfg_s.turbineRatingMw,
        electricityPriceUsdPerMwh=cfg_s.electricityPriceUsdPerMwh,
        capexUsdPerMw=cfg_s.capexUsdPerMw,
        opexPercentOfCapex=cfg_s.opexPercentOfCapex,
        projectLifeYears=cfg_s.projectLifeYears,
        windWeight=cfg_s.windWeight,
        terrainWeight=cfg_s.terrainWeight,
        infrastructureWeight=cfg_s.infrastructureWeight,
        environmentalWeight=cfg_s.environmentalWeight,
        populationWeight=cfg_s.populationWeight,
        confidenceWeight=cfg_s.confidenceWeight,
        economicWeight=cfg_s.economicWeight,
        environmentalStrictness=cfg_s.environmentalStrictness,
        infrastructurePreference=cfg_s.infrastructurePreference,
    )
    inputs = [
        CandidateInput(
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
            capacityFactor=c.capacityFactor,
            topStrengths=c.topStrengths,
            topRisks=c.topRisks,
        )
        for c in request.candidates
    ]
    result = run_simulation(inputs, config)
    return SimulationResponse(
        simulationId=result.simulationId,
        config=request.config,
        recomputedCandidates=[_sim_candidate_to_schema(s) for s in result.recomputedCandidates],
        rankingChanges=[
            CandidateRankingChange(
                id=rc.id,
                latitude=rc.latitude,
                longitude=rc.longitude,
                originalRank=rc.originalRank,
                newRank=rc.newRank,
                rankChange=rc.rankChange,
                direction=rc.direction,
            )
            for rc in result.rankingChanges
        ],
        strongestCandidate=(
            _sim_candidate_to_schema(result.strongestCandidate)
            if result.strongestCandidate else None
        ),
        weakestCandidate=(
            _sim_candidate_to_schema(result.weakestCandidate)
            if result.weakestCandidate else None
        ),
        mostImprovedCandidate=(
            _sim_candidate_to_schema(result.mostImprovedCandidate)
            if result.mostImprovedCandidate else None
        ),
        mostSensitiveCandidate=(
            _sim_candidate_to_schema(result.mostSensitiveCandidate)
            if result.mostSensitiveCandidate else None
        ),
        methodology=result.methodology,
        auditTrail=result.auditTrail,
    )


@router.post("/api/layout/analyze", response_model=LayoutAnalysisResponse)
async def analyze_layout(req: LayoutAnalysisRequest) -> LayoutAnalysisResponse:
    from app.services.layout import LayoutAssumptions, generate_candidate_layout

    wind_defaulted = req.prevailingWindDirectionDeg is None
    assumptions = LayoutAssumptions(
        rotor_diameter_m=req.rotorDiameterM,
        turbine_rating_mw=req.turbineRatingMw,
        prevailing_wind_direction_deg=req.prevailingWindDirectionDeg if req.prevailingWindDirectionDeg is not None else 270.0,
    )
    result = generate_candidate_layout(
        center_lat=req.latitude,
        center_lng=req.longitude,
        turbine_count=req.turbineCount,
        assumptions=assumptions,
        wind_direction_was_defaulted=wind_defaulted,
    )
    a = result.assumptions
    assumptions_dict = {
        "rotorDiameterM": f"{a.rotor_diameter_m:.0f} m",
        "turbineRatingMw": f"{a.turbine_rating_mw:.1f} MW",
        "crosswindSpacing": f"{a.crosswind_spacing_rotor_diameters:.1f}D ({a.crosswind_spacing_rotor_diameters * a.rotor_diameter_m:.0f} m)",
        "downwindSpacing": f"{a.downwind_spacing_rotor_diameters:.1f}D ({a.downwind_spacing_rotor_diameters * a.rotor_diameter_m:.0f} m)",
        "prevailingWindFrom": f"{a.prevailing_wind_direction_deg:.0f}° {'(defaulted)' if wind_defaulted else '(provided)'}",
        "wakeDecayConstant": str(a.wake_decay_constant),
        "thrustCoefficient": str(a.thrust_coefficient),
    }
    return LayoutAnalysisResponse(
        layoutId=result.layout_id,
        turbines=[TurbinePositionSchema(id=t.id, latitude=t.latitude, longitude=t.longitude) for t in result.turbines],
        spacingViolations=result.spacing_violations,
        estimatedWakeLossPercent=result.estimated_wake_loss_percent,
        layoutEfficiencyScore=result.layout_efficiency_score,
        assumptions=assumptions_dict,
        warnings=result.warnings,
        methodology=result.methodology,
        auditTrail=result.audit_trail,
        generatedAt=result.generated_at,
    )


@router.post("/api/ai/synthesize", response_model=SynthesisResponse)
async def ai_synthesize(req: SynthesisRequest) -> SynthesisResponse:
    from app.synthesis.service import synthesize
    result = await synthesize(
        mode=req.mode,
        site_analysis=req.siteAnalysis,
        prospecting=req.prospecting,
        simulation=req.simulation,
    )
    narrative_raw = result["narrative"]
    from app.api.schemas import CitationSchema, EvidencePacketSchema, SynthesisNarrative
    narrative = SynthesisNarrative(
        executiveSummary=narrative_raw["executiveSummary"],
        strategicAssessment=narrative_raw["strategicAssessment"],
        strongestSignals=narrative_raw["strongestSignals"],
        majorRisks=narrative_raw["majorRisks"],
        economicNarrative=narrative_raw["economicNarrative"],
        infrastructureNarrative=narrative_raw["infrastructureNarrative"],
        environmentalNarrative=narrative_raw["environmentalNarrative"],
        recommendations=narrative_raw["recommendations"],
        warnings=narrative_raw["warnings"],
        citations=[CitationSchema(**c) for c in narrative_raw["citations"]],
        generatedFromEvidenceIds=narrative_raw["generatedFromEvidenceIds"],
    )
    return SynthesisResponse(
        synthesisId=result["synthesisId"],
        mode=result["mode"],
        provider=result["provider"],
        model=result["model"],
        narrative=narrative,
        evidencePackets=[EvidencePacketSchema(**p) for p in result["evidencePackets"]],
        validationWarnings=result["validationWarnings"],
        generatedAt=result["generatedAt"],
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
