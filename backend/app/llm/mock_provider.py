"""
Deterministic mock LLM provider.

Generates structured synthesis from evidence packets without any external API call.
Used when CHITTA_LLM_PROVIDER=mock (default) or when no API key is available.
"""
from __future__ import annotations

from .base import LLMProvider


class MockProvider(LLMProvider):
    model = "mock-deterministic-v1"

    async def generate_json(
        self,
        system_prompt: str,
        user_payload: dict,
        schema: dict,
    ) -> dict:
        evidence_list: list[dict] = user_payload.get("evidence", [])
        mode: str = user_payload.get("mode", "site")

        ev: dict[str, dict] = {e["evidenceId"]: e for e in evidence_list}

        def val(eid: str, default: str = "N/A") -> str:
            p = ev.get(eid)
            return p["value"] if p and p.get("value") else default

        total_score = val("score:total_suitability")
        decision = val("score:decision", "mixed")
        wind_score = val("wind:score")
        wind_speed = val("wind:speed_at_hub")
        terrain_score = val("terrain:score")
        infra_score = val("infra:score")
        env_score = val("env:score")
        pop_score = val("social:population_score")
        land_cover = val("env:land_cover", "")
        pa_risk = val("env:protected_area_risk", "unknown")
        nearest_road = val("infra:nearest_road", "")
        nearest_power = val("infra:nearest_powerline", "")
        lcoe = val("economic:lcoe", "")
        payback = val("economic:payback", "")
        cf = val("economic:capacity_factor", "")
        candidate_count = val("prospecting:candidate_count", "")
        enriched_count = val("prospecting:enriched_count", "")
        region_name = val("prospecting:region", "")
        strongest_id = val("sim:strongest_candidate", "")
        ranking_note = val("sim:ranking_changes", "")

        # ── Strongest signals ──────────────────────────────────────────────────
        strongest_signals: list[str] = []
        major_risks: list[str] = []

        def _try_float(s: str) -> float | None:
            try:
                return float(s)
            except (ValueError, TypeError):
                return None

        ws_f = _try_float(wind_score)
        if ws_f is not None:
            if ws_f >= 70:
                strongest_signals.append(f"Strong wind resource — score {wind_score}/100")
            elif ws_f < 45:
                major_risks.append(f"Weak wind resource — score {wind_score}/100")

        ts_f = _try_float(terrain_score)
        if ts_f is not None:
            if ts_f >= 70:
                strongest_signals.append(f"Favourable terrain for construction — score {terrain_score}/100")
            elif ts_f < 45:
                major_risks.append(f"Challenging terrain — score {terrain_score}/100")

        ifs_f = _try_float(infra_score)
        if ifs_f is not None:
            if ifs_f >= 70:
                strongest_signals.append(f"Good infrastructure access — score {infra_score}/100")
            elif ifs_f < 45:
                major_risks.append(f"Limited infrastructure access — score {infra_score}/100")

        lcoe_f = _try_float(lcoe)
        if lcoe_f is not None:
            if lcoe_f < 60:
                strongest_signals.append(f"Competitive estimated LCOE of ${lcoe_f:.0f}/MWh")
            elif lcoe_f > 100:
                major_risks.append(f"Elevated estimated LCOE of ${lcoe_f:.0f}/MWh — project economics are marginal")

        if pa_risk.lower() == "high":
            major_risks.append("Site is in or near a protected area — environmental permits may face significant constraints")

        if not strongest_signals:
            strongest_signals.append("Screening data is limited — no strong positive signals identified from available evidence")
        if not major_risks:
            major_risks.append("No major risk flags identified in deterministic screening — detailed field validation still required")

        # ── Executive summary ──────────────────────────────────────────────────
        decision_label = {
            "promising": "strong candidate",
            "mixed": "moderate candidate with material tradeoffs",
            "caution": "candidate requiring caution",
            "poor": "unsuitable location based on current evidence",
        }.get(decision.lower(), "candidate")

        summary_parts = []
        if mode == "prospecting" and candidate_count:
            summary_parts.append(
                f"Prospecting across {region_name or 'the specified region'} screened {candidate_count} candidate sites, "
                f"of which {enriched_count} received full enriched analysis."
            )
            summary_parts.append(
                "Top candidates and cluster zones are summarised below based on deterministic CHITTA scoring."
            )
        elif mode == "simulation":
            summary_parts.append(
                "Scenario simulation recomputed suitability and economic metrics across all candidate sites "
                "using user-configured weights and assumptions."
            )
            if strongest_id:
                summary_parts.append(f"The strongest candidate post-simulation is at {strongest_id}.")
            if ranking_note:
                summary_parts.append(ranking_note)
        else:
            summary_parts.append(
                f"This site is assessed as a {decision_label} for wind energy development, "
                f"with a total suitability score of {total_score}/100."
            )
            if wind_speed and wind_speed != "N/A":
                summary_parts.append(f"Hub-height wind speed is {wind_speed} m/s.")
            if lcoe and payback:
                summary_parts.append(
                    f"Under standard project assumptions, the estimated LCOE is ${lcoe}/MWh "
                    f"with a payback period of {payback} years."
                )

        exec_summary = " ".join(summary_parts)

        # ── Strategic assessment ───────────────────────────────────────────────
        if mode == "site":
            strategic = (
                f"Total suitability: {total_score}/100. "
                f"Primary score drivers: wind {wind_score}, terrain {terrain_score}, "
                f"infrastructure {infra_score}, environment {env_score}, population {pop_score}. "
                f"Coordinator decision: {decision}."
            )
        elif mode == "prospecting":
            strategic = (
                f"Regional screening identified {candidate_count} candidates across {region_name or 'the region'}. "
                f"Cluster analysis surfaced the most promising sub-zones. "
                "CHITTA's two-pass engine enriched top sites with wind, terrain, infrastructure, and economic data."
            )
        else:
            strategic = (
                "Simulation results reflect recomputed scores under the configured weight and economic parameters. "
                "Ranking changes identify which candidates are most sensitive to scenario assumptions."
            )

        # ── Narratives ─────────────────────────────────────────────────────────
        if lcoe and cf:
            eco_narrative = (
                f"With a capacity factor of {cf} and an estimated LCOE of ${lcoe}/MWh, "
                f"the economic case {'is competitive at current tariff assumptions' if (lcoe_f or 999) < 60 else 'requires careful evaluation given elevated generation costs'}. "
                f"Payback is estimated at {payback} years under the assumed project parameters."
            )
        elif mode == "simulation":
            eco_narrative = (
                "Economic metrics were recomputed under the simulation's turbine count, capacity factor, "
                "electricity price, and CAPEX assumptions. Individual candidate economics are listed in the evidence packets."
            )
        else:
            eco_narrative = (
                "Economic feasibility data is limited for this site. "
                "A dedicated wind resource campaign is required before project economics can be reliably modelled."
            )

        if nearest_road or nearest_power:
            road_str = f"nearest road is {float(nearest_road)/1000:.1f} km away" if nearest_road else ""
            power_str = f"nearest powerline is {float(nearest_power)/1000:.1f} km away" if nearest_power else ""
            parts = [p for p in [road_str, power_str] if p]
            infra_narrative = (
                f"Infrastructure proximity: {', '.join(parts)}. "
                f"Infrastructure score: {infra_score}/100."
            )
        else:
            infra_narrative = (
                f"Infrastructure score: {infra_score}/100. "
                "Detailed road and grid access data was not available from OpenStreetMap at time of analysis."
            )

        env_parts = []
        if land_cover:
            env_parts.append(f"land cover is classified as '{land_cover}'")
        if pa_risk and pa_risk != "N/A":
            env_parts.append(f"protected area risk assessed as '{pa_risk}'")
        if env_parts:
            env_narrative = (
                f"Environmental profile: {', '.join(env_parts)}. "
                f"Environmental score: {env_score}/100."
            )
        else:
            env_narrative = (
                f"Environmental score: {env_score}/100. "
                "Full land cover and protected area analysis is recommended before project advancement."
            )

        # ── Recommendations ────────────────────────────────────────────────────
        recs: list[str] = []
        if decision.lower() in ("promising", "mixed"):
            recs.append("Commission a 12-month on-site wind resource measurement campaign to validate screening results.")
        if ifs_f is not None and ifs_f < 60:
            recs.append("Assess grid connection cost and road access improvement requirements before advancing to feasibility.")
        if pa_risk.lower() in ("medium", "high"):
            recs.append("Conduct an Environmental Impact Assessment to clarify protected area and biodiversity constraints.")
        if lcoe_f is not None and lcoe_f > 80:
            recs.append("Explore CAPEX reduction pathways or higher-resource micro-siting within the region before committing.")
        if mode == "prospecting":
            recs.append("Prioritise full site-level analysis for top-ranked enriched candidates before field visits.")
        if not recs:
            recs.append("Conduct a full pre-feasibility study to validate CHITTA's deterministic screening results with ground truth data.")

        # ── Warnings ──────────────────────────────────────────────────────────
        warnings_list = [
            "AI-generated narrative from deterministic CHITTA analysis. "
            "All claims are derived solely from evidence packets — no additional data sources were consulted."
        ]
        if total_score == "N/A" and mode == "site":
            warnings_list.append("Total suitability score unavailable — wind or terrain data may be missing.")

        # ── Citations ──────────────────────────────────────────────────────────
        used_ids: list[str] = [e["evidenceId"] for e in evidence_list]
        citations: list[dict] = []

        if mode == "site" and total_score != "N/A":
            core_ids = [eid for eid in ["score:total_suitability", "score:decision"] if eid in ev]
            if core_ids:
                citations.append({
                    "claim": f"Total suitability score of {total_score}/100 — coordinator decision: {decision}",
                    "evidenceIds": core_ids,
                })
        if wind_speed and wind_speed not in ("N/A", ""):
            ws_ids = [eid for eid in ["wind:speed_at_hub", "wind:score"] if eid in ev]
            if ws_ids:
                citations.append({
                    "claim": f"Hub-height wind speed {wind_speed} m/s, wind score {wind_score}/100",
                    "evidenceIds": ws_ids,
                })
        if lcoe and lcoe != "N/A":
            eco_ids = [eid for eid in ["economic:lcoe", "economic:payback", "economic:capacity_factor"] if eid in ev]
            if eco_ids:
                citations.append({
                    "claim": f"LCOE ${lcoe}/MWh, payback {payback} years, capacity factor {cf}",
                    "evidenceIds": eco_ids,
                })
        if env_parts:
            env_ids = [eid for eid in ["env:land_cover", "env:protected_area_risk", "env:score"] if eid in ev]
            if env_ids:
                citations.append({
                    "claim": f"Environmental: {', '.join(env_parts)}",
                    "evidenceIds": env_ids,
                })

        return {
            "executiveSummary": exec_summary,
            "strategicAssessment": strategic,
            "strongestSignals": strongest_signals,
            "majorRisks": major_risks,
            "economicNarrative": eco_narrative,
            "infrastructureNarrative": infra_narrative,
            "environmentalNarrative": env_narrative,
            "recommendations": recs,
            "warnings": warnings_list,
            "citations": citations,
            "generatedFromEvidenceIds": used_ids,
        }
