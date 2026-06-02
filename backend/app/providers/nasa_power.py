from __future__ import annotations

import datetime as dt
import math
from typing import Any

import httpx

from app.providers.base import LatLng, WindProvider, WindTimeseries
from app.services.cache import coord_cache_key, wind_timeseries_cache


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


class NasaPowerWindProvider(WindProvider):
    """NASA POWER API (no key required) for wind time series."""

    BASE_URL = "https://power.larc.nasa.gov/api/temporal"

    def __init__(self, *, timeout_s: float = 6.0):
        self._timeout = httpx.Timeout(timeout_s, connect=timeout_s)

    async def get_wind_score(self, p: LatLng) -> tuple[float, dict[str, object]]:
        ts, dbg = await self.get_wind_timeseries(p)
        mean = ts.get("mean_speed_mps", 0.0)
        score = max(0.0, min(100.0, (mean - 3.0) / (10.0 - 3.0) * 100.0))
        return float(score), {"source": "nasa_power", "derived_from": "mean_speed_mps", **dbg}

    async def get_wind_timeseries(
        self, p: LatLng
    ) -> tuple[WindTimeseries, dict[str, object]]:
        cache_key = coord_cache_key(p.latitude, p.longitude)
        cached = wind_timeseries_cache.get(cache_key)
        if cached is not None:
            ts, dbg = cached
            return ts, {**dbg, "cacheHit": True}  # type: ignore[misc]

        end = dt.date.today()
        start = end - dt.timedelta(days=365)
        start_s = start.strftime("%Y%m%d")
        end_s = end.strftime("%Y%m%d")

        params = {
            "parameters": "WS10M",
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
            "periodStart": start_s,
            "periodEnd": end_s,
            "request": {"url": url, "params": params},
            "errors": [],
            "warnings": [],
        }

        speeds: list[float] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                res = await client.get(url, params=params)
                debug["httpStatus"] = res.status_code
                res.raise_for_status()
                payload = res.json()
            except Exception as e:
                debug["errors"] = [f"NASA POWER request failed: {e!s}"]
                ts: WindTimeseries = {
                    "resolution": "daily",
                    "periodStart": start_s,
                    "periodEnd": end_s,
                    "speeds_mps": [],
                    "directions_deg": None,
                    "mean_speed_mps": 0.0,
                }
                wind_timeseries_cache.set(cache_key, (ts, debug))
                return ts, debug

        try:
            props = payload.get("properties") or {}
            param = (props.get("parameter") or {}).get("WS10M") or {}
            for _, v in sorted(param.items()):
                fv = _safe_float(v)
                if fv is None or math.isnan(fv) or fv < 0:
                    continue
                speeds.append(float(fv))
        except Exception as e:
            debug["errors"] = [f"NASA POWER parse failed: {e!s}"]
            speeds = []

        if not speeds:
            debug["warnings"] = ["No usable WS10M samples; falling back to mock."]

        mean_speed = float(sum(speeds) / len(speeds)) if speeds else 0.0
        debug["sampleCount"] = len(speeds)
        debug["mean_speed_mps"] = mean_speed
        debug["min_speed_mps"] = float(min(speeds)) if speeds else None
        debug["max_speed_mps"] = float(max(speeds)) if speeds else None

        ts = WindTimeseries(
            resolution="daily",
            periodStart=start_s,
            periodEnd=end_s,
            speeds_mps=speeds,
            directions_deg=None,
            mean_speed_mps=mean_speed,
        )
        wind_timeseries_cache.set(cache_key, (ts, debug))
        return ts, debug
