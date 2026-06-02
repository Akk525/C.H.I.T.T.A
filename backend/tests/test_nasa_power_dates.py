"""
Smoke tests for NASA POWER date handling.

These tests make real HTTP calls to NASA POWER.
Run with: pytest tests/test_nasa_power_dates.py -v
"""
from __future__ import annotations

import datetime as dt

import pytest

import pytest

from app.providers.base import LatLng
from app.providers.nasa_power import NasaPowerWindProvider
from app.services import cache as _cache_module

# Chitradurga, Karnataka — well-known Indian wind corridor
CHITRADURGA = LatLng(latitude=14.2251, longitude=76.398)


@pytest.fixture(autouse=True)
def clear_caches():
    """Reset all provider caches before each test so tests are independent."""
    _cache_module.multi_height_wind_cache._store.clear()
    _cache_module.wind_timeseries_cache._store.clear()
    yield


@pytest.mark.asyncio
async def test_safe_end_date_is_in_past():
    """The computed end date must be strictly before today."""
    provider = NasaPowerWindProvider()
    today = dt.date.today()
    end = today - dt.timedelta(days=provider._SAFE_LAG_DAYS)
    assert end < today, f"End date {end} is not strictly before today {today}"


@pytest.mark.asyncio
async def test_ws100m_not_requested():
    """
    WS100M must not be in the parameters sent to NASA POWER.
    It is not available in the RE/daily community and causes a 422.
    """
    import inspect, re
    source = inspect.getsource(NasaPowerWindProvider.get_multi_height_wind)
    # Find the parameters_requested assignment line
    match = re.search(r'parameters_requested\s*=\s*"([^"]+)"', source)
    assert match, "Could not find parameters_requested assignment in get_multi_height_wind"
    params_value = match.group(1)
    assert "WS100M" not in params_value, (
        f"parameters_requested ({params_value!r}) must not include WS100M — "
        "not available in NASA POWER RE/daily community"
    )


@pytest.mark.asyncio
async def test_chitradurga_wind_not_fallback_due_to_future_dates():
    """
    Wind provider must return real data for Chitradurga — fallback should only
    occur due to genuine API failure, not because we requested future/unprocessed dates.
    """
    provider = NasaPowerWindProvider()
    mh, debug = await provider.get_multi_height_wind(CHITRADURGA)

    # The requested window must not extend into the future
    requested_end = debug.get("requestedEndDate", "")
    today_s = dt.date.today().strftime("%Y%m%d")
    assert requested_end <= today_s, (
        f"requestedEndDate ({requested_end}) is in the future relative to today ({today_s})"
    )

    # We must have received some data
    days_returned = int(debug.get("daysReturned") or 0)
    assert days_returned > 100, (
        f"Expected >100 days of wind data, got {days_returned}. "
        f"parametersUsed={debug.get('parametersUsed')}, "
        f"errors={debug.get('errors')}"
    )

    # Primary height must be non-zero
    primary_height = mh["primary_height_m"]
    assert primary_height in {10, 50, 100}, f"Unexpected primary_height_m: {primary_height}"

    # Mean speed at primary height must be positive
    mean_key = f"mean_{primary_height}m_mps"
    mean_val = mh.get(mean_key)  # type: ignore[call-overload]
    assert mean_val is not None and mean_val > 0, (
        f"Mean wind speed at {primary_height}m is {mean_val} — expected a positive float"
    )


@pytest.mark.asyncio
async def test_debug_fields_present():
    """All required debug fields must be present and populated."""
    provider = NasaPowerWindProvider()
    _, debug = await provider.get_multi_height_wind(CHITRADURGA)

    required_fields = [
        "requestedStartDate",
        "requestedEndDate",
        "daysReturned",
        "parametersRequested",
        "parametersUsed",
        "primary_height_m",
    ]
    for field in required_fields:
        assert field in debug, f"Missing debug field: {field}"
        assert debug[field] is not None, f"Debug field {field} is None"

    # latestCompletedDate may be None only if all data was fill values
    # (which shouldn't happen for Chitradurga) — assert it's present
    assert "latestCompletedDate" in debug, "Missing latestCompletedDate in debug"
    assert debug["latestCompletedDate"] is not None, (
        "latestCompletedDate is None — suggests no valid data returned"
    )


@pytest.mark.asyncio
async def test_wind_agent_status_not_fallback_for_chitradurga():
    """
    WindAgent.status must be 'complete' or 'partial' for Chitradurga,
    never 'fallback', when the date window is correct.
    """
    import asyncio
    from app.services.analysis import analyze_site_enriched
    from app.services.scoring import (
        environmental_score, infrastructure_score, land_cover_score,
        population_score, protected_area_score, total_suitability_v2,
    )
    from app.agents import AgentContext, WindAgent

    metrics, debug, choice, enriched = await analyze_site_enriched(CHITRADURGA)

    infra = enriched.get("infrastructure")
    lc = enriched.get("land_cover")
    pa = enriched.get("protected_area")
    infra_s = infrastructure_score(
        infra.get("nearest_road_m") if infra else None,
        infra.get("nearest_powerline_m") if infra else None,
    ) if infra else None
    lc_class = lc.get("cover_class") if lc else None
    lc_s = land_cover_score(lc_class)
    in_pa = pa.get("in_protected_area", False) if pa else False
    pa_s = protected_area_score(in_pa, pa.get("nearest_pa_m") if pa else None)
    env_s = environmental_score(lc_s, pa_s)
    settle = infra.get("settlement_count_15km") if infra else None
    pop_s = population_score(settle) if settle is not None else None
    total = total_suitability_v2(
        metrics["windScore"], metrics["terrainScore"],
        infra_s, env_s, pop_s, float(metrics["confidenceScore"]),
    )

    ctx = AgentContext(
        metrics=metrics, enriched=enriched, debug=debug, choice=choice,
        wind_score=metrics["windScore"], terrain_score=metrics["terrainScore"],
        infra_score=infra_s, env_score=env_s, pop_score=pop_s,
        lc_score=lc_s, pa_score=pa_s, total_score=total,
        confidence_score=float(metrics["confidenceScore"]),
    )
    wind_out = WindAgent().run(ctx)

    assert wind_out.status != "fallback", (
        f"WindAgent fell back for Chitradurga — check NASA POWER date window. "
        f"Debug: {debug.get('sources', {}).get('wind', {}).get('debug', {})}"
    )
    assert wind_out.confidence > 20, (
        f"WindAgent confidence is too low ({wind_out.confidence}) — expected >20 for real data"
    )
