from __future__ import annotations

from app.agents.base import AgentContext, AgentEvidence, AgentOutput


class TerrainAgent:
    def run(self, ctx: AgentContext) -> AgentOutput:
        elev_src = (ctx.debug.get("sources") or {}).get("elevation") or {}
        provider = elev_src.get("provider", "unavailable")

        terrain_score = ctx.terrain_score
        complexity = ctx.metrics.get("terrainComplexity")
        elevation_m = ctx.metrics.get("elevationM")
        slope_pct = ctx.metrics.get("slopePct")
        ridge_score = ctx.metrics.get("ridgeScore")

        if provider == "opentopodata":
            status = "complete"
            confidence = 80.0
        else:
            status = "fallback"
            confidence = 10.0

        findings: list[str] = []
        risks: list[str] = []
        recs: list[str] = []
        evidence: list[AgentEvidence] = []

        if status == "fallback":
            summary = "Elevation data unavailable — terrain buildability cannot be assessed."
            risks.append(
                "No elevation data — slope, terrain complexity, and construction feasibility are unknown."
            )
            recs.append(
                "Fetch SRTM or Copernicus DEM tiles for the site and compute slope and roughness."
            )
            return AgentOutput(
                agentName="Terrain",
                status=status,
                confidence=confidence,
                summary=summary,
                findings=findings,
                risks=risks,
                recommendations=recs,
                evidence=evidence,
            )

        # Complexity narrative
        if complexity is not None:
            if complexity < 0.4:
                findings.append(
                    "Flat to gently rolling terrain — civil works costs are likely minimal."
                )
            elif complexity < 0.8:
                findings.append(
                    "Moderate terrain complexity — standard access road grading needed; foundations are conventional."
                )
            elif complexity < 1.4:
                risks.append(
                    "Complex terrain — turbulence risk is elevated; detailed micrositing and TI measurement required."
                )
            else:
                risks.append(
                    "Highly complex terrain — turbulence intensity likely IEC Category A or above; advanced flow modelling required."
                )

        # Slope narrative
        if slope_pct is not None:
            if slope_pct < 5.0:
                findings.append(
                    f"Gentle slope ({slope_pct:.1f}%) — crane access and component transport are straightforward."
                )
            elif slope_pct < 15.0:
                findings.append(
                    f"Moderate slope ({slope_pct:.1f}%) — road engineering and crane outrigger pads required."
                )
            else:
                risks.append(
                    f"Steep terrain ({slope_pct:.1f}% slope) — may constrain equipment access and foundation viability."
                )

        # Ridge score
        if ridge_score is not None:
            if ridge_score > 0.6:
                risks.append(
                    "Significant elevation transitions detected — potential for speed-up effects and turbulent wakes."
                )
            elif ridge_score > 0.3:
                findings.append(
                    "Moderate terrain variability — minor flow distortion expected; standard TI assessment sufficient."
                )
            else:
                findings.append(
                    "Smooth elevation gradient — minimal flow distortion expected."
                )

        # Summary
        if terrain_score is not None:
            if terrain_score >= 75:
                summary = "Favourable terrain — low complexity and slope suggest straightforward civil works."
            elif terrain_score >= 55:
                summary = "Moderate terrain — standard road engineering required; no major constraints detected."
            else:
                summary = "Challenging terrain — complexity or slope will increase civil works cost and timeline."
        else:
            summary = "Terrain assessed from elevation samples — see findings for detail."

        # Evidence
        if elevation_m is not None:
            evidence.append(AgentEvidence("Site elevation", f"{elevation_m:.0f} m", "OpenTopoData (SRTM90m)"))
        if complexity is not None:
            evidence.append(AgentEvidence("Terrain complexity index", f"{complexity:.3f}", "CHITTA model"))
        if slope_pct is not None:
            evidence.append(AgentEvidence("Approximate slope", f"{slope_pct:.1f}%", "CHITTA model"))
        if ridge_score is not None:
            evidence.append(AgentEvidence("Ridge transition score", f"{ridge_score:.3f}", "CHITTA model"))
        if terrain_score is not None:
            evidence.append(AgentEvidence("Terrain score", f"{terrain_score:.0f}/100", "CHITTA model"))

        recs.append(
            "Obtain high-resolution DEM (≤30m) and recompute slope and roughness for detailed micrositing."
        )
        if complexity is not None and complexity >= 0.8:
            recs.append(
                "Commission a computational fluid dynamics (CFD) or non-linear flow model for turbulence assessment."
            )

        return AgentOutput(
            agentName="Terrain",
            status=status,
            confidence=confidence,
            summary=summary,
            findings=findings,
            risks=risks,
            recommendations=recs,
            evidence=evidence,
        )
