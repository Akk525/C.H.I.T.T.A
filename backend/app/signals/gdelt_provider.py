"""
GDELT DOC API v2 provider for CHITTA Development Signals.

Rate limit: 1 request per 5 seconds. Endpoint: api.gdeltproject.org/api/v2/doc/doc
Article data includes title, domain, seendate, language, sourcecountry — no full text.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

import httpx

_GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_TIMEOUT = 12.0

# Simple sentiment keywords applied to article titles
_POSITIVE = frozenset([
    "launch", "commission", "approv", "install", "invest", "milestone",
    "award", "secure", "expand", "success", "complet", "sign", "open",
    "partner", "boost", "fund", "connect", "achiev", "progress",
])
_NEGATIVE = frozenset([
    "block", "cancel", "delay", "protest", "reject", "oppos", "disput",
    "controvers", "violat", "challeng", "halt", "suspend", "abandon",
    "damage", "pollut", "concern", "threat", "ban", "shut",
])

# Category keyword sets (matched against title lowercase)
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "renewable": ["wind", "solar", "renewable", "turbine", "clean energy", "green energy", "photovoltaic"],
    "grid": ["transmission", "power grid", "electricity grid", "substation", "interconnect", "powerline", "power line"],
    "infrastructure": ["highway", "road", "railway", "transport", "connectivity", "corridor"],
    "environmental": ["biodiversity", "forest", "protected area", "wildlife", "deforest", "pollution", "habitat"],
    "policy": ["energy policy", "renewable target", "subsidy", "regulation", "government", "ministry", "tender", "tariff"],
    "economic": ["investment", "billion", "million", "project", "company", "venture", "finance", "ipo", "stock"],
}

_MAJOR_DOMAINS = frozenset([
    "reuters.com", "bloomberg.com", "thehindu.com", "hindustantimes.com",
    "economictimes.indiatimes.com", "livemint.com", "bbc.com", "ft.com",
    "wsj.com", "nytimes.com", "theguardian.com", "mercopress.com",
])


def _parse_gdelt_date(seendate: str) -> str:
    """Convert GDELT date string '20260506T081500Z' to ISO format."""
    try:
        dt = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return seendate


def _classify_category(title: str) -> str:
    lower = title.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return cat
    return "economic"


def _classify_sentiment(title: str) -> str:
    lower = title.lower()
    pos = sum(1 for kw in _POSITIVE if kw in lower)
    neg = sum(1 for kw in _NEGATIVE if kw in lower)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    if pos > 0 and neg > 0:
        return "mixed"
    return "neutral"


def _relevance_score(title: str, domain: str, seendate: str, region_name: str) -> float:
    score = 0.0
    lower = title.lower()
    region_lower = region_name.lower()

    # Region name match in title
    if any(part in lower for part in region_lower.split() if len(part) > 3):
        score += 0.35

    # Renewable/energy keywords
    energy_kws = ["wind", "solar", "renewable", "energy", "power"]
    if any(kw in lower for kw in energy_kws):
        score += 0.25

    # Major source domain
    if domain in _MAJOR_DOMAINS:
        score += 0.15

    # Recency bonus
    try:
        dt = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - dt).days
        if age_days <= 30:
            score += 0.25
        elif age_days <= 60:
            score += 0.15
        elif age_days <= 90:
            score += 0.05
    except Exception:
        pass

    return round(min(1.0, score), 3)


def _build_summary(title: str, category: str, sentiment: str) -> str:
    """Generate a short summary from title since GDELT doesn't provide article body."""
    cat_label = {
        "renewable": "renewable energy development",
        "grid": "electricity infrastructure",
        "infrastructure": "physical infrastructure",
        "environmental": "environmental conditions",
        "policy": "energy policy",
        "economic": "economic activity",
    }.get(category, category)
    tone = {"positive": "Positive signal", "negative": "Risk signal",
            "mixed": "Mixed signal", "neutral": "Development signal"}.get(sentiment, "Signal")
    return f"{tone} for {cat_label}. {title[:120]}{'…' if len(title) > 120 else ''}"


async def query_gdelt(
    region_name: str,
    *,
    max_records: int = 25,
    timespan: str = "90d",
) -> list[dict]:
    """
    Query GDELT DOC API for development signals related to a region.
    Returns raw article dicts with added classification fields.
    """
    # Build query: region name + energy/infrastructure keywords
    safe_region = re.sub(r'[^\w\s]', '', region_name).strip()
    words = safe_region.split()[:3]  # Use first 3 words max
    region_part = " ".join(words)

    query = (
        f'"{region_part}" '
        f'(wind OR solar OR renewable OR transmission OR "power grid" OR '
        f'environmental OR "clean energy" OR infrastructure OR energy)'
    )

    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": max_records,
        "format": "json",
        "timespan": timespan,
        "sort": "hybridrel",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(_GDELT_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    articles = data.get("articles") or []
    results: list[dict] = []

    for i, art in enumerate(articles):
        title = art.get("title", "") or ""
        domain = art.get("domain", "") or ""
        seendate = art.get("seendate", "") or ""
        url = art.get("url", "") or ""

        if not title or not url:
            continue

        category = _classify_category(title)
        sentiment = _classify_sentiment(title)
        rel_score = _relevance_score(title, domain, seendate, region_name)

        results.append({
            "id": f"gdelt-{i}",
            "title": title,
            "category": category,
            "summary": _build_summary(title, category, sentiment),
            "sentiment": sentiment,
            "source": domain,
            "url": url,
            "publishedAt": _parse_gdelt_date(seendate),
            "relevanceScore": rel_score,
        })

    # Sort by relevance descending
    results.sort(key=lambda x: x["relevanceScore"], reverse=True)
    return results
