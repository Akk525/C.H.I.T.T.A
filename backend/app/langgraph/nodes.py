"""
LangGraph node functions for CHITTA historical comparison.

Each node accepts the full GraphState and returns a dict of partial updates.
Nodes are pure functions — all DB access is resolved before graph invocation.
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from app.langgraph.state import GraphState


# ── Node 1: validate loaded payloads ──────────────────────────────────────────

def load_snapshot_node(state: GraphState) -> dict:
    current = state.get("current_run", {})
    previous = state.get("previous_run")
    run_type = state.get("run_type", "unknown")
    warnings: list[str] = list(state.get("warnings", []))

    if not current:
        warnings.append("current_run payload is empty — historical summary may be incomplete.")

    return {
        "current_run": current,
        "previous_run": previous,
        "run_type": run_type,
        "deltas": {},
        "historical_narrative": "",
        "evidence": [],
        "warnings": warnings,
    }


# ── Node 2: compute score/decision deltas ─────────────────────────────────────

def compare_runs_node(state: GraphState) -> dict:
    cur = state["current_run"]
    prev = state["previous_run"] or {}
    deltas: dict = dict(state.get("deltas", {}))

    cur_score = cur.get("totalSuitabilityScore")
    prev_score = prev.get("totalSuitabilityScore")
    score_delta = None
    if cur_score is not None and prev_score is not None:
        score_delta = round(cur_score - prev_score, 2)

    cur_decision = _dig(cur, "agentAnalysis", "coordinator", "finalDecision") or cur.get("finalDecision")
    prev_decision = _dig(prev, "agentAnalysis", "coordinator", "finalDecision") or prev.get("finalDecision")

    cur_ver = _dig(cur, "methodology", "scoringFormulaVersion") or ""
    prev_ver = _dig(prev, "methodology", "scoringFormulaVersion") or ""

    eco_diffs: list[str] = []
    cur_eco = cur.get("economicMetrics", {}) or {}
    prev_eco = prev.get("economicMetrics", {}) or {}
    if cur_eco and prev_eco:
        for key, label in [("lcoeUsdPerMwh", "LCOE"), ("paybackYears", "Payback"), ("economicScore", "Economic score")]:
            cv, pv = cur_eco.get(key), prev_eco.get(key)
            if cv is not None and pv is not None:
                diff = round(cv - pv, 2)
                sign = "+" if diff > 0 else ""
                eco_diffs.append(f"{label}: {sign}{diff}")

    deltas["score"] = {
        "currentScore": cur_score,
        "previousScore": prev_score,
        "delta": score_delta,
        "currentDecision": cur_decision,
        "previousDecision": prev_decision,
        "decisionChanged": cur_decision != prev_decision,
        "formulaVersionChanged": cur_ver != prev_ver,
        "currentFormula": cur_ver,
        "previousFormula": prev_ver,
        "economicDiffs": eco_diffs,
    }

    return {"deltas": deltas}


# ── Node 3: prospecting ranking deltas ────────────────────────────────────────

def ranking_delta_node(state: GraphState) -> dict:
    cur = state["current_run"]
    prev = state["previous_run"] or {}
    deltas: dict = dict(state.get("deltas", {}))
    warnings: list[str] = list(state.get("warnings", []))

    cur_top = cur.get("topCandidates", [])
    prev_top = prev.get("topCandidates", [])

    if not cur_top and not prev_top:
        warnings.append("No top candidate data found for ranking comparison.")
        return {"deltas": deltas, "warnings": warnings}

    cur_map = {c["id"]: c for c in cur_top}
    prev_map = {c["id"]: c for c in prev_top}

    new_in_current = [c["id"] for c in cur_top if c["id"] not in prev_map]
    dropped_from_prev = [c["id"] for c in prev_top if c["id"] not in cur_map]

    score_changes: list[dict] = []
    for cid, cc in cur_map.items():
        if cid in prev_map:
            pc = prev_map[cid]
            cs = cc.get("totalSuitability")
            ps = pc.get("totalSuitability")
            if cs is not None and ps is not None:
                diff = round(cs - ps, 1)
                if abs(diff) >= 1.0:
                    score_changes.append({"id": cid, "delta": diff, "current": cs, "previous": ps})
    score_changes.sort(key=lambda x: abs(x["delta"]), reverse=True)

    deltas["ranking"] = {
        "newCandidateIds": new_in_current[:5],
        "droppedCandidateIds": dropped_from_prev[:5],
        "significantScoreChanges": score_changes[:5],
        "currentCandidateCount": cur.get("candidateCount"),
        "previousCandidateCount": prev.get("candidateCount"),
        "currentEnrichedCount": cur.get("enrichedCount"),
        "previousEnrichedCount": prev.get("enrichedCount"),
    }

    return {"deltas": deltas, "warnings": warnings}


# ── Node 4: simulation config/result deltas ───────────────────────────────────

def simulation_delta_node(state: GraphState) -> dict:
    cur = state["current_run"]
    prev = state["previous_run"] or {}
    deltas: dict = dict(state.get("deltas", {}))
    warnings: list[str] = list(state.get("warnings", []))

    cur_sim = cur.get("simulation") or cur.get("simulationPayload")
    prev_sim = prev.get("simulation") or prev.get("simulationPayload")

    if not cur_sim or not prev_sim:
        warnings.append("Simulation data not present in one or both runs — simulation comparison skipped.")
        deltas["simulation"] = {"available": False}
        return {"deltas": deltas, "warnings": warnings}

    cur_cfg = cur_sim.get("config", {})
    prev_cfg = prev_sim.get("config", {})
    cfg_diffs: list[str] = []
    for key in ["turbineCount", "turbineRatingMw", "electricityPriceUsdPerMwh", "capexUsdPerMw",
                "windWeight", "terrainWeight", "environmentalStrictness", "infrastructurePreference"]:
        cv, pv = cur_cfg.get(key), prev_cfg.get(key)
        if cv != pv and cv is not None and pv is not None:
            cfg_diffs.append(f"{key}: {pv} → {cv}")

    deltas["simulation"] = {
        "available": True,
        "configDiffs": cfg_diffs,
        "currentStrongest": _candidate_label(cur_sim.get("strongestCandidate")),
        "previousStrongest": _candidate_label(prev_sim.get("strongestCandidate")),
        "currentWeakest": _candidate_label(cur_sim.get("weakestCandidate")),
        "previousWeakest": _candidate_label(prev_sim.get("weakestCandidate")),
    }

    return {"deltas": deltas, "warnings": warnings}


# ── Node 5: LLM narrative ─────────────────────────────────────────────────────

async def narrative_delta_node(state: GraphState) -> dict:
    from app.llm import get_provider

    provider = get_provider()
    run_type = state["run_type"]
    deltas = state.get("deltas", {})
    cur_meta = state.get("current_run_meta", {})
    prev_meta = state.get("previous_run_meta") or {}
    has_prev = bool(state.get("previous_run"))

    system_prompt = _build_history_prompt(run_type, has_prev)
    user_payload = {
        "run_type": run_type,
        "has_comparison": has_prev,
        "current_meta": cur_meta,
        "previous_meta": prev_meta,
        "deltas": deltas,
    }
    schema: dict = {}

    try:
        raw = await provider.generate_json(system_prompt, user_payload, schema)
        narrative = raw.get("narrative", "") or _fallback_narrative(deltas, run_type, has_prev)
        evidence = raw.get("evidence", [])
    except Exception as exc:
        narrative = _fallback_narrative(deltas, run_type, has_prev)
        evidence = []
        state["warnings"].append(f"LLM narrative generation failed: {exc!s} — using deterministic fallback.")

    return {"historical_narrative": narrative, "evidence": evidence}


# ── Node 6: assemble final result ─────────────────────────────────────────────

def historical_summary_node(state: GraphState) -> dict:
    return {
        "summary_id": str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dig(d: dict, *keys: str):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k, {}) or {}
    return d if d else None


def _candidate_label(c: dict | None) -> str | None:
    if not c:
        return None
    score = c.get("newTotalSuitability") or c.get("totalSuitability")
    lat, lng = c.get("latitude"), c.get("longitude")
    if lat and lng and score is not None:
        return f"{lat:.3f}, {lng:.3f} (score {score:.1f})"
    return None


def _build_history_prompt(run_type: str, has_comparison: bool) -> str:
    if has_comparison:
        return (
            f"You are a CHITTA historical analysis assistant. Two {run_type} runs are being compared. "
            "Narrate the significant changes between the runs in 2-3 concise sentences. "
            "Focus on score deltas, decision changes, and any notable shifts. "
            "Do not invent data. If no significant change occurred, say so plainly. "
            'Return JSON: {"narrative": "...", "evidence": [{"claim": "...", "field": "..."}]}'
        )
    return (
        f"You are a CHITTA analysis assistant. Summarise this {run_type} run in 2 sentences. "
        "Focus on the headline result and the most important metric. "
        'Return JSON: {"narrative": "...", "evidence": []}'
    )


def _fallback_narrative(deltas: dict, run_type: str, has_comparison: bool) -> str:
    score_d = deltas.get("score", {})
    delta = score_d.get("delta")
    cur_score = score_d.get("currentScore")
    cur_dec = score_d.get("currentDecision", "")

    if not has_comparison:
        return (
            f"This {run_type} run recorded a total suitability score of "
            f"{cur_score:.1f}/100 with a coordinator decision of '{cur_dec}'."
            if cur_score is not None
            else f"This {run_type} run has been saved to history."
        )

    if delta is not None:
        sign = "+" if delta > 0 else ""
        change = "improved" if delta > 0 else ("declined" if delta < 0 else "unchanged")
        narrative = f"Total suitability {change} by {sign}{delta:.1f} pts between the two runs."
    else:
        narrative = f"Both {run_type} runs have been compared."

    dec_changed = score_d.get("decisionChanged", False)
    prev_dec = score_d.get("previousDecision", "")
    if dec_changed and prev_dec and cur_dec:
        narrative += f" The coordinator decision shifted from '{prev_dec}' to '{cur_dec}'."

    return narrative
