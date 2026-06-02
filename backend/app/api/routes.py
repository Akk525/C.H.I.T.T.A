from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import (
    SiteAnalysisRequest,
    SiteAnalysisResponse,
    SiteHeatmapRequest,
    SiteHeatmapResponse,
)
from app.providers.base import LatLng
from app.providers.mock import MockAccessibilityProvider
from app.services.analysis import analyze_site_realdata
from app.services.heatmap import build_heatmap
from app.services.report import build_report
from app.services.scoring import total_suitability

router = APIRouter()


@router.post("/api/site-analysis", response_model=SiteAnalysisResponse)
async def site_analysis(req: SiteAnalysisRequest) -> SiteAnalysisResponse:
    p = LatLng(latitude=req.latitude, longitude=req.longitude)

    access_provider = MockAccessibilityProvider()

    accessibility_score, acc_dbg = await access_provider.get_accessibility_score(p)

    metrics_fragment, sources_debug, _choice = await analyze_site_realdata(p)
    wind_score = metrics_fragment["windScore"]
    terrain_score = metrics_fragment["terrainScore"]
    confidence_score = metrics_fragment["confidenceScore"]
    elevation_m = metrics_fragment["elevationM"]
    terrain_complexity = metrics_fragment["terrainComplexity"]

    total = total_suitability(
        wind_score=wind_score,
        terrain_score=terrain_score,
        accessibility_score=accessibility_score,
        confidence_score=confidence_score,
    )

    report = build_report(
        total=total,
        wind=wind_score,
        terrain=terrain_score,
        accessibility=accessibility_score,
        confidence=confidence_score,
        elevation_m=elevation_m,
        terrain_complexity=terrain_complexity,
        data_sources=[
            f"Wind: {sources_debug.get('sources', {}).get('wind', {}).get('provider', 'unknown')}",
            f"Elevation: {sources_debug.get('sources', {}).get('elevation', {}).get('provider', 'unknown')}",
            "Accessibility: mock (OSM integration planned)",
        ],
    )

    return SiteAnalysisResponse(
        inputs=req,
        metrics={
            "windScore": wind_score,
            "terrainScore": terrain_score,
            "accessibilityScore": accessibility_score,
            "confidenceScore": confidence_score,
            "elevationM": elevation_m,
            "terrainComplexity": terrain_complexity,
        },
        totalSuitabilityScore=total,
        report=report,  # type: ignore[arg-type]
        debug={
            "accessibility": acc_dbg,
            **sources_debug,
        },
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

