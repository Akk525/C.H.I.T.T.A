from __future__ import annotations

from app.agents.base import AgentContext, AgentEvidence, AgentOutput


def _fmt_km(m: float | None) -> str:
    if m is None:
        return "unknown"
    return f"{m / 1000:.1f} km" if m >= 1000 else f"{m:.0f} m"


class InfrastructureAgent:
    def run(self, ctx: AgentContext) -> AgentOutput:
        infra = ctx.enriched.get("infrastructure")
        infra_score = ctx.infra_score

        road_m = infra.get("nearest_road_m") if infra else None
        power_m = infra.get("nearest_powerline_m") if infra else None
        rail_m = infra.get("nearest_rail_m") if infra else None
        settle_count = infra.get("settlement_count_15km") if infra else None
        road_type = infra.get("road_type") if infra else None

        has_road = road_m is not None
        has_power = power_m is not None
        provider = ctx.choice.infrastructure

        if provider == "osm_overpass" and (has_road or has_power):
            status = "complete" if has_road and has_power else "partial"
            confidence = 78.0 if status == "complete" else 55.0
        else:
            status = "fallback"
            confidence = 10.0

        findings: list[str] = []
        risks: list[str] = []
        recs: list[str] = []
        evidence: list[AgentEvidence] = []

        if status == "fallback":
            summary = "Infrastructure data unavailable — road and grid access cannot be assessed."
            risks.append(
                "No OSM infrastructure data returned — road and transmission distances are unknown."
            )
            recs.append(
                "Query OpenStreetMap Overpass API for road and power line proximity before advancing."
            )
            return AgentOutput(
                agentName="Infrastructure",
                status=status,
                confidence=confidence,
                summary=summary,
                findings=findings,
                risks=risks,
                recommendations=recs,
                evidence=evidence,
            )

        # Road access narrative
        if road_m is not None:
            if road_m < 500:
                findings.append(
                    f"Access road within {_fmt_km(road_m)} — construction logistics are straightforward."
                )
                if road_type:
                    findings.append(f"Road type: {road_type}.")
            elif road_m < 5_000:
                findings.append(
                    f"Road access {_fmt_km(road_m)} away — short haul road construction is likely needed."
                )
            elif road_m < 20_000:
                risks.append(
                    f"Road is {_fmt_km(road_m)} away — significant road construction required for component transport."
                )
            else:
                risks.append(
                    f"No road within 20km (nearest: {_fmt_km(road_m)}) — major road infrastructure investment required."
                )
        else:
            risks.append("No road data found in OSM — road access status is uncertain.")

        # Grid / transmission
        if power_m is not None:
            if power_m < 1_000:
                findings.append(
                    f"Transmission line within {_fmt_km(power_m)} — grid interconnection cost is minimal."
                )
            elif power_m < 10_000:
                findings.append(
                    f"Grid {_fmt_km(power_m)} away — medium-voltage connection is typically viable at this distance."
                )
            elif power_m < 50_000:
                risks.append(
                    f"Transmission line {_fmt_km(power_m)} away — dedicated line extension required; significant CAPEX impact."
                )
            else:
                risks.append(
                    f"No transmission line within 50km (nearest: {_fmt_km(power_m)}) — major grid investment or off-grid arrangement needed."
                )
        else:
            risks.append(
                "No OSM-mapped transmission line found in query radius — grid proximity is unknown."
            )

        # Rail hint
        if rail_m is not None and rail_m < 30_000:
            findings.append(
                f"Rail access within {_fmt_km(rail_m)} — potential for oversized component delivery by rail."
            )

        # Summary
        if infra_score is not None:
            if infra_score >= 75:
                summary = "Good infrastructure access — road and grid proximity reduce logistics risk."
            elif infra_score >= 50:
                summary = "Moderate infrastructure access — some road or grid extension will be required."
            else:
                summary = "Poor infrastructure access — significant road and/or grid investment needed."
        else:
            summary = "Infrastructure assessed from OpenStreetMap data — see findings for detail."

        # Evidence
        if road_m is not None:
            evidence.append(AgentEvidence("Nearest road", _fmt_km(road_m), "OpenStreetMap"))
        if power_m is not None:
            evidence.append(AgentEvidence("Nearest transmission line", _fmt_km(power_m), "OpenStreetMap"))
        if rail_m is not None:
            evidence.append(AgentEvidence("Nearest railway", _fmt_km(rail_m), "OpenStreetMap"))
        if settle_count is not None:
            evidence.append(AgentEvidence("Settlements within 15km", str(settle_count), "OpenStreetMap"))
        if road_type:
            evidence.append(AgentEvidence("Nearest road type", road_type, "OpenStreetMap"))
        if infra_score is not None:
            evidence.append(AgentEvidence("Infrastructure score", f"{infra_score:.0f}/100", "CHITTA model"))

        recs.append(
            "Verify OSM road data against satellite imagery and local government records before route planning."
        )
        if power_m is None or (power_m is not None and power_m > 10_000):
            recs.append(
                "Obtain grid operator data on available substation capacity and interconnection requirements."
            )

        return AgentOutput(
            agentName="Infrastructure",
            status=status,
            confidence=confidence,
            summary=summary,
            findings=findings,
            risks=risks,
            recommendations=recs,
            evidence=evidence,
        )
