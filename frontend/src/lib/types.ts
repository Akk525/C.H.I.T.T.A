export type LatLng = {
  latitude: number;
  longitude: number;
};

export type SiteAnalysisRequest = LatLng;

export type SiteAnalysisMetrics = {
  windScore: number | null;
  terrainScore: number | null;
  accessibilityScore: number;
  confidenceScore: number;
  elevationM: number | null;
  terrainComplexity: number | null;
};

export type MethodologyMetadata = {
  windDataSource: string;
  windDateRange: string;
  elevationSource: string;
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


export type SiteReportExportRequest = {
  analysis: SiteAnalysisResponse;
  heatmap?: SiteHeatmapResponse | null;
};
