"""
Deterministic mock provider for CHITTA Development Signals.
Returns realistic signals without calling GDELT.
Used when CHITTA_SIGNALS_PROVIDER=mock (default).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone


def _stable_date(seed: int, days_ago_range: tuple[int, int]) -> str:
    lo, hi = days_ago_range
    offset = lo + (seed % (hi - lo + 1))
    dt = datetime.now(timezone.utc) - timedelta(days=offset)
    return dt.isoformat()


_MOCK_SIGNALS: list[dict] = [
    {
        "category": "renewable",
        "title_template": "State approves 500 MW wind energy project in {region} corridor",
        "sentiment": "positive",
        "source": "energynews.in",
        "days_ago": (5, 15),
    },
    {
        "category": "renewable",
        "title_template": "Adani Green commissioned new 200 MW wind farm near {region}",
        "sentiment": "positive",
        "source": "livemint.com",
        "days_ago": (12, 30),
    },
    {
        "category": "renewable",
        "title_template": "{region} wind energy project delayed amid land acquisition disputes",
        "sentiment": "negative",
        "source": "thehindu.com",
        "days_ago": (20, 45),
    },
    {
        "category": "grid",
        "title_template": "PGCIL announces transmission upgrade for {region} renewable evacuation",
        "sentiment": "positive",
        "source": "economictimes.indiatimes.com",
        "days_ago": (8, 25),
    },
    {
        "category": "grid",
        "title_template": "Grid congestion concerns raised for {region} wind integration",
        "sentiment": "negative",
        "source": "powerline.in",
        "days_ago": (30, 60),
    },
    {
        "category": "infrastructure",
        "title_template": "New highway corridor through {region} to improve logistics access",
        "sentiment": "positive",
        "source": "hindustantimes.com",
        "days_ago": (15, 40),
    },
    {
        "category": "environmental",
        "title_template": "Environmental impact assessment approved for {region} wind installations",
        "sentiment": "positive",
        "source": "downtoearth.org.in",
        "days_ago": (10, 35),
    },
    {
        "category": "environmental",
        "title_template": "Wildlife activists oppose wind turbine expansion in {region} forest areas",
        "sentiment": "negative",
        "source": "bbc.com",
        "days_ago": (25, 55),
    },
    {
        "category": "policy",
        "title_template": "State renewable energy target raised to 30 GW — {region} to benefit",
        "sentiment": "positive",
        "source": "pib.gov.in",
        "days_ago": (3, 20),
    },
    {
        "category": "policy",
        "title_template": "Ministry clears land-use policy for {region} wind development zone",
        "sentiment": "positive",
        "source": "mnre.gov.in",
        "days_ago": (7, 28),
    },
    {
        "category": "economic",
        "title_template": "Global funds target {region} renewable projects with $1.2B commitment",
        "sentiment": "positive",
        "source": "bloomberg.com",
        "days_ago": (6, 22),
    },
    {
        "category": "economic",
        "title_template": "Wind energy LCOE in {region} drops below coal — new analysis",
        "sentiment": "positive",
        "source": "irena.org",
        "days_ago": (18, 45),
    },
]


async def query_mock(region_name: str, *, max_records: int = 12) -> list[dict]:
    """Return deterministic mock signals based on region name hash."""
    seed = int(hashlib.md5(region_name.encode()).hexdigest()[:8], 16)
    region_short = region_name.split()[0] if region_name else "Regional"

    results: list[dict] = []
    for i, tmpl in enumerate(_MOCK_SIGNALS[:max_records]):
        item_seed = seed + i
        title = tmpl["title_template"].format(region=region_short)
        pub_at = _stable_date(item_seed, tmpl["days_ago"])
        rel_score = round(0.55 + (((item_seed % 45) / 100)), 3)
        results.append({
            "id": f"mock-{i}",
            "title": title,
            "category": tmpl["category"],
            "summary": f"[Mock signal] {title}",
            "sentiment": tmpl["sentiment"],
            "source": tmpl["source"],
            "url": None,
            "publishedAt": pub_at,
            "relevanceScore": min(1.0, rel_score),
        })

    results.sort(key=lambda x: x["relevanceScore"], reverse=True)
    return results
