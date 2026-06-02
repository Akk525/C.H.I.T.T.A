from __future__ import annotations

from pydantic import BaseModel, Field


class SiteAnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class SiteAnalysisMetrics(BaseModel):
    windScore: float
    terrainScore: float
    accessibilityScore: float
    confidenceScore: float
    elevationM: float
    terrainComplexity: float


class ConsultantReport(BaseModel):
    executiveSummary: str
    siteStrengths: list[str]
    risks: list[str]
    recommendations: list[str]
    confidenceNotes: list[str]
    dataSources: list[str]


class SiteAnalysisResponse(BaseModel):
    inputs: SiteAnalysisRequest
    metrics: SiteAnalysisMetrics
    totalSuitabilityScore: float
    report: ConsultantReport
    debug: dict[str, object] | None = None


class SiteHeatmapRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radiusKm: float = Field(default=10.0, gt=0, le=50)
    gridSize: int = Field(default=5, ge=1, le=9)


class HeatmapCellMetrics(BaseModel):
    windScore: float
    terrainScore: float
    accessibilityScore: float
    confidenceScore: float
    totalSuitability: float


class HeatmapProviderStatus(BaseModel):
    wind: str
    elevation: str


class HeatmapCell(BaseModel):
    latitude: float
    longitude: float
    metrics: HeatmapCellMetrics
    label: str
    providerStatus: HeatmapProviderStatus


class SiteHeatmapResponse(BaseModel):
    center: SiteAnalysisRequest
    radiusKm: float
    gridSize: int
    cells: list[HeatmapCell]
    bestCells: list[HeatmapCell]



class SiteReportExportRequest(BaseModel):
    analysis: SiteAnalysisResponse
    heatmap: SiteHeatmapResponse | None = None
