from __future__ import annotations

from app.agents.base import AgentContext, AgentEvidence, AgentOutput


class WindAgent:
    def run(self, ctx: AgentContext) -> AgentOutput:
        wind_src = (ctx.debug.get("sources") or {}).get("wind") or {}
        raw = wind_src.get("raw") or {}
        dbg = wind_src.get("debug") or {}
        provider = wind_src.get("provider", "unavailable")
        sample_count = int(raw.get("sample_count") or 0)
        mean_speed = raw.get("mean_speed_mps")
        wind_speed_hub = ctx.metrics.get("windSpeedAtHub")
        hub_height = raw.get("hub_height_m") or dbg.get("primary_height_m")
        parameters_used = dbg.get("parametersUsed")
        latest_date = dbg.get("latestCompletedDate")
        days_returned = dbg.get("daysReturned") or sample_count
        wind_score = ctx.wind_score

        # Status
        if provider == "nasa_power" and sample_count >= 100:
            status = "complete"
            confidence = min(85.0, 70.0 + (sample_count / 365.0) * 15.0)
        elif provider == "nasa_power" and sample_count > 0:
            status = "partial"
            confidence = 35.0 + (sample_count / 100.0) * 15.0
        else:
            status = "fallback"
            confidence = 10.0

        findings: list[str] = []
        risks: list[str] = []
        recs: list[str] = []
        evidence: list[AgentEvidence] = []

        if status == "fallback":
            summary = "Wind data unavailable — NASA POWER returned no usable data for this location."
            risks.append(
                "No wind data available — cannot assess resource quality or commercial viability."
            )
            recs.append(
                "Pull 1–3 years of daily wind data from NASA POWER (WS50M / WS100M) once available."
            )
            recs.append(
                "Consider ERA5 reanalysis data as an interim wind climatology source."
            )
        else:
            display_speed = wind_speed_hub or mean_speed
            speed_str = f"{display_speed:.2f} m/s" if display_speed is not None else "unknown"

            if wind_score is not None and wind_score >= 80:
                summary = f"Exceptional wind resource ({speed_str} at {hub_height or '?'}m) — likely IEC Class I threshold."
                findings.append(
                    "Exceptional wind resource — mean speed likely above IEC Class I threshold (≥10 m/s at hub height)."
                )
            elif wind_score is not None and wind_score >= 65:
                summary = f"Strong wind resource ({speed_str} at {hub_height or '?'}m) — commercially viable for most turbine classes."
                findings.append(
                    "Strong wind signal — IEC Class II–III range, commercially viable for most grid-scale turbines."
                )
            elif wind_score is not None and wind_score >= 45:
                summary = f"Moderate wind signal ({speed_str} at {hub_height or '?'}m) — viable with favourable terrain; detailed study needed."
                findings.append(
                    "Moderate wind resource — viable in favourable terrain with detailed climatology."
                )
            else:
                summary = f"Below-threshold wind signal ({speed_str}) — marginal for utility-scale development at this height."
                risks.append(
                    "Wind speed below typical commercial threshold — verify with hub-height extrapolation and long-term data."
                )

            if hub_height and hub_height < 50:
                risks.append(
                    f"Wind data only available at {hub_height}m — hub-height speed likely 30–50% higher; extrapolation needed."
                )
            elif hub_height and hub_height >= 100:
                findings.append(f"100m wind data available — directly relevant to modern turbine hub heights.")

            if status == "partial":
                risks.append(
                    f"Only {sample_count} daily observations available — confidence is limited; full 12-month dataset preferred."
                )

            if wind_speed_hub is not None:
                height_label = f"{hub_height}m" if hub_height else "hub"
                evidence.append(AgentEvidence(f"Mean wind speed ({height_label})", f"{wind_speed_hub:.2f} m/s", "NASA POWER"))
            elif mean_speed is not None:
                evidence.append(AgentEvidence("Mean wind speed (10m)", f"{mean_speed:.2f} m/s", "NASA POWER"))

            if wind_score is not None:
                evidence.append(AgentEvidence("Wind score", f"{wind_score:.0f}/100", "CHITTA model"))
            if parameters_used and parameters_used != "none":
                evidence.append(AgentEvidence("Parameter used", parameters_used, "NASA POWER"))
            elif hub_height:
                evidence.append(AgentEvidence("Data height", f"{hub_height} m", "NASA POWER"))
            if days_returned:
                evidence.append(AgentEvidence("Days returned", str(days_returned), "NASA POWER"))
            if latest_date:
                evidence.append(AgentEvidence("Latest data date", str(latest_date), "NASA POWER"))

            recs.append(
                "Commission a 12-month met mast campaign for a bankable wind resource assessment."
            )
            if status == "partial":
                recs.append(
                    "Cross-check with ERA5 reanalysis to assess long-term wind resource variability."
                )

        return AgentOutput(
            agentName="Wind",
            status=status,
            confidence=round(confidence, 1),
            summary=summary,
            findings=findings,
            risks=risks,
            recommendations=recs,
            evidence=evidence,
        )
