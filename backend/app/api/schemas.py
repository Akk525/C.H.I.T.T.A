from __future__ import annotations

from pydantic import BaseModel, Field


class SiteAnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class SiteAnalysisMetrics(BaseModel):
    # Core
    windScore: float | None = None
    terrainScore: float | None = None
    confidenceScore: float
    # Elevation / terrain detail
    elevationM: float | None = None
    terrainComplexity: float | None = None
    slopePct: float | None = None
    ridgeScore: float | None = None
    # Wind hub-height
    windSpeedAtHub: float | None = None       # mean speed at highest available height (50m or 10m)
    # Infrastructure (OSM)
    infrastructureScore: float | None = None
    nearestRoadM: float | None = None
    nearestPowerlineM: float | None = None
    settlementCount15km: int | None = None
    # Environmental
    environmentalScore: float | None = None
    landCoverClass: str | None = None         # "forest"|"cropland"|"barren"|"urban"|...
    landCoverScore: float | None = None
    protectedAreaRisk: str | None = None      # "low"|"medium"|"high"
    protectedAreaScore: float | None = None
    inProtectedArea: bool | None = None
    # Population proxy
    populationScore: float | None = None
    # Legacy field kept for backward compat with heatmap / frontend
    accessibilityScore: float = 50.0


class MethodologyMetadata(BaseModel):
    windDataSource: str
    windDateRange: str
    elevationSource: str
    infrastructureSource: str = "Unavailable"
    scoringFormulaVersion: str
    terrainRoughnessMethod: str
    confidenceCalculationMethod: str
    fallbackStatus: str
    generatedAt: str


class ConsultantReport(BaseModel):
    executiveSummary: str
    siteStrengths: list[str]
    risks: list[str]
    recommendations: list[str]
    confidenceNotes: list[str]
    dataSources: list[str]


class EconomicAssumptionsSchema(BaseModel):
    turbineRatingMw: float
    turbineCount: int
    electricityPriceUsdPerMwh: float
    capexUsdPerMw: float
    opexPctOfCapex: float
    projectLifeYears: int
    discountRate: float


class EconomicMetricsSchema(BaseModel):
    capacityFactor: float
    annualEnergyMwh: float
    capexUsd: float
    opexUsdPerYear: float
    annualRevenueUsd: float
    paybackYears: float | None = None
    lcoeUsdPerMwh: float
    economicScore: float
    windAvailable: bool
    assumptions: EconomicAssumptionsSchema
    limitations: list[str]


class AgentEvidence(BaseModel):
    label: str
    value: str
    source: str


class AgentOutput(BaseModel):
    agentName: str
    status: str  # "complete" | "partial" | "fallback"
    confidence: float
    summary: str
    findings: list[str]
    risks: list[str]
    recommendations: list[str]
    evidence: list[AgentEvidence]


class CoordinatorOutput(BaseModel):
    finalDecision: str  # "promising" | "mixed" | "caution" | "poor"
    topStrengths: list[str]
    topRisks: list[str]
    nextSteps: list[str]
    confidenceSummary: str
    contradictionNotes: list[str]


class AgentAnalysis(BaseModel):
    agents: list[AgentOutput]
    coordinator: CoordinatorOutput


class SiteAnalysisResponse(BaseModel):
    analysisId: str
    methodology: MethodologyMetadata
    auditTrail: list[str]
    inputs: SiteAnalysisRequest
    metrics: SiteAnalysisMetrics
    totalSuitabilityScore: float | None = None
    report: ConsultantReport
    agentAnalysis: AgentAnalysis | None = None
    economicMetrics: EconomicMetricsSchema | None = None
    debug: dict[str, object] | None = None


class SiteHeatmapRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radiusKm: float = Field(default=10.0, gt=0, le=50)
    gridSize: int = Field(default=5, ge=1, le=9)


class ProspectingRequest(BaseModel):
    regionName: str = "Custom Region"
    centerLatitude: float = Field(..., ge=-90, le=90)
    centerLongitude: float = Field(..., ge=-180, le=180)
    radiusKm: float = Field(default=75.0, gt=0, le=200)
    gridSize: int = Field(default=5, ge=2, le=10)
    maxCandidates: int = Field(default=25, ge=4, le=50)


class ProspectingCandidateSchema(BaseModel):
    id: str
    latitude: float
    longitude: float
    totalSuitability: float | None = None
    finalDecision: str | None = None
    windScore: float | None = None
    terrainScore: float | None = None
    infrastructureScore: float | None = None
    environmentalScore: float | None = None
    populationScore: float | None = None
    confidenceScore: float
    topStrengths: list[str]
    topRisks: list[str]
    isFullyEnriched: bool
    providerStatus: dict[str, str]
    # Economic fields (populated for fully-enriched candidates)
    economicScore: float | None = None
    lcoeUsdPerMwh: float | None = None
    annualEnergyMwh: float | None = None
    paybackYears: float | None = None
    capacityFactor: float | None = None
    error: str | None = None


class ProspectingClusterSchema(BaseModel):
    id: str
    label: str
    centroidLatitude: float
    centroidLongitude: float
    averageSuitability: float
    candidateCount: int
    topDecision: str
    summary: str


class ProspectingResponse(BaseModel):
    prospectingId: str
    region: dict[str, object]
    generatedAt: str
    candidateCount: int
    enrichedCount: int
    candidates: list[ProspectingCandidateSchema]
    clusters: list[ProspectingClusterSchema]
    topCandidates: list[ProspectingCandidateSchema]
    methodology: dict[str, str]
    auditTrail: list[str]


class HeatmapCellMetrics(BaseModel):
    windScore: float | None = None
    terrainScore: float | None = None
    accessibilityScore: float
    confidenceScore: float
    totalSuitability: float | None = None


class HeatmapProviderStatus(BaseModel):
    wind: str
    elevation: str


class HeatmapCell(BaseModel):
    latitude: float
    longitude: float
    metrics: HeatmapCellMetrics
    label: str
    providerStatus: HeatmapProviderStatus
    dataUnavailable: bool = False


class SiteHeatmapResponse(BaseModel):
    analysisId: str
    methodology: MethodologyMetadata
    auditTrail: list[str]
    center: SiteAnalysisRequest
    radiusKm: float
    gridSize: int
    cells: list[HeatmapCell]
    bestCells: list[HeatmapCell]



class SiteReportExportRequest(BaseModel):
    analysis: SiteAnalysisResponse
    heatmap: SiteHeatmapResponse | None = None


# ── Simulation ─────────────────────────────────────────────────────────────────

class SimulationConfigSchema(BaseModel):
    turbineCount: int = 10
    turbineRatingMw: float = 3.0
    electricityPriceUsdPerMwh: float = 55.0
    capexUsdPerMw: float = 1_300_000.0
    opexPercentOfCapex: float = 0.03
    projectLifeYears: int = 20
    windWeight: float = 35.0
    terrainWeight: float = 20.0
    infrastructureWeight: float = 15.0
    environmentalWeight: float = 10.0
    populationWeight: float = 10.0
    confidenceWeight: float = 5.0
    economicWeight: float = 5.0
    environmentalStrictness: str = "medium"
    infrastructurePreference: str = "balanced"


class SimulatedCandidateSchema(BaseModel):
    id: str
    latitude: float
    longitude: float
    originalTotalSuitability: float | None = None
    newTotalSuitability: float | None = None
    suitabilityDelta: float | None = None
    originalDecision: str | None = None
    newDecision: str | None = None
    newEconomicScore: float | None = None
    newLcoeUsdPerMwh: float | None = None
    newAnnualEnergyMwh: float | None = None
    newPaybackYears: float | None = None
    newCapacityFactor: float | None = None
    topStrengths: list[str] = Field(default_factory=list)
    topRisks: list[str] = Field(default_factory=list)


class CandidateRankingChange(BaseModel):
    id: str
    latitude: float
    longitude: float
    originalRank: int
    newRank: int
    rankChange: int   # positive = moved up
    direction: str    # "up" | "down" | "unchanged"


class SimulationRequest(BaseModel):
    candidates: list[ProspectingCandidateSchema]
    config: SimulationConfigSchema


class SimulationResponse(BaseModel):
    simulationId: str
    config: SimulationConfigSchema
    recomputedCandidates: list[SimulatedCandidateSchema]
    rankingChanges: list[CandidateRankingChange]
    strongestCandidate: SimulatedCandidateSchema | None = None
    weakestCandidate: SimulatedCandidateSchema | None = None
    mostImprovedCandidate: SimulatedCandidateSchema | None = None
    mostSensitiveCandidate: SimulatedCandidateSchema | None = None
    methodology: dict[str, str]
    auditTrail: list[str]


# ── AI Synthesis ────────────────────────────────────────────────────────────────

class SynthesisRequest(BaseModel):
    mode: str = Field(..., pattern="^(site|prospecting|simulation)$")
    siteAnalysis: SiteAnalysisResponse | None = None
    prospecting: ProspectingResponse | None = None
    simulation: SimulationResponse | None = None


class CitationSchema(BaseModel):
    claim: str
    evidenceIds: list[str]


class SynthesisNarrative(BaseModel):
    executiveSummary: str
    strategicAssessment: str
    strongestSignals: list[str]
    majorRisks: list[str]
    economicNarrative: str
    infrastructureNarrative: str
    environmentalNarrative: str
    recommendations: list[str]
    warnings: list[str]
    citations: list[CitationSchema]
    generatedFromEvidenceIds: list[str]


class EvidencePacketSchema(BaseModel):
    evidenceId: str
    category: str
    label: str
    value: str
    unit: str | None = None
    source: str
    quality: str


class SynthesisResponse(BaseModel):
    synthesisId: str
    mode: str
    provider: str
    model: str
    narrative: SynthesisNarrative
    evidencePackets: list[EvidencePacketSchema]
    validationWarnings: list[str]
    generatedAt: str


class ProspectingReportExportRequest(BaseModel):
    prospecting: ProspectingResponse
    simulation: SimulationResponse | None = None
    synthesis: SynthesisResponse | None = None


# ── Layout Analysis ─────────────────────────────────────────────────────────────

class LayoutAnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    turbineCount: int = Field(default=10, ge=1, le=50)
    turbineRatingMw: float = Field(default=3.0, gt=0)
    rotorDiameterM: float = Field(default=120.0, gt=0)
    prevailingWindDirectionDeg: float | None = Field(default=None, ge=0, lt=360)


class TurbinePositionSchema(BaseModel):
    id: str
    latitude: float
    longitude: float


class LayoutAnalysisResponse(BaseModel):
    layoutId: str
    turbines: list[TurbinePositionSchema]
    spacingViolations: int
    estimatedWakeLossPercent: float
    layoutEfficiencyScore: float
    assumptions: dict[str, str]
    warnings: list[str]
    methodology: dict[str, str]
    auditTrail: list[str]
    generatedAt: str
