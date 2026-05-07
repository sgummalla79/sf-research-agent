"""
Assembles the LangGraph StateGraph.

Flow:
  intake → discovery ⟲ (interrupt on each question) → researcher → reviewer → approver
                                ↑_________________________| (review failed)
                                ↑_________________________________| (approval rejected)
"""

from langgraph.graph import StateGraph, END

from state import AgentState
from graph.edges import route_after_intake, route_after_discovery, route_after_review, route_after_approval

from agents.intake import run_intake
from agents.discovery import run_discovery
from agents.researcher import run_researcher
from agents.reviewer import run_reviewer
from agents.approver import run_approver


def build_graph(checkpointer):
    """
    Accepts either a sync PostgresSaver or async AsyncPostgresSaver —
    LangGraph handles both transparently.
    """
    graph = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("intake",     run_intake)
    graph.add_node("discovery",  run_discovery)
    graph.add_node("researcher", run_researcher)
    graph.add_node("reviewer",   run_reviewer)
    graph.add_node("approver",   run_approver)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.set_entry_point("intake")

    # ── Linear edges ──────────────────────────────────────────────────────────
    graph.add_edge("researcher", "reviewer")

    # ── Intake gate: invalid image → END, everything else → discovery ─────────
    graph.add_conditional_edges(
        "intake",
        route_after_intake,
        {"discovery": "discovery", "end": END},
    )

    # ── Conditional edges ─────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "discovery",
        route_after_discovery,
        {"discovery": "discovery", "researcher": "researcher"},
    )

    graph.add_conditional_edges(
        "reviewer",
        route_after_review,
        {"approver": "approver", "researcher": "researcher"},
    )

    graph.add_conditional_edges(
        "approver",
        route_after_approval,
        {"complete": END, "halted": END, "researcher": "researcher"},
    )

    return graph.compile(checkpointer=checkpointer)
