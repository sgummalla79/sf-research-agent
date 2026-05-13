"""
Assembles the LangGraph StateGraph.

Two entry paths based on session_type:
  "chat"       → chat node (loops, no structured pipeline)
  "agent_flow" → intake → discovery ⟲ → researcher → reviewer → approver
"""

from langgraph.graph import StateGraph, END

from state import AgentState
from graph.edges import (
    route_entry,
    route_after_intake,
    route_after_discovery,
    route_after_review,
    route_after_approval,
    route_after_chat,
)
from agents.chat import run_chat
from agents.intake import run_intake
from agents.discovery import run_discovery
from agents.researcher import run_researcher
from agents.reviewer import run_reviewer
from agents.approver import run_approver


def build_graph(checkpointer):
    graph = StateGraph(AgentState)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    graph.add_node("router",     lambda s: s)   # passthrough router node
    graph.add_node("chat",       run_chat)
    graph.add_node("intake",     run_intake)
    graph.add_node("discovery",  run_discovery)
    graph.add_node("researcher", run_researcher)
    graph.add_node("reviewer",   run_reviewer)
    graph.add_node("approver",   run_approver)

    # ── Entry: always hits router first ───────────────────────────────────────
    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        route_entry,
        {"chat": "chat", "intake": "intake"},
    )

    # ── Chat loop: keeps running until the stream ends ────────────────────────
    graph.add_conditional_edges(
        "chat",
        route_after_chat,
        {"chat": "chat", "end": END},
    )

    # ── Agent flow pipeline ───────────────────────────────────────────────────
    graph.add_edge("researcher", "reviewer")

    graph.add_conditional_edges(
        "intake",
        route_after_intake,
        {"discovery": "discovery", "end": END},
    )
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
