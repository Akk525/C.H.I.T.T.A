from __future__ import annotations

from typing import TypedDict


class GraphState(TypedDict):
    current_run: dict            # Full SavedRun payload
    current_run_meta: dict       # id, run_type, label, created_at, scores
    previous_run: dict | None    # Previous run payload (None = single-run summary)
    previous_run_meta: dict | None
    run_type: str
    deltas: dict                 # Score/decision/ranking diffs
    historical_narrative: str    # LLM-generated narrative
    evidence: list[dict]         # Evidence packets for the narrative
    warnings: list[str]
    summary_id: str
    generated_at: str
