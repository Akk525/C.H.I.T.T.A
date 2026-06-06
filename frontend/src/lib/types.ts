export type LatLng = {
  latitude: number;
  longitude: number;
};

export type SiteAnalysisRequest = LatLng;

export type SiteAnalysisMetrics = {
  // Core
  windScore: number | null;
  terrainScore: number | null;
  confidenceScore: number;
  // Elevation / terrain
  elevationM: number | null;
  terrainComplexity: number | null;
  slopePct: number | null;
  ridgeScore: number | null;
  // Hub-height wind
  windSpeedAtHub: number | null;
  // Infrastructure (OSM)
  infrastructureScore: number | null;
  nearestRoadM: number | null;
  nearestPowerlineM: number | null;
  settlementCount15km: number | null;
  // Environmental
  environmentalScore: number | null;
  landCoverClass: string | null;
  landCoverScore: number | null;
  protectedAreaRisk: string | null;
  protectedAreaScore: number | null;
  inProtectedArea: boolean | null;
  // Population proxy
  populationScore: number | null;
  // Legacy field (mapped to infrastructureScore in v2)
  accessibilityScore: number;
};

export type MethodologyMetadata = {
  windDataSource: string;
  windDateRange: string;
  elevationSource: string;
  infrastructureSource?: string;
  scoringFormulaVersion: string;
  terrainRoughnessMethod: string;
  confidenceCalculationMethod: string;
  fallbackStatus: string;
  generatedAt: string;
};

export type ConsultantReport = {
  executiveSummary: string;
  siteStrengths: string[];
  risks: string[];
  recommendations: string[];
  confidenceNotes: string[];
  dataSources: string[];
};

// ── Development Risk types ────────────────────────────────────────────────────

export type RiskLevel = "low" | "medium" | "high" | "unknown";
export type KnowledgeClass =
  | "known_known"
  | "known_unknown"
  | "unknown_known"
  | "unknown_unknown";
export type DevelopmentOutlookVerdict =
  | "promising"
  | "fragile"
  | "high_risk"
  | "not_recommended";

export type RiskEvidenceItem = {
  label: string;
  value: string;
  source: string;
};

export type RiskItem = {
  category: string;
  level: RiskLevel;
  confidence: number;
  knowledgeClass: KnowledgeClass;
  summary: string;
  evidence: RiskEvidenceItem[];
  potentialFatalFlaw: boolean;
  recommendedNextStep: string;
};

export type FatalFlaw = {
  id: string;
  category: string;
  severity: "warning" | "critical";
  description: string;
  evidence: string;
  nextStep: string;
};

export type FitnessTestResult = {
  testName: string;
  passed: boolean;
  impactSummary: string;
  beforeMetrics: Record<string, unknown>;
  afterMetrics: Record<string, unknown>;
  failureReason: string | null;
};

export type FitnessResult = {
  tests: FitnessTestResult[];
  testsPassed: number;
  totalTests: number;
  fitnessScore: number;
  riskBand: "low" | "medium" | "high" | "very_high";
  mostVulnerableAssumptions: string[];
  interpretation: string;
};

export type DevelopmentOutlook = {
  developmentOutlook: DevelopmentOutlookVerdict;
  riskRegister: {
    categories: RiskItem[];
    fatalFlaws: FatalFlaw[];
    fatalFlawCount: number;
    criticalFatalFlawCount: number;
  };
  fatalFlaws: FatalFlaw[];
  fitnessTest: FitnessResult;
  narrativeSummary: string;
  nextInvestigationPriorities: string[];
};

export type SiteAnalysisResponse = {
  analysisId: string;
  methodology: MethodologyMetadata;
  auditTrail: string[];
  inputs: LatLng;
  metrics: SiteAnalysisMetrics;
  totalSuitabilityScore: number | null;
  report: ConsultantReport;
  agentAnalysis?: AgentAnalysis | null;
  economicMetrics?: EconomicMetrics | null;
  developmentOutlook?: DevelopmentOutlook | null;
  debug?: Record<string, unknown>;
};



export type HeatmapCellMetrics = {
  windScore: number | null;
  terrainScore: number | null;
  accessibilityScore: number;
  confidenceScore: number;
  totalSuitability: number | null;
};

export type HeatmapProviderStatus = {
  wind: "REAL" | "MOCK" | "UNAVAILABLE";
  elevation: "REAL" | "MOCK" | "UNAVAILABLE";
};

export type HeatmapCell = LatLng & {
  metrics: HeatmapCellMetrics;
  label: string;
  providerStatus: HeatmapProviderStatus;
  dataUnavailable?: boolean;
};

export type SiteHeatmapRequest = LatLng & {
  radiusKm?: number;
  gridSize?: number;
};

export type SiteHeatmapResponse = {
  analysisId: string;
  methodology: MethodologyMetadata;
  auditTrail: string[];
  center: LatLng;
  radiusKm: number;
  gridSize: number;
  cells: HeatmapCell[];
  bestCells: HeatmapCell[];
};


// ── Economic feasibility ───────────────────────────────────────────────────

export type EconomicAssumptions = {
  turbineRatingMw: number;
  turbineCount: number;
  electricityPriceUsdPerMwh: number;
  capexUsdPerMw: number;
  opexPctOfCapex: number;
  projectLifeYears: number;
  discountRate: number;
};

export type EconomicMetrics = {
  capacityFactor: number;
  annualEnergyMwh: number;
  capexUsd: number;
  opexUsdPerYear: number;
  annualRevenueUsd: number;
  paybackYears: number | null;
  lcoeUsdPerMwh: number;
  economicScore: number;
  windAvailable: boolean;
  assumptions: EconomicAssumptions;
  limitations: string[];
};

export type AgentEvidence = {
  label: string;
  value: string;
  source: string;
};

export type AgentOutput = {
  agentName: string;
  status: "complete" | "partial" | "fallback";
  confidence: number;
  summary: string;
  findings: string[];
  risks: string[];
  recommendations: string[];
  evidence: AgentEvidence[];
};

export type CoordinatorOutput = {
  finalDecision: "promising" | "mixed" | "caution" | "poor";
  topStrengths: string[];
  topRisks: string[];
  nextSteps: string[];
  confidenceSummary: string;
  contradictionNotes: string[];
};

export type AgentAnalysis = {
  agents: AgentOutput[];
  coordinator: CoordinatorOutput;
};

export type SiteReportExportRequest = {
  analysis: SiteAnalysisResponse;
  heatmap?: SiteHeatmapResponse | null;
};

// ── Prospecting ────────────────────────────────────────────────────────────

export type ProspectingRequest = {
  regionName?: string;
  centerLatitude: number;
  centerLongitude: number;
  radiusKm?: number;
  gridSize?: number;
  maxCandidates?: number;
};

export type ProspectingCandidate = {
  id: string;
  latitude: number;
  longitude: number;
  totalSuitability: number | null;
  finalDecision: "promising" | "mixed" | "caution" | "poor" | null;
  windScore: number | null;
  terrainScore: number | null;
  infrastructureScore: number | null;
  environmentalScore: number | null;
  populationScore: number | null;
  confidenceScore: number;
  topStrengths: string[];
  topRisks: string[];
  isFullyEnriched: boolean;
  providerStatus: Record<string, string>;
  // Economic fields (populated for fully-enriched candidates)
  economicScore?: number | null;
  lcoeUsdPerMwh?: number | null;
  annualEnergyMwh?: number | null;
  paybackYears?: number | null;
  capacityFactor?: number | null;
  error?: string | null;
};

export type ProspectingCluster = {
  id: string;
  label: string;
  centroidLatitude: number;
  centroidLongitude: number;
  averageSuitability: number;
  candidateCount: number;
  topDecision: string;
  summary: string;
};

export type ProspectingResponse = {
  prospectingId: string;
  region: {
    name: string;
    centerLatitude: number;
    centerLongitude: number;
    radiusKm: number;
    gridSize: number;
  };
  generatedAt: string;
  candidateCount: number;
  enrichedCount: number;
  candidates: ProspectingCandidate[];
  clusters: ProspectingCluster[];
  topCandidates: ProspectingCandidate[];
  methodology: Record<string, string>;
  auditTrail: string[];
};

// ── Simulation ─────────────────────────────────────────────────────────────────

export type SimulationConfig = {
  turbineCount: number;
  turbineRatingMw: number;
  electricityPriceUsdPerMwh: number;
  capexUsdPerMw: number;
  opexPercentOfCapex: number;
  projectLifeYears: number;
  windWeight: number;
  terrainWeight: number;
  infrastructureWeight: number;
  environmentalWeight: number;
  populationWeight: number;
  confidenceWeight: number;
  economicWeight: number;
  environmentalStrictness: "low" | "medium" | "high";
  infrastructurePreference: "remote" | "balanced" | "grid-connected";
};

export const DEFAULT_SIMULATION_CONFIG: SimulationConfig = {
  turbineCount: 10,
  turbineRatingMw: 3.0,
  electricityPriceUsdPerMwh: 55.0,
  capexUsdPerMw: 1_300_000,
  opexPercentOfCapex: 0.03,
  projectLifeYears: 20,
  windWeight: 35,
  terrainWeight: 20,
  infrastructureWeight: 15,
  environmentalWeight: 10,
  populationWeight: 10,
  confidenceWeight: 5,
  economicWeight: 5,
  environmentalStrictness: "medium",
  infrastructurePreference: "balanced",
};

export type SimulatedCandidate = {
  id: string;
  latitude: number;
  longitude: number;
  originalTotalSuitability: number | null;
  newTotalSuitability: number | null;
  suitabilityDelta: number | null;
  originalDecision: string | null;
  newDecision: string | null;
  newEconomicScore: number | null;
  newLcoeUsdPerMwh: number | null;
  newAnnualEnergyMwh: number | null;
  newPaybackYears: number | null;
  newCapacityFactor: number | null;
  topStrengths: string[];
  topRisks: string[];
};

export type CandidateRankingChange = {
  id: string;
  latitude: number;
  longitude: number;
  originalRank: number;
  newRank: number;
  rankChange: number;
  direction: "up" | "down" | "unchanged";
};

export type SimulationRequest = {
  candidates: ProspectingCandidate[];
  config: SimulationConfig;
};

export type SimulationResponse = {
  simulationId: string;
  config: SimulationConfig;
  recomputedCandidates: SimulatedCandidate[];
  rankingChanges: CandidateRankingChange[];
  strongestCandidate: SimulatedCandidate | null;
  weakestCandidate: SimulatedCandidate | null;
  mostImprovedCandidate: SimulatedCandidate | null;
  mostSensitiveCandidate: SimulatedCandidate | null;
  methodology: Record<string, string>;
  auditTrail: string[];
};

// ── AI Synthesis ───────────────────────────────────────────────────────────────

export type SynthesisMode = "site" | "prospecting" | "simulation";

export type SynthesisRequest = {
  mode: SynthesisMode;
  siteAnalysis?: SiteAnalysisResponse | null;
  prospecting?: ProspectingResponse | null;
  simulation?: SimulationResponse | null;
};

export type SynthesisCitation = {
  claim: string;
  evidenceIds: string[];
};

export type SynthesisNarrative = {
  executiveSummary: string;
  strategicAssessment: string;
  strongestSignals: string[];
  majorRisks: string[];
  economicNarrative: string;
  infrastructureNarrative: string;
  environmentalNarrative: string;
  recommendations: string[];
  warnings: string[];
  citations: SynthesisCitation[];
  generatedFromEvidenceIds: string[];
};

export type EvidencePacket = {
  evidenceId: string;
  category: string;
  label: string;
  value: string;
  unit: string | null;
  source: string;
  quality: string;
};

export type SynthesisResponse = {
  synthesisId: string;
  mode: SynthesisMode;
  provider: string;
  model: string;
  narrative: SynthesisNarrative;
  evidencePackets: EvidencePacket[];
  validationWarnings: string[];
  generatedAt: string;
};

// ── Development Signals ───────────────────────────────────────────────────────

export type SignalsQueryRequest = {
  regionName: string;
  latitude: number;
  longitude: number;
  radiusKm?: number;
};

export type DevelopmentSignal = {
  id: string;
  title: string;
  category: string;
  summary: string;
  sentiment: "positive" | "negative" | "mixed" | "neutral";
  source: string;
  url: string | null;
  publishedAt: string;
  relevanceScore: number;
};

export type GroupedInsight = {
  category: string;
  categoryLabel: string;
  signalCount: number;
  sentiment: string;
  keyTheme: string;
};

export type SignalsQueryResponse = {
  queryId: string;
  regionName: string;
  provider: string;
  signals: DevelopmentSignal[];
  groupedInsights: GroupedInsight[];
  agentSummary: string;
  warnings: string[];
  generatedAt: string;
};

// ── History ────────────────────────────────────────────────────────────────────

export type SaveRunRequest = {
  runType: "site" | "prospecting" | "simulation" | "synthesis" | "layout";
  label?: string | null;
  payload: Record<string, unknown>;
};

export type SaveRunResponse = {
  id: string;
  runType: string;
  label: string | null;
  createdAt: string;
};

export type SavedRunSummary = {
  id: string;
  runType: string;
  label: string | null;
  latitude: number | null;
  longitude: number | null;
  regionName: string | null;
  totalSuitabilityScore: number | null;
  finalDecision: string | null;
  formulaVersion: string | null;
  createdAt: string;
  tags: string[];
};

export type SavedRunDetail = SavedRunSummary & {
  payload: Record<string, unknown>;
};

export type HistoryListResponse = {
  runs: SavedRunSummary[];
  total: number;
};

export type HistorySummarizeRequest = {
  runId: string;
  compareToId?: string | null;
};

export type HistorySummaryResponse = {
  summaryId: string;
  runType: string;
  currentRunId: string;
  previousRunId: string | null;
  deltas: Record<string, unknown>;
  historicalNarrative: string;
  evidence: Record<string, unknown>[];
  warnings: string[];
  generatedAt: string;
};

export type ProspectingReportExportRequest = {
  prospecting: ProspectingResponse;
  simulation?: SimulationResponse | null;
  synthesis?: SynthesisResponse | null;
};

// ── Layout Analysis ────────────────────────────────────────────────────────────

export type LayoutAnalysisRequest = {
  latitude: number;
  longitude: number;
  turbineCount?: number;
  turbineRatingMw?: number;
  rotorDiameterM?: number;
  prevailingWindDirectionDeg?: number | null;
};

export type TurbinePosition = {
  id: string;
  latitude: number;
  longitude: number;
};

export type LayoutAnalysisResponse = {
  layoutId: string;
  turbines: TurbinePosition[];
  spacingViolations: number;
  estimatedWakeLossPercent: number;
  layoutEfficiencyScore: number;
  assumptions: Record<string, string>;
  warnings: string[];
  methodology: Record<string, string>;
  auditTrail: string[];
  generatedAt: string;
};
