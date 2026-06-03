from __future__ import annotations

import json
import os

from pydantic import BaseModel, Field, field_validator


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


# ── History ──────────────────────────────────────────────────────────────────────

# ── Development Signals ────────────────────────────────────────────────────────────

class SignalsQueryRequest(BaseModel):
    regionName: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radiusKm: float = Field(default=100.0, gt=0, le=500)


class DevelopmentSignal(BaseModel):
    id: str
    title: str
    category: str
    summary: str
    sentiment: str
    source: str
    url: str | None = None
    publishedAt: str
    relevanceScore: float


class GroupedInsight(BaseModel):
    category: str
    categoryLabel: str
    signalCount: int
    sentiment: str
    keyTheme: str


class SignalsQueryResponse(BaseModel):
    queryId: str
    regionName: str
    provider: str
    signals: list[DevelopmentSignal]
    groupedInsights: list[GroupedInsight]
    agentSummary: str
    warnings: list[str]
    generatedAt: str


class SaveRunRequest(BaseModel):
    runType: str = Field(..., pattern="^(site|prospecting|simulation|synthesis|layout)$")
    label: str | None = Field(default=None, max_length=120)
    payload: dict[str, object]

    @field_validator("payload")
    @classmethod
    def _check_payload_size(cls, v: dict) -> dict:
        max_bytes = int(os.environ.get("CHITTA_MAX_HISTORY_PAYLOAD_BYTES", "1048576"))
        try:
            serialized = json.dumps(v, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"payload is not JSON-serializable: {exc}") from exc
        size = len(serialized)
        if size > max_bytes:
            raise ValueError(
                f"payload is {size // 1024} KB; exceeds the {max_bytes // 1024} KB limit"
            )
        return v


class SaveRunResponse(BaseModel):
    id: str
    runType: str
    label: str | None
    createdAt: str


class SavedRunSummary(BaseModel):
    id: str
    runType: str
    label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    regionName: str | None = None
    totalSuitabilityScore: float | None = None
    finalDecision: str | None = None
    formulaVersion: str | None = None
    createdAt: str
    tags: list[str]


class SavedRunDetail(SavedRunSummary):
    payload: dict[str, object]


class HistoryListResponse(BaseModel):
    runs: list[SavedRunSummary]
    total: int


class HistorySummarizeRequest(BaseModel):
    runId: str
    compareToId: str | None = None


class HistorySummaryResponse(BaseModel):
    summaryId: str
    runType: str
    currentRunId: str
    previousRunId: str | None
    deltas: dict[str, object]
    historicalNarrative: str
    evidence: list[dict[str, object]]
    warnings: list[str]
    generatedAt: str
