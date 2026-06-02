from __future__ import annotations

import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Simple in-memory TTL cache for provider/analysis results."""

    def __init__(self, *, ttl_s: float = 3600.0, max_size: int = 512):
        self._ttl = ttl_s
        self._max_size = max_size
        self._store: dict[str, tuple[float, T]] = {}

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._store.items() if exp <= now]
        for k in expired:
            del self._store[k]

    def _evict_oldest(self) -> None:
        if len(self._store) <= self._max_size:
            return
        oldest = min(self._store.items(), key=lambda item: item[1][0])
        del self._store[oldest[0]]

    def get(self, key: str) -> T | None:
        self._evict_expired()
        entry = self._store.get(key)
        if entry is None:
            return None
        exp, value = entry
        if exp <= time.monotonic():
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: T) -> None:
        self._evict_expired()
        self._evict_oldest()
        self._store[key] = (time.monotonic() + self._ttl, value)


def coord_cache_key(lat: float, lng: float, *, precision: int = 3) -> str:
    return f"{round(lat, precision)}:{round(lng, precision)}"


cell_analysis_cache: TTLCache[dict[str, object]] = TTLCache(ttl_s=3600.0, max_size=512)

wind_timeseries_cache: TTLCache[tuple[object, dict[str, object]]] = TTLCache(ttl_s=3600.0, max_size=256)
elevation_point_cache: TTLCache[tuple[float, dict[str, object]]] = TTLCache(ttl_s=3600.0, max_size=256)
elevation_samples_cache: TTLCache[tuple[list[object], dict[str, object]]] = TTLCache(ttl_s=3600.0, max_size=256)
