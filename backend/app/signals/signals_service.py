"""
Development Signals service for CHITTA.

Orchestrates GDELT/mock queries, groups results by category, and runs
the deterministic DevelopmentSignalsAgent.
"""
from __future__ import annotations

import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from app.signals.gdelt_provider import query_gdelt
from app.signals.mock_provider import query_mock

_SENTIMENT_WEIGHTS = {"positive": 1, "negative": -1, "mixed": 0, "neutral": 0}

_CATEGORY_LABELS = {
    "renewable": "Renewable Energy",
    "grid": "Grid & Transmission",
    "infrastructure": "Infrastructure",
    "environmental": "Environmental",
    "policy": "Policy & Regulation",
    "economic": "Economic Activity",
}


def _dominant_sentiment(signals: list[dict]) -> str:
    score = sum(_SENTIMENT_WEIGHTS.get(s["sentiment"], 0) for s in signals)
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    pos = sum(1 for s in signals if s["sentiment"] == "positive")
    neg = sum(1 for s in signals if s["sentiment"] == "negative")
    return "mixed" if pos > 0 and neg > 0 else "neutral"


def _group_insights(signals: list[dict]) -> list[dict]:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for s in signals:
        by_cat[s["category"]].append(s)

    insights: list[dict] = []
    for cat, sigs in by_cat.items():
        dom_sent = _dominant_sentiment(sigs)
        pos = sum(1 for s in sigs if s["sentiment"] == "positive")
        neg = sum(1 for s in sigs if s["sentiment"] == "negative")
        theme_parts = []
        if pos > 0:
            theme_parts.append(f"{pos} positive signal{'s' if pos > 1 else ''}")
        if neg > 0:
            theme_parts.append(f"{neg} risk signal{'s' if neg > 1 else ''}")
        key_theme = f"{_CATEGORY_LABELS.get(cat, cat)}: {', '.join(theme_parts) or 'neutral activity'}"
        insights.append({
            "category": cat,
            "categoryLabel": _CATEGORY_LABELS.get(cat, cat),
            "signalCount": len(sigs),
            "sentiment": dom_sent,
            "keyTheme": key_theme,
        })

    insights.sort(key=lambda x: x["signalCount"], reverse=True)
    return insights


def _agent_summary(signals: list[dict], grouped: list[dict], region_name: str) -> str:
    """Deterministic DevelopmentSignalsAgent — no LLM required."""
    if not signals:
        return (
            f"No recent development signals found for {region_name}. "
            "This may indicate limited news coverage or a low-activity period. "
            "Manual desk research is recommended."
        )

    total = len(signals)
    positive = sum(1 for s in signals if s["sentiment"] == "positive")
    negative = sum(1 for s in signals if s["sentiment"] == "negative")
    overall = _dominant_sentiment(signals)

    renewable_sigs = [s for s in signals if s["category"] == "renewable"]
    policy_sigs = [s for s in signals if s["category"] == "policy"]
    env_sigs = [s for s in signals if s["category"] == "environmental" and s["sentiment"] == "negative"]

    momentum = "strong positive" if positive >= total * 0.6 else \
               "broadly positive" if positive > negative else \
               "mixed or cautious" if positive >= negative * 0.5 else "predominantly challenging"

    lines = [
        f"Regional development momentum for {region_name} is {momentum} "
        f"based on {total} signals ({positive} positive, {negative} risk).",
    ]

    if renewable_sigs:
        ren_pos = sum(1 for s in renewable_sigs if s["sentiment"] == "positive")
        ren_label = "active investment and project activity" if ren_pos >= len(renewable_sigs) * 0.6 else "mixed activity"
        lines.append(
            f"Renewable energy sector shows {ren_label} "
            f"({ren_pos}/{len(renewable_sigs)} signals positive)."
        )

    if policy_sigs and any(s["sentiment"] == "positive" for s in policy_sigs):
        lines.append("Policy signals are supportive, with recent government actions favouring renewable development.")

    if env_sigs:
        lines.append(
            f"Environmental risk signals detected ({len(env_sigs)} negative) — "
            "permitting friction and biodiversity concerns may affect project timelines."
        )

    lines.append(
        "ADVISORY: Signals are derived from news media only and are not verified facts. "
        "Treat as directional intelligence, not investment analysis."
    )

    return " ".join(lines)


async def run_signals_query(
    region_name: str,
    latitude: float,
    longitude: float,
    radius_km: float = 100.0,
) -> dict:
    provider = os.environ.get("CHITTA_SIGNALS_PROVIDER", "mock").strip().lower()
    warnings: list[str] = []

    try:
        if provider == "gdelt":
            signals = await query_gdelt(region_name, max_records=25, timespan="90d")
            if len(signals) < 3:
                warnings.append(
                    f"GDELT returned only {len(signals)} articles for '{region_name}'. "
                    "Results may be sparse for this region."
                )
        else:
            signals = await query_mock(region_name, max_records=12)
            warnings.append("Using mock signals — set CHITTA_SIGNALS_PROVIDER=gdelt for live GDELT data.")
    except Exception as exc:
        signals = await query_mock(region_name, max_records=12)
        warnings.append(f"GDELT query failed ({exc!s}) — fell back to mock signals.")

    grouped = _group_insights(signals)
    agent_summary = _agent_summary(signals, grouped, region_name)

    return {
        "queryId": str(uuid.uuid4()),
        "regionName": region_name,
        "provider": provider,
        "signals": signals,
        "groupedInsights": grouped,
        "agentSummary": agent_summary,
        "warnings": warnings,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
