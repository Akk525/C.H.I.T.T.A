from __future__ import annotations

from app.agents.base import AgentContext, AgentEvidence, AgentOutput


def _fmt_km(m: float | None) -> str:
    if m is None:
        return "unknown"
    return f"{m / 1000:.1f} km" if m >= 1000 else f"{m:.0f} m"


class SocialAgent:
    def run(self, ctx: AgentContext) -> AgentOutput:
        infra = ctx.enriched.get("infrastructure")
        settle_count = infra.get("settlement_count_15km") if infra else None
        nearest_settle_m = infra.get("nearest_settlement_m") if infra else None
        pop_score = ctx.pop_score
        provider = ctx.choice.infrastructure

        if provider == "osm_overpass" and settle_count is not None:
            status = "complete"
            confidence = 70.0
        else:
            status = "fallback"
            confidence = 10.0

        findings: list[str] = []
        risks: list[str] = []
        recs: list[str] = []
        evidence: list[AgentEvidence] = []

        if status == "fallback":
            summary = "Settlement data unavailable — social impact and permitting friction cannot be assessed."
            risks.append(
                "No settlement count data — noise and visual impact constraints are unknown."
            )
            recs.append(
                "Query OpenStreetMap for settlement nodes and cross-reference with national population data."
            )
            return AgentOutput(
                agentName="Social",
                status=status,
                confidence=confidence,
                summary=summary,
                findings=findings,
                risks=risks,
                recommendations=recs,
                evidence=evidence,
            )

        # Settlement count narrative
        if settle_count == 0:
            findings.append(
                "No mapped settlements within 15km — minimal noise, shadow flicker, and visual impact constraints."
            )
            summary = "Remote site with no settlements within 15km — social impact risk is low."
        elif settle_count <= 2:
            findings.append(
                f"{settle_count} settlement(s) within 15km — standard community consultation and noise assessment is likely sufficient."
            )
            summary = f"Low settlement density ({settle_count} within 15km) — permitting friction is manageable."
        elif settle_count <= 5:
            risks.append(
                f"{settle_count} settlements within 15km — detailed noise, shadow flicker, and visual impact assessment required."
            )
            summary = f"Moderate settlement density ({settle_count} within 15km) — permitting will require environmental noise assessment."
        elif settle_count <= 10:
            risks.append(
                f"{settle_count} settlements within 15km — full social impact study and stakeholder engagement plan is required."
            )
            summary = f"High settlement density ({settle_count} within 15km) — social impact study and community engagement are critical."
        else:
            risks.append(
                f"{settle_count} settlements within 15km — permitting complexity is significantly elevated; community opposition risk is high."
            )
            summary = f"Very high settlement density ({settle_count} within 15km) — development timeline risk is elevated."

        # Nearest settlement distance
        if nearest_settle_m is not None:
            if nearest_settle_m < 2_000:
                risks.append(
                    f"Nearest settlement is only {_fmt_km(nearest_settle_m)} away — setback distances must be carefully evaluated."
                )
            elif nearest_settle_m < 5_000:
                findings.append(
                    f"Nearest settlement at {_fmt_km(nearest_settle_m)} — within standard noise and visual impact study radius."
                )
            else:
                findings.append(
                    f"Nearest settlement {_fmt_km(nearest_settle_m)} away — outside typical noise setback zone for most turbine classes."
                )

        # Evidence
        evidence.append(AgentEvidence("Settlements within 15km", str(settle_count), "OpenStreetMap"))
        if nearest_settle_m is not None:
            evidence.append(AgentEvidence("Nearest settlement", _fmt_km(nearest_settle_m), "OpenStreetMap"))
        if pop_score is not None:
            evidence.append(AgentEvidence("Population/social score", f"{pop_score:.0f}/100", "CHITTA model"))

        # Recommendations
        if settle_count > 0:
            recs.append(
                "Commission a noise and shadow flicker assessment compliant with relevant national wind energy guidelines."
            )
        if settle_count > 5:
            recs.append(
                "Develop a community engagement plan and consider a community benefit fund to manage social acceptance risk."
            )
        recs.append(
            "Verify settlement data against national census and local government planning records."
        )

        return AgentOutput(
            agentName="Social",
            status=status,
            confidence=confidence,
            summary=summary,
            findings=findings,
            risks=risks,
            recommendations=recs,
            evidence=evidence,
        )
