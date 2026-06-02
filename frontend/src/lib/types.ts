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
