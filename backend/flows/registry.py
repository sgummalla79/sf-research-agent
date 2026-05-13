"""
Flow Registry — defines all available session types.

Session types:
  chat        — free-form LLM conversation, no pipeline
  agent_flow  — structured LangGraph pipeline with a named flow

Adding a new agent flow:
  1. Create flows/<name>.py with PROMPTS dict
  2. Add an entry to FLOWS below
  No other code changes needed.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class FlowConfig:
    id:          str
    name:        str
    description: str
    icon:        str
    prompts:     dict[str, str] = field(default_factory=dict)


# ── Agent flow registry ───────────────────────────────────────────────────────

def _load_flows() -> dict[str, FlowConfig]:
    from flows.architect import PROMPTS as ARCHITECT_PROMPTS
    return {
        "architect": FlowConfig(
            id="architect",
            name="Architect Engagement",
            description="Formal Salesforce Architecture Recommendation Document via a "
                        "5-stage pipeline: intake → discovery → research → review → approval.",
            icon="⚡",
            prompts=ARCHITECT_PROMPTS,
        ),
    }


def get_all_flows() -> dict[str, FlowConfig]:
    return _load_flows()


def get_flow(flow_id: str) -> FlowConfig:
    flows = _load_flows()
    if flow_id not in flows:
        raise ValueError(f"Unknown agent flow: {flow_id!r}")
    return flows[flow_id]


# ── Chat model curated list ───────────────────────────────────────────────────
# Only Claude models are offered for free-form chat.
# Default is Sonnet 4.6 — the best balance of capability and speed.

CHAT_MODELS: list[dict] = [
    {
        "model":       "claude-opus-4-7",
        "display":     "Opus 4.7",
        "description": "Most capable for ambitious work",
    },
    {
        "model":       "claude-sonnet-4-6",
        "display":     "Sonnet 4.6",
        "description": "Responsive everyday work",
        "default":     True,
    },
    {
        "model":       "claude-haiku-4-5-20251001",
        "display":     "Haiku 4.5",
        "description": "Fastest, most efficient",
    },
]

CHAT_DEFAULT_MODEL = "claude-sonnet-4-6"
