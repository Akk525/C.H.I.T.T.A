from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
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
    DevelopmentOutlookSchema,
    EconomicAssumptionsSchema,
    EconomicMetricsSchema,
    FatalFlawSchema,
    FitnessResultSchema,
    FitnessTestResultSchema,
    ProspectingCandidateSchema,
    ProspectingClusterSchema,
    ProspectingRequest,
    ProspectingResponse,
    RiskEvidenceItemSchema,
    RiskItemSchema,
    RiskRegisterSchema,
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
    DevelopmentSignal,
    GroupedInsight,
    HistoryListResponse,
    HistorySummarizeRequest,
    HistorySummaryResponse,
    SignalsQueryRequest,
    SignalsQueryResponse,
    ProspectingReportExportRequest,
    SavedRunDetail,
    SavedRunSummary,
    SaveRunRequest,
    SaveRunResponse,
    SynthesisRequest,
    SynthesisResponse,
    TurbinePositionSchema,
)
from app.security import require_api_key
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
from app.services.risk import RiskRegisterResult, DevelopmentOutlookResult, compute_risk_register, compose_development_outlook
from app.services.fitness import FitnessResult, run_fitness_test
from app.services.methodology import (
    build_methodology,
    build_site_audit_trail,
    generate_analysis_id,
    utc_now_iso,
)
from app.db.deps import get_db
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


def _outlook_to_schema(
    risk_reg: RiskRegisterResult,
    fitness: FitnessResult,
    outlook: DevelopmentOutlookResult,
) -> DevelopmentOutlookSchema:
    risk_categories = [
        RiskItemSchema(
            category=r.category,
            level=r.level,
            confidence=r.confidence,
            knowledgeClass=r.knowledgeClass,
            summary=r.summary,
            evidence=[RiskEvidenceItemSchema(label=e.label, value=e.value, source=e.source) for e in r.evidence],
            potentialFatalFlaw=r.potentialFatalFlaw,
            recommendedNextStep=r.recommendedNextStep,
        )
        for r in risk_reg.categories
    ]
    fatal_flaws = [
        FatalFlawSchema(id=f.id, category=f.category, severity=f.severity,
                        description=f.description, evidence=f.evidence, nextStep=f.nextStep)
        for f in risk_reg.fatalFlaws
    ]
    fitness_tests = [
        FitnessTestResultSchema(
            testName=t.testName,
            passed=t.passed,
            impactSummary=t.impactSummary,
            beforeMetrics=t.beforeMetrics,
            afterMetrics=t.afterMetrics,
            failureReason=t.failureReason,
        )
        for t in fitness.tests
    ]
    return DevelopmentOutlookSchema(
        developmentOutlook=outlook.developmentOutlook,
        riskRegister=RiskRegisterSchema(
            categories=risk_categories,
            fatalFlaws=fatal_flaws,
            fatalFlawCount=risk_reg.fatalFlawCount,
            criticalFatalFlawCount=risk_reg.criticalFatalFlawCount,
        ),
        fatalFlaws=fatal_flaws,
        fitnessTest=FitnessResultSchema(
            tests=fitness_tests,
            testsPassed=fitness.testsPassed,
            totalTests=fitness.totalTests,
            fitnessScore=fitness.fitnessScore,
            riskBand=fitness.riskBand,
            mostVulnerableAssumptions=fitness.mostVulnerableAssumptions,
            interpretation=fitness.interpretation,
        ),
        narrativeSummary=outlook.narrativeSummary,
        nextInvestigationPriorities=outlook.nextInvestigationPriorities,
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


@router.post("/api/site-analysis", response_model=SiteAnalysisResponse, dependencies=[Depends(require_api_key)])
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

    risk_reg = compute_risk_register(
        wind_score=wind_score,
        wind_speed_at_hub=wind_speed_at_hub,
        confidence_score=confidence_score,
        terrain_score=terrain_score,
        terrain_complexity=terrain_complexity,
        slope_pct=slope_pct,
        infra_score=infra_s,
        nearest_road_m=nearest_road,
        nearest_powerline_m=nearest_power,
        settlement_count_15km=settlement_count,
        env_score=env_s,
        land_cover_class=lc_class,
        protected_area_risk=pa_risk,
        in_protected_area=in_pa,
        eco=eco,
    )
    fitness_result = run_fitness_test(
        wind_speed_at_hub=wind_speed_at_hub,
        terrain_score=terrain_score,
        infra_score=infra_s,
        eco=eco,
        confidence_score=confidence_score,
    )
    outlook_result = compose_development_outlook(risk_reg, fitness_result, total)

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
        developmentOutlook=_outlook_to_schema(risk_reg, fitness_result, outlook_result),
        debug={**sources_debug},
    )


@router.post("/api/site-heatmap", response_model=SiteHeatmapResponse, dependencies=[Depends(require_api_key)])
async def site_heatmap(req: SiteHeatmapRequest) -> SiteHeatmapResponse:
    center = LatLng(latitude=req.latitude, longitude=req.longitude)
    result = await build_heatmap(
        center,
        radius_km=req.radiusKm,
        grid_size=req.gridSize,
    )
    return SiteHeatmapResponse(**result)  # type: ignore[arg-type]


@router.post("/api/site-report/export", dependencies=[Depends(require_api_key)])
async def export_site_report(req: SiteReportExportRequest) -> Response:
    pdf_bytes = generate_site_report_pdf(req.analysis, req.heatmap)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="chitta-site-assessment.pdf"'
        },
    )


@router.post("/api/prospecting-report/export", dependencies=[Depends(require_api_key)])
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


@router.post("/api/simulation/run", response_model=SimulationResponse, dependencies=[Depends(require_api_key)])
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


@router.post("/api/layout/analyze", response_model=LayoutAnalysisResponse, dependencies=[Depends(require_api_key)])
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


@router.post("/api/ai/synthesize", response_model=SynthesisResponse, dependencies=[Depends(require_api_key)])
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


@router.post("/api/prospecting/run", response_model=ProspectingResponse, dependencies=[Depends(require_api_key)])
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


# ── Signals route ─────────────────────────────────────────────────────────────

@router.get("/api/health/providers")
async def health_providers() -> dict:
    """Check connectivity to all external providers and infrastructure."""
    import os
    from datetime import datetime, timezone
    results: dict[str, str] = {}

    # Database
    try:
        if os.environ.get("PERSIST_ANALYSES", "false").lower() in {"1", "true", "yes", "on"}:
            from sqlalchemy import text as sa_text
            from app.db.session import SessionLocal
            db = SessionLocal()
            db.execute(sa_text("SELECT 1"))
            db.close()
            results["database"] = "ok"
        else:
            results["database"] = "disabled"
    except Exception as exc:
        results["database"] = f"unavailable ({exc!s})"

    # NASA POWER
    import httpx
    _to = 6.0
    for key, url in [
        ("nasaPower", "https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=WS10M&community=RE&longitude=0&latitude=0&format=JSON"),
        ("openTopoData", "https://api.opentopodata.org/v1/srtm90m?locations=0,0"),
        ("osmOverpass", "https://overpass-api.de/api/status"),
    ]:
        try:
            async with httpx.AsyncClient(timeout=_to) as client:
                r = await client.get(url)
            results[key] = "ok" if r.status_code < 500 else f"error ({r.status_code})"
        except Exception:
            results[key] = "unavailable"

    # GDELT / signals
    gdelt_prov = os.environ.get("CHITTA_SIGNALS_PROVIDER", "mock").lower()
    if gdelt_prov == "mock":
        results["gdelt"] = "ok (mock)"
    else:
        try:
            gdelt_url = (
                "https://api.gdeltproject.org/api/v2/doc/doc"
                "?query=test&mode=artlist&maxrecords=1&format=json&timespan=1d"
            )
            async with httpx.AsyncClient(timeout=_to) as client:
                r = await client.get(gdelt_url)
            if r.status_code == 429:
                results["gdelt"] = "rate_limited"
            elif r.status_code < 400:
                results["gdelt"] = "ok"
            else:
                results["gdelt"] = f"error ({r.status_code})"
        except Exception:
            results["gdelt"] = "unavailable"

    # LLM provider
    llm_prov = os.environ.get("CHITTA_LLM_PROVIDER", "mock").lower()
    results["llmProvider"] = f"ok ({llm_prov})"

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "providers": results,
    }


@router.post("/api/signals/query", response_model=SignalsQueryResponse, dependencies=[Depends(require_api_key)])
async def query_signals(req: SignalsQueryRequest) -> SignalsQueryResponse:
    from app.signals.signals_service import run_signals_query
    result = await run_signals_query(
        region_name=req.regionName,
        latitude=req.latitude,
        longitude=req.longitude,
        radius_km=req.radiusKm,
    )
    return SignalsQueryResponse(
        queryId=result["queryId"],
        regionName=result["regionName"],
        provider=result["provider"],
        signals=[DevelopmentSignal(**s) for s in result["signals"]],
        groupedInsights=[GroupedInsight(**g) for g in result["groupedInsights"]],
        agentSummary=result["agentSummary"],
        warnings=result["warnings"],
        generatedAt=result["generatedAt"],
    )


# ── History routes ─────────────────────────────────────────────────────────────

def _extract_meta(run_type: str, payload: dict) -> dict:
    """Denormalize key scalar fields from payload for efficient querying."""
    if run_type == "site":
        inputs = payload.get("inputs") or {}
        ag = (payload.get("agentAnalysis") or {}).get("coordinator") or {}
        meth = payload.get("methodology") or {}
        return {
            "latitude": inputs.get("latitude"),
            "longitude": inputs.get("longitude"),
            "total_suitability_score": payload.get("totalSuitabilityScore"),
            "final_decision": ag.get("finalDecision"),
            "formula_version": meth.get("scoringFormulaVersion"),
        }
    if run_type == "prospecting":
        region = payload.get("region") or {}
        return {
            "region_name": region.get("name"),
            "latitude": region.get("centerLatitude"),
            "longitude": region.get("centerLongitude"),
        }
    return {}


def _row_to_summary(row: "object") -> SavedRunSummary:
    from app.models.saved_run import SavedRun as _SR
    r: _SR = row  # type: ignore[assignment]
    return SavedRunSummary(
        id=str(r.id),
        runType=r.run_type,
        label=r.label,
        latitude=r.latitude,
        longitude=r.longitude,
        regionName=r.region_name,
        totalSuitabilityScore=r.total_suitability_score,
        finalDecision=r.final_decision,
        formulaVersion=r.formula_version,
        createdAt=r.created_at.isoformat(),
        tags=list(r.tags or []),
    )


@router.post("/api/history/save", response_model=SaveRunResponse, dependencies=[Depends(require_api_key)])
async def save_run(req: SaveRunRequest, db=Depends(get_db)) -> SaveRunResponse:
    from app.models.saved_run import SavedRun

    meta = _extract_meta(req.runType, dict(req.payload))
    row = SavedRun(
        run_type=req.runType,
        label=req.label,
        payload=dict(req.payload),
        **{k: v for k, v in meta.items() if v is not None},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return SaveRunResponse(
        id=str(row.id),
        runType=row.run_type,
        label=row.label,
        createdAt=row.created_at.isoformat(),
    )


@router.get("/api/history/runs", response_model=HistoryListResponse, dependencies=[Depends(require_api_key)])
async def list_runs(
    runType: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
) -> HistoryListResponse:
    from sqlalchemy import select, func as sa_func
    from app.models.saved_run import SavedRun

    q = select(SavedRun)
    if runType:
        q = q.where(SavedRun.run_type == runType)
    q = q.order_by(SavedRun.created_at.desc())

    total = db.scalar(select(sa_func.count()).select_from(q.subquery()))
    rows = db.scalars(q.offset(offset).limit(limit)).all()

    return HistoryListResponse(
        runs=[_row_to_summary(r) for r in rows],
        total=total or 0,
    )


@router.get("/api/history/run/{run_id}", response_model=SavedRunDetail, dependencies=[Depends(require_api_key)])
async def get_run(run_id: str, db=Depends(get_db)) -> SavedRunDetail:
    import uuid as _uuid
    from app.models.saved_run import SavedRun

    try:
        uid = _uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    row = db.get(SavedRun, uid)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    summary = _row_to_summary(row)
    return SavedRunDetail(**summary.model_dump(), payload=dict(row.payload))


async def _run_history_graph(
    current_row: "object",
    previous_row: "object | None",
) -> HistorySummaryResponse:
    from app.langgraph.graph import history_graph
    from app.models.saved_run import SavedRun as _SR

    def _meta(r: _SR) -> dict:
        return {
            "id": str(r.id),
            "run_type": r.run_type,
            "label": r.label,
            "created_at": r.created_at.isoformat(),
            "total_suitability_score": r.total_suitability_score,
            "final_decision": r.final_decision,
        }

    cur: _SR = current_row  # type: ignore[assignment]
    initial_state = {
        "current_run": dict(cur.payload),
        "current_run_meta": _meta(cur),
        "previous_run": dict(previous_row.payload) if previous_row else None,  # type: ignore[union-attr]
        "previous_run_meta": _meta(previous_row) if previous_row else None,  # type: ignore[arg-type]
        "run_type": cur.run_type,
        "deltas": {},
        "historical_narrative": "",
        "evidence": [],
        "warnings": [],
        "summary_id": "",
        "generated_at": "",
    }

    result = await history_graph.ainvoke(initial_state)

    return HistorySummaryResponse(
        summaryId=result["summary_id"],
        runType=result["run_type"],
        currentRunId=str(cur.id),
        previousRunId=str(previous_row.id) if previous_row else None,  # type: ignore[union-attr]
        deltas=result["deltas"],
        historicalNarrative=result["historical_narrative"],
        evidence=result["evidence"],
        warnings=result["warnings"],
        generatedAt=result["generated_at"],
    )


@router.get("/api/history/compare/{id_a}/{id_b}", response_model=HistorySummaryResponse, dependencies=[Depends(require_api_key)])
async def compare_runs(id_a: str, id_b: str, db=Depends(get_db)) -> HistorySummaryResponse:
    import uuid as _uuid
    from app.models.saved_run import SavedRun

    try:
        uid_a, uid_b = _uuid.UUID(id_a), _uuid.UUID(id_b)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    row_a = db.get(SavedRun, uid_a)
    row_b = db.get(SavedRun, uid_b)

    if not row_a or not row_b:
        raise HTTPException(status_code=404, detail="One or both runs not found")
    if row_a.run_type != row_b.run_type:
        raise HTTPException(status_code=422, detail="Runs must be of the same type to compare")

    return await _run_history_graph(row_a, row_b)


@router.post("/api/history/summarize", response_model=HistorySummaryResponse, dependencies=[Depends(require_api_key)])
async def summarize_run(req: HistorySummarizeRequest, db=Depends(get_db)) -> HistorySummaryResponse:
    import uuid as _uuid
    from app.models.saved_run import SavedRun

    try:
        uid = _uuid.UUID(req.runId)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    row = db.get(SavedRun, uid)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    prev_row = None
    if req.compareToId:
        try:
            prev_uid = _uuid.UUID(req.compareToId)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid compareToId format")
        prev_row = db.get(SavedRun, prev_uid)
        if not prev_row:
            raise HTTPException(status_code=404, detail="Comparison run not found")

    return await _run_history_graph(row, prev_row)
