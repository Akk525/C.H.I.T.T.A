"""
LangGraph history graph for CHITTA historical comparison and summarisation.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.langgraph.state import GraphState
from app.langgraph.nodes import (
    compare_runs_node,
    historical_summary_node,
    load_snapshot_node,
    narrative_delta_node,
    ranking_delta_node,
    simulation_delta_node,
)


def _should_compare(state: GraphState) -> str:
    return "compare_runs_node" if state.get("previous_run") else "narrative_delta_node"


def _route_after_compare(state: GraphState) -> str:
    return "ranking_delta_node" if state.get("run_type") == "prospecting" else "simulation_delta_node"


def build_history_graph():
    g: StateGraph = StateGraph(GraphState)

    g.add_node("load_snapshot_node", load_snapshot_node)
    g.add_node("compare_runs_node", compare_runs_node)
    g.add_node("ranking_delta_node", ranking_delta_node)
    g.add_node("simulation_delta_node", simulation_delta_node)
    g.add_node("narrative_delta_node", narrative_delta_node)
    g.add_node("historical_summary_node", historical_summary_node)

    g.set_entry_point("load_snapshot_node")

    g.add_conditional_edges(
        "load_snapshot_node",
        _should_compare,
        {
            "compare_runs_node": "compare_runs_node",
            "narrative_delta_node": "narrative_delta_node",
        },
    )

    g.add_conditional_edges(
        "compare_runs_node",
        _route_after_compare,
        {
            "ranking_delta_node": "ranking_delta_node",
            "simulation_delta_node": "simulation_delta_node",
        },
    )

    g.add_edge("ranking_delta_node", "simulation_delta_node")
    g.add_edge("simulation_delta_node", "narrative_delta_node")
    g.add_edge("narrative_delta_node", "historical_summary_node")
    g.add_edge("historical_summary_node", END)

    return g.compile()


history_graph = build_history_graph()
