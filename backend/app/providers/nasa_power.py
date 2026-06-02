from __future__ import annotations

import datetime as dt
import math
from typing import Any

import httpx

from app.providers.base import LatLng, MultiHeightWind, WindProvider, WindTimeseries
from app.services.cache import coord_cache_key, multi_height_wind_cache, wind_timeseries_cache


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if s.lower() in {"nan", "none", ""}:
            return None
        return float(s)
    except Exception:
        return None


def _parse_param_series(param_dict: dict[str, Any]) -> list[float]:
    speeds: list[float] = []
    for _, v in sorted(param_dict.items()):
        fv = _safe_float(v)
        if fv is None or math.isnan(fv) or fv < 0:
            continue
        speeds.append(float(fv))
    return speeds


def _mean(speeds: list[float]) -> float:
    return float(sum(speeds) / len(speeds)) if speeds else 0.0


def _wind_power_density(mean_speed_mps: float) -> float:
    """Simplified wind power density W/m² using mean³ (air density ≈ 1.225 kg/m³)."""
    return 0.5 * 1.225 * (mean_speed_mps ** 3)


class NasaPowerWindProvider(WindProvider):
    """
    NASA POWER API (no key required).
    Queries WS10M, WS50M, WS100M in a single request.
    The primary timeseries (returned via get_wind_timeseries) uses the highest
    available height — 100m when possible, then 50m, then 10m.
    """

    BASE_URL = "https://power.larc.nasa.gov/api/temporal"

    def __init__(self, *, timeout_s: float = 10.0):
        self._timeout = httpx.Timeout(timeout_s, connect=timeout_s)

    async def get_wind_score(self, p: LatLng) -> tuple[float, dict[str, object]]:
        ts, dbg = await self.get_wind_timeseries(p)
        mean = ts.get("mean_speed_mps", 0.0)
        score = max(0.0, min(100.0, (mean - 3.0) / (10.0 - 3.0) * 100.0))
        return float(score), {"source": "nasa_power", "derived_from": "mean_speed_mps", **dbg}

    async def get_wind_timeseries(
        self, p: LatLng
    ) -> tuple[WindTimeseries, dict[str, object]]:
        mh, dbg = await self.get_multi_height_wind(p)
        # Use highest available height for the timeseries
        height = mh["primary_height_m"]
        mean = mh[f"mean_{height}m_mps"]  # type: ignore[literal-required]
        ts = WindTimeseries(
            resolution="daily",
            periodStart=dbg.get("periodStart", ""),  # type: ignore[arg-type]
            periodEnd=dbg.get("periodEnd", ""),  # type: ignore[arg-type]
            speeds_mps=dbg.get(f"speeds_{height}m", []),  # type: ignore[arg-type]
            directions_deg=None,
            mean_speed_mps=float(mean) if mean is not None else 0.0,
            hub_height_m=height,
        )
        return ts, dbg

    # NASA POWER RE/daily community supports WS10M and WS50M.
    # WS100M is NOT available for this community/resolution (returns 422).
    # We request both heights and prefer WS50M for scoring (closer to turbine hub).
    # A 10-day lag buffer guards against the edge of data availability.
    _SAFE_LAG_DAYS = 10

    async def get_multi_height_wind(
        self, p: LatLng
    ) -> tuple[MultiHeightWind, dict[str, object]]:
        cache_key = coord_cache_key(p.latitude, p.longitude)
        cached = multi_height_wind_cache.get(cache_key)
        if cached is not None:
            mh, dbg = cached
            return mh, {**dbg, "cacheHit": True}  # type: ignore[misc]

        end = dt.date.today() - dt.timedelta(days=self._SAFE_LAG_DAYS)
        start = end - dt.timedelta(days=365)
        start_s = start.strftime("%Y%m%d")
        end_s = end.strftime("%Y%m%d")
        parameters_requested = "WS10M,WS50M"

        params = {
            "parameters": parameters_requested,
            "community": "RE",
            "longitude": f"{p.longitude:.6f}",
            "latitude": f"{p.latitude:.6f}",
            "start": start_s,
            "end": end_s,
            "format": "JSON",
        }

        url = f"{self.BASE_URL}/daily/point"
        debug: dict[str, object] = {
            "provider": "nasa_power",
            "source": "nasa_power",
            "resolution": "daily",
            "requestedStartDate": start_s,
            "requestedEndDate": end_s,
            "latestCompletedDate": None,
            "daysReturned": 0,
            "parametersRequested": parameters_requested,
            "parametersUsed": None,
            # Legacy keys for backward compat
            "periodStart": start_s,
            "periodEnd": end_s,
            "errors": [],
            "warnings": [],
        }

        speeds_10m: list[float] = []
        speeds_50m: list[float] = []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                res = await client.get(url, params=params)
                debug["httpStatus"] = res.status_code
                res.raise_for_status()
                payload = res.json()
            except Exception as e:
                debug["errors"] = [f"NASA POWER request failed: {e!s}"]
                mh = MultiHeightWind(
                    mean_10m_mps=None,
                    mean_50m_mps=None,
                    mean_100m_mps=None,
                    power_density_w_m2=None,
                    primary_height_m=10,
                )
                multi_height_wind_cache.set(cache_key, (mh, debug))
                _empty_ts = WindTimeseries(
                    resolution="daily", periodStart=start_s, periodEnd=end_s,
                    speeds_mps=[], directions_deg=None, mean_speed_mps=0.0, hub_height_m=10,
                )
                wind_timeseries_cache.set(cache_key, (_empty_ts, debug))
                return mh, debug

        try:
            props = payload.get("properties") or {}
            param_block = props.get("parameter") or {}

            ws10m_raw = param_block.get("WS10M") or {}
            ws50m_raw = param_block.get("WS50M") or {}

            speeds_10m = _parse_param_series(ws10m_raw)
            speeds_50m = _parse_param_series(ws50m_raw)

            # Derive latest date with valid data
            best_raw = ws50m_raw or ws10m_raw
            if best_raw:
                valid_dates = sorted(
                    k for k, v in best_raw.items()
                    if (_safe_float(v) or -1) >= 0 and not math.isnan(_safe_float(v) or float("nan"))  # type: ignore[arg-type]
                )
                if valid_dates:
                    debug["latestCompletedDate"] = valid_dates[-1]
        except Exception as e:
            debug["errors"] = [f"NASA POWER parse failed: {e!s}"]

        speeds_100m: list[float] = []  # WS100M not available; kept for type compat

        mean_10 = _mean(speeds_10m) if speeds_10m else None
        mean_50 = _mean(speeds_50m) if speeds_50m else None
        mean_100: float | None = None  # WS100M not available in RE/daily

        # Pick highest available height: WS50M preferred over WS10M
        if mean_50 is not None and mean_50 > 0:
            primary_height = 50
            primary_speeds = speeds_50m
            parameters_used = "WS50M"
        elif mean_10 is not None and mean_10 > 0:
            primary_height = 10
            primary_speeds = speeds_10m
            parameters_used = "WS10M (WS50M unavailable)"
        else:
            primary_height = 10
            primary_speeds = []
            parameters_used = "none"

        primary_mean = _mean(primary_speeds) if primary_speeds else None
        power_density = _wind_power_density(float(mean_100 or mean_50 or mean_10 or 0))

        debug["daysReturned"] = len(primary_speeds)
        debug["parametersUsed"] = parameters_used
        debug["sampleCount_10m"] = len(speeds_10m)
        debug["sampleCount_50m"] = len(speeds_50m)
        debug["sampleCount_100m"] = len(speeds_100m)
        debug["mean_10m_mps"] = mean_10
        debug["mean_50m_mps"] = mean_50
        debug["mean_100m_mps"] = mean_100
        debug["primary_height_m"] = primary_height
        debug["power_density_w_m2"] = power_density
        # Store speeds under height key for get_wind_timeseries to retrieve
        debug[f"speeds_{primary_height}m"] = primary_speeds

        if not primary_speeds:
            debug["warnings"] = ["No usable wind speed samples at any height — all parameters returned fill values or empty series."]

        mh = MultiHeightWind(
            mean_10m_mps=mean_10,
            mean_50m_mps=mean_50,
            mean_100m_mps=mean_100,
            power_density_w_m2=power_density,
            primary_height_m=primary_height,
        )
        multi_height_wind_cache.set(cache_key, (mh, debug))

        ts = WindTimeseries(
            resolution="daily",
            periodStart=start_s,
            periodEnd=end_s,
            speeds_mps=primary_speeds,
            directions_deg=None,
            mean_speed_mps=float(primary_mean) if primary_mean is not None else 0.0,
            hub_height_m=primary_height,
        )
        wind_timeseries_cache.set(cache_key, (ts, debug))

        return mh, debug
