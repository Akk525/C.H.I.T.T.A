from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from app.services.analysis import EnrichedData, ProviderChoice

if TYPE_CHECKING:
    from app.services.economics import EconomicMetrics


@dataclass
class AgentEvidence:
    label: str
    value: str   # always stringified for display
    source: str  # "NASA POWER" | "OSM" | "OpenTopoData" | "CHITTA model"


@dataclass
class AgentOutput:
    agentName: str
    status: Literal["complete", "partial", "fallback"]
    confidence: float          # 0–100, domain-specific
    summary: str               # 1-sentence verdict
    findings: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    evidence: list[AgentEvidence] = field(default_factory=list)


@dataclass
class CoordinatorOutput:
    finalDecision: Literal["promising", "mixed", "caution", "poor"]
    topStrengths: list[str]
    topRisks: list[str]
    nextSteps: list[str]
    confidenceSummary: str
    contradictionNotes: list[str]


@dataclass
class AgentContext:
    metrics: dict                  # full metrics_fragment from analyze_site_enriched
    enriched: EnrichedData         # OSM infra, land_cover, protected_area
    debug: dict                    # full debug dict from analyze_site_enriched
    choice: ProviderChoice
    # Pre-computed scores (typed explicitly for clarity inside agents)
    wind_score: float | None
    terrain_score: float | None
    infra_score: float | None
    env_score: float | None
    pop_score: float | None
    lc_score: float | None
    pa_score: float | None
    total_score: float | None
    confidence_score: float
    economic_metrics: "EconomicMetrics | None" = None
