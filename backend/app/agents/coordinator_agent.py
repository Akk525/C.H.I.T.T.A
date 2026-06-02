from __future__ import annotations

from typing import Literal

from app.agents.base import AgentContext, AgentOutput, CoordinatorOutput


def _find(agents: list[AgentOutput], name: str) -> AgentOutput | None:
    for a in agents:
        if a.agentName.lower() == name.lower():
            return a
    return None


def _complete_or_partial(agent: AgentOutput | None) -> bool:
    return agent is not None and agent.status in {"complete", "partial"}


def _decide(ctx: AgentContext, agents: list[AgentOutput]) -> Literal["promising", "mixed", "caution", "poor"]:
    wind = _find(agents, "wind")
    terrain = _find(agents, "terrain")

    wind_fallback = wind is None or wind.status == "fallback"
    terrain_fallback = terrain is None or terrain.status == "fallback"

    if wind_fallback and terrain_fallback:
        return "caution"

    total = ctx.total_score
    if total is None:
        return "caution"

    if total >= 68:
        return "promising"
    if total >= 50:
        return "mixed"
    if total >= 32:
        return "caution"
    return "poor"


def _contradictions(ctx: AgentContext, agents: list[AgentOutput]) -> list[str]:
    notes: list[str] = []
    wind = _find(agents, "wind")
    terrain = _find(agents, "terrain")
    env = _find(agents, "environmental")

    ws = ctx.wind_score
    ts = ctx.terrain_score
    env_s = ctx.env_score
    infra_s = ctx.infra_score

    pa_data = ctx.enriched.get("protected_area")
    in_pa = pa_data.get("in_protected_area", False) if pa_data else False

    lc_data = ctx.enriched.get("land_cover")
    cover_class = lc_data.get("cover_class") if lc_data else None

    # Good wind but inside PA
    if ws is not None and ws >= 65 and in_pa:
        notes.append(
            "Strong wind signal but site overlaps a protected area — feasibility is constrained by regulatory factors regardless of wind resource."
        )

    # Good wind but urban land cover
    if ws is not None and ws >= 65 and cover_class == "urban":
        notes.append(
            "Good wind resource but urban land cover — zoning and noise constraints likely make development impractical."
        )

    # Good terrain but no wind data
    if ts is not None and ts >= 70 and (wind is None or wind.status == "fallback"):
        notes.append(
            "Favourable terrain but wind data is unavailable — site viability cannot be confirmed without a wind resource assessment."
        )

    # Good infrastructure but poor environmental score
    if infra_s is not None and infra_s >= 75 and env_s is not None and env_s <= 35:
        notes.append(
            "Good infrastructure access but significant environmental constraints — confirm the permitting pathway before advancing development plans."
        )

    # Good wind but high settlement density
    settle_count = None
    infra = ctx.enriched.get("infrastructure")
    if infra:
        settle_count = infra.get("settlement_count_15km")
    if ws is not None and ws >= 65 and settle_count is not None and settle_count > 10:
        notes.append(
            "Strong wind resource but high settlement density — permitting timeline risk is elevated and community opposition is likely."
        )

    # Good wind but constrained economics (likely terrain/infra CAPEX premium)
    eco = ctx.economic_metrics
    if eco is not None and eco.economic_score < 35 and ws is not None and ws >= 65:
        notes.append(
            "Strong wind resource but preliminary economics are constrained — likely due to terrain or infrastructure CAPEX premium raising the LCOE above market benchmarks."
        )

    return notes


def _confidence_summary(agents: list[AgentOutput]) -> str:
    complete = [a for a in agents if a.status == "complete"]
    partial = [a for a in agents if a.status == "partial"]
    fallback = [a for a in agents if a.status == "fallback"]

    parts: list[str] = []
    if complete:
        names = ", ".join(a.agentName for a in complete)
        parts.append(f"{len(complete)} agent(s) with full data ({names})")
    if partial:
        names = ", ".join(a.agentName for a in partial)
        parts.append(f"{len(partial)} agent(s) with partial data ({names})")
    if fallback:
        names = ", ".join(a.agentName for a in fallback)
        parts.append(f"{len(fallback)} agent(s) with no data ({names})")

    if not parts:
        return "No agent data available."

    summary = "Analysis based on: " + "; ".join(parts) + "."
    if fallback:
        summary += " Scores for unavailable domains use neutral fallback values."
    return summary


class CoordinatorAgent:
    def run(self, agents: list[AgentOutput], ctx: AgentContext) -> CoordinatorOutput:
        decision = _decide(ctx, agents)

        # Top strengths: best finding from each complete/partial agent with a positive signal
        strengths: list[str] = []
        for agent in agents:
            if agent.status == "fallback":
                continue
            score = getattr(ctx, f"{agent.agentName.lower()}_score", None)
            # Use the first finding if score is decent or findings exist
            if agent.findings:
                strengths.append(f"[{agent.agentName}] {agent.findings[0]}")

        # Top risks: first risk from each agent that has one, complete agents first
        risks: list[str] = []
        for agent in sorted(agents, key=lambda a: 0 if a.status == "complete" else 1):
            if agent.risks:
                risks.append(f"[{agent.agentName}] {agent.risks[0]}")

        # Next steps: de-duplicated recommendations across agents (max 5)
        seen: set[str] = set()
        steps: list[str] = []
        for agent in agents:
            for rec in agent.recommendations:
                normalised = rec.lower()[:60]
                if normalised not in seen:
                    seen.add(normalised)
                    steps.append(rec)
                if len(steps) >= 5:
                    break
            if len(steps) >= 5:
                break

        contradictions = _contradictions(ctx, agents)
        conf_summary = _confidence_summary(agents)

        return CoordinatorOutput(
            finalDecision=decision,
            topStrengths=strengths[:4],
            topRisks=risks[:4],
            nextSteps=steps[:5],
            confidenceSummary=conf_summary,
            contradictionNotes=contradictions,
        )
