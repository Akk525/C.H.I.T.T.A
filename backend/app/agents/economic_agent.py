from __future__ import annotations

from app.agents.base import AgentContext, AgentEvidence, AgentOutput


def _fmt_usd(v: float) -> str:
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.0f}k"
    return f"${v:.0f}"


class EconomicAgent:
    def run(self, ctx: AgentContext) -> AgentOutput:
        eco = ctx.economic_metrics
        wind_real = ctx.choice.wind not in {"unavailable", "mock"}
        terrain_real = ctx.choice.elevation not in {"unavailable", "mock"}

        if eco is None:
            return AgentOutput(
                agentName="Economic",
                status="fallback",
                confidence=10.0,
                summary="Economic metrics unavailable — wind and terrain data required for feasibility estimate.",
                risks=["No economic estimate could be computed — insufficient site data."],
                recommendations=["Obtain wind and terrain data before conducting economic screening."],
            )

        # Status
        if wind_real and terrain_real:
            status = "complete"
            confidence = 72.0
        elif wind_real or terrain_real:
            status = "partial"
            confidence = 45.0
        else:
            status = "partial"
            confidence = 25.0

        cf = eco.capacity_factor
        lcoe = eco.lcoe_usd_per_mwh
        payback = eco.payback_years
        aep = eco.annual_energy_mwh
        capex = eco.capex_usd
        revenue = eco.annual_revenue_usd
        eco_score = eco.economic_score
        asmp = eco.assumptions

        findings: list[str] = []
        risks: list[str] = []
        recs: list[str] = []

        # Capacity factor narrative
        if cf >= 0.40:
            findings.append(f"High capacity factor ({cf:.0%}) — excellent wind energy conversion.")
        elif cf >= 0.30:
            findings.append(f"Good capacity factor ({cf:.0%}) — commercially standard for onshore wind.")
        elif cf >= 0.20:
            findings.append(f"Moderate capacity factor ({cf:.0%}) — acceptable in some markets but not class-leading.")
        else:
            risks.append(f"Low capacity factor ({cf:.0%}) — below typical commercial viability threshold.")

        # LCOE narrative
        if lcoe < 45:
            findings.append(f"Strong LCOE (${lcoe:.0f}/MWh) — competitive with incumbent generation in most markets.")
        elif lcoe < 60:
            findings.append(f"Viable LCOE (${lcoe:.0f}/MWh) — within typical onshore wind market range.")
        elif lcoe < 75:
            risks.append(f"Elevated LCOE (${lcoe:.0f}/MWh) — sensitive to electricity price assumptions.")
        else:
            risks.append(f"High LCOE (${lcoe:.0f}/MWh) — exceeds typical onshore wind benchmarks; viability uncertain.")

        # Payback narrative
        if payback is None:
            risks.append("Payback period cannot be confirmed — revenue does not exceed operating costs at current assumptions.")
        elif payback <= 10:
            findings.append(f"Short payback period ({payback:.1f} years) — strong return profile.")
        elif payback <= 15:
            findings.append(f"Standard payback period ({payback:.1f} years) — typical for onshore wind development.")
        elif payback <= 20:
            risks.append(f"Long payback period ({payback:.1f} years) — sensitive to electricity price and financing cost.")
        else:
            risks.append(f"Extended payback ({payback:.1f} years) — economics are marginal at current assumptions.")

        # Wind availability flag
        if not eco.wind_available:
            risks.append("Wind data unavailable — capacity factor assumed at conservative 22%; all figures are highly uncertain.")

        # Summary
        if eco_score >= 70:
            summary = f"Viable preliminary economics — estimated LCOE ${lcoe:.0f}/MWh, CF {cf:.0%}, payback {payback:.0f}yr." if payback else f"Viable preliminary economics — LCOE ${lcoe:.0f}/MWh, CF {cf:.0%}."
        elif eco_score >= 45:
            summary = f"Marginal economics — LCOE ${lcoe:.0f}/MWh at {cf:.0%} CF; sensitivity to price and CAPEX is high."
        else:
            summary = f"Challenging economics at current assumptions — LCOE ${lcoe:.0f}/MWh, CF {cf:.0%}. Consider richer wind data before advancing."

        # Recommendations
        recs.append(
            "Commission a bankable wind resource assessment (met mast or satellite-derived) before financial modelling."
        )
        recs.append(
            f"Verify CAPEX estimate with a developer-grade EPC quotation (current basis: ${asmp.capex_usd_per_mw / 1e6:.1f}M/MW)."
        )
        if lcoe > 60:
            recs.append(
                f"Assess local offtake pricing — current assumed electricity price (${asmp.electricity_price_usd_per_mwh}/MWh) drives viability."
            )

        # Evidence
        evidence = [
            AgentEvidence("Capacity factor", f"{cf:.1%}", "CHITTA model"),
            AgentEvidence("Annual energy (AEP)", f"{aep:,.0f} MWh/yr", "CHITTA model"),
            AgentEvidence("CAPEX estimate", _fmt_usd(capex), "CHITTA model"),
            AgentEvidence("OPEX/yr estimate", _fmt_usd(eco.opex_usd_per_year), "CHITTA model"),
            AgentEvidence("Annual revenue", _fmt_usd(revenue), "CHITTA model"),
            AgentEvidence("LCOE", f"${lcoe:.1f}/MWh", "CHITTA model"),
            AgentEvidence("Payback (simple)", f"{payback:.1f} yr" if payback else "N/A", "CHITTA model"),
            AgentEvidence("Electricity price assumed", f"${asmp.electricity_price_usd_per_mwh}/MWh", "CHITTA assumptions"),
            AgentEvidence("Turbines assumed", f"{asmp.turbine_count} × {asmp.turbine_rating_mw}MW", "CHITTA assumptions"),
        ]

        risks.insert(0, "Preliminary estimate only — see limitations for accuracy bounds.")

        return AgentOutput(
            agentName="Economic",
            status=status,
            confidence=round(confidence, 1),
            summary=summary,
            findings=findings,
            risks=risks,
            recommendations=recs,
            evidence=evidence,
        )
