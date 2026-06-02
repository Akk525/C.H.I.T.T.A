from __future__ import annotations

import asyncio
import math

from app.providers.base import LatLng
from app.providers.mock import MockAccessibilityProvider
from app.services.analysis import analyze_site_realdata
from app.services.cache import cell_analysis_cache, coord_cache_key
from app.services.methodology import (
    build_heatmap_audit_trail,
    build_heatmap_methodology,
    generate_analysis_id,
    utc_now_iso,
)
from app.services.scoring import total_suitability_optional


def generate_grid_points(
    center: LatLng,
    *,
    radius_km: float,
    grid_size: int,
) -> list[tuple[int, int, LatLng]]:
    n = max(1, grid_size)
    radius_m = radius_km * 1000.0

    lat_deg_per_m = 1.0 / 111_320.0
    lon_deg_per_m = 1.0 / (
        111_320.0 * max(0.2, math.cos(math.radians(center.latitude)))
    )

    if n == 1:
        offsets = [0.0]
    else:
        step = (2.0 * radius_m) / (n - 1)
        offsets = [-radius_m + i * step for i in range(n)]

    points: list[tuple[int, int, LatLng]] = []
    for row, lat_off in enumerate(offsets):
        for col, lon_off in enumerate(offsets):
            points.append(
                (
                    row,
                    col,
                    LatLng(
                        latitude=center.latitude + lat_off * lat_deg_per_m,
                        longitude=center.longitude + lon_off * lon_deg_per_m,
                    ),
                )
            )
    return points


def _provider_status(name: str) -> str:
    if name == "mock":
        return "MOCK"
    if name == "unavailable":
        return "UNAVAILABLE"
    return "REAL"


def _round_or_none(v: float | None) -> float | None:
    return round(v, 1) if v is not None else None


def _cell_label(row: int, col: int, grid_size: int, total: float | None) -> str:
    center_row = (grid_size - 1) / 2.0
    center_col = (grid_size - 1) / 2.0
    dr = row - center_row
    dc = col - center_col

    ns = "N" if dr < -0.01 else "S" if dr > 0.01 else ""
    ew = "E" if dc > 0.01 else "W" if dc < -0.01 else ""
    direction = f"{ns}{ew}".strip() or "Center"

    if total is None:
        return f"{direction} · Data unavailable"

    band = (
        "High"
        if total >= 75
        else "Promising"
        if total >= 60
        else "Mixed"
        if total >= 45
        else "Low"
    )
    return f"{direction} · {band}"


def _public_cell(cell: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in cell.items() if not str(k).startswith("_")}


async def score_cell(
    row: int,
    col: int,
    p: LatLng,
    *,
    grid_size: int,
) -> dict[str, object]:
    cache_key = coord_cache_key(p.latitude, p.longitude)
    cached = cell_analysis_cache.get(cache_key)
    if cached is not None:
        return dict(cached)

    access_provider = MockAccessibilityProvider()
    accessibility_score, _ = await access_provider.get_accessibility_score(p)

    try:
        metrics_fragment, _sources_debug, choice = await analyze_site_realdata(p)
    except Exception:
        cell = {
            "latitude": p.latitude,
            "longitude": p.longitude,
            "metrics": {
                "windScore": None,
                "terrainScore": None,
                "accessibilityScore": round(accessibility_score, 1),
                "confidenceScore": 15.0,
                "totalSuitability": None,
            },
            "label": _cell_label(row, col, grid_size, None),
            "providerStatus": {"wind": "UNAVAILABLE", "elevation": "UNAVAILABLE"},
            "dataUnavailable": True,
        }
        cell_analysis_cache.set(cache_key, cell)
        return cell

    wind_score = metrics_fragment["windScore"]
    terrain_score = metrics_fragment["terrainScore"]
    confidence_score = metrics_fragment["confidenceScore"]

    total = total_suitability_optional(
        wind_score=wind_score,
        terrain_score=terrain_score,
        accessibility_score=accessibility_score,
        confidence_score=confidence_score,
    )

    data_unavailable = total is None

    cell = {
        "latitude": p.latitude,
        "longitude": p.longitude,
        "metrics": {
            "windScore": _round_or_none(wind_score),
            "terrainScore": _round_or_none(terrain_score),
            "accessibilityScore": round(accessibility_score, 1),
            "confidenceScore": round(confidence_score, 1),
            "totalSuitability": _round_or_none(total),
        },
        "label": _cell_label(row, col, grid_size, total),
        "providerStatus": {
            "wind": _provider_status(choice.wind),
            "elevation": _provider_status(choice.elevation),
        },
        "dataUnavailable": data_unavailable,
    }
    cell_analysis_cache.set(cache_key, cell)
    return cell


def _cell_sort_key(cell: dict[str, object]) -> float:
    metrics = cell.get("metrics")
    if not isinstance(metrics, dict):
        return -1.0
    total = metrics.get("totalSuitability")
    return float(total) if total is not None else -1.0


async def build_heatmap(
    center: LatLng,
    *,
    radius_km: float = 10.0,
    grid_size: int = 5,
    max_concurrency: int = 3,
) -> dict[str, object]:
    grid_points = generate_grid_points(center, radius_km=radius_km, grid_size=grid_size)

    sem = asyncio.Semaphore(max_concurrency)

    async def _run(row: int, col: int, p: LatLng) -> dict[str, object]:
        async with sem:
            return await score_cell(row, col, p, grid_size=grid_size)

    results = await asyncio.gather(
        *[_run(row, col, p) for row, col, p in grid_points],
        return_exceptions=True,
    )

    cells: list[dict[str, object]] = []
    for i, result in enumerate(results):
        row, col, p = grid_points[i]
        if isinstance(result, Exception):
            cells.append(_public_cell(await score_cell(row, col, p, grid_size=grid_size)))
        else:
            cells.append(_public_cell(result))

    scored_cells = [
        c
        for c in cells
        if _cell_sort_key(c) >= 0
    ]
    sorted_cells = sorted(scored_cells, key=_cell_sort_key, reverse=True)

    generated_at = utc_now_iso()
    analysis_id = generate_analysis_id()
    methodology = build_heatmap_methodology(
        generated_at=generated_at,
        radius_km=radius_km,
        grid_size=grid_size,
        cells=cells,
    )
    audit_trail = build_heatmap_audit_trail(
        latitude=center.latitude,
        longitude=center.longitude,
        radius_km=radius_km,
        grid_size=grid_size,
        cell_count=len(cells),
        generated_at=generated_at,
        analysis_id=analysis_id,
    )

    return {
        "analysisId": analysis_id,
        "methodology": methodology,
        "auditTrail": audit_trail,
        "center": {"latitude": center.latitude, "longitude": center.longitude},
        "radiusKm": radius_km,
        "gridSize": grid_size,
        "cells": cells,
        "bestCells": sorted_cells[:3],
    }
