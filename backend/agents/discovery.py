"""
Stage 2 — Dynamic Discovery Agent

Intelligently determines what type of architectural discussion is happening,
then asks ONLY the questions relevant to that type. Does not blindly run
through a Salesforce-specific checklist for every session.
"""

from utils.llm_retry import invoke_with_retry
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from config import MAX_DISCOVERY_QUESTIONS
from utils.llm_factory import get_llm_for_slot, slot_model
from utils.pricing import usage_record
from state import AgentState, DiscoveryQuestion

class DiscoveryOutput(BaseModel):
    next_questions: list[str]        # group of independent questions for this round
    updated_questions: list[DiscoveryQuestion]
    discovery_complete: bool
    reasoning: str

_DISCOVERY_WINDOW = 30

def run_discovery(state: AgentState) -> dict:
    llm = get_llm_for_slot("discovery", state.session_agent_config).with_structured_output(DiscoveryOutput, include_raw=True)

    windowed = list(
        state.messages[-_DISCOVERY_WINDOW:]
        if len(state.messages) > _DISCOVERY_WINDOW
        else state.messages
    )

    # Claude requires conversation to end with a HumanMessage.
    if windowed and isinstance(windowed[-1], AIMessage):
        windowed.append(HumanMessage(content="Please begin the discovery session."))

    messages = [
        SystemMessage(content=state.flow_config.get("DISCOVERY_SYSTEM_PROMPT")),
        *windowed,
    ]

    raw    = invoke_with_retry(llm, messages)
    result: DiscoveryOutput = raw["parsed"]
    urec   = usage_record("discovery", slot_model("discovery", state.session_agent_config), getattr(raw.get("raw"), "usage_metadata", None))

    answered_count = sum(1 for q in result.updated_questions if q.answer)
    cap_reached = answered_count >= MAX_DISCOVERY_QUESTIONS

    if result.discovery_complete or cap_reached or not result.next_questions:
        return {
            "current_stage": "discovery",
            "discovery_questions": result.updated_questions,
            "discovery_complete": True,
            "usage_records": [urec],
        }

    # Interrupt with the full list of questions for this round.
    # Resumes with a list of answer strings (same length, positional).
    answers: list[str] = interrupt(result.next_questions)

    # Pair each answer with its question and add to message history
    qa_lines = "\n".join(
        f"Q{i+1}: {q}\nA{i+1}: {a}"
        for i, (q, a) in enumerate(zip(result.next_questions, answers))
    )

    # Update discovery_questions with the new answers
    answered_map = dict(zip(result.next_questions, answers))
    for q in result.updated_questions:
        if q.question in answered_map and not q.answer:
            q.answer = answered_map[q.question]
            q.satisfied = bool(q.answer.strip())

    return {
        "current_stage": "discovery",
        "discovery_questions": result.updated_questions,
        "discovery_complete": False,
        "usage_records": [urec],
        "messages": [
            AIMessage(name="discovery", content="\n".join(f"{i+1}. {q}" for i, q in enumerate(result.next_questions))),
            HumanMessage(content=qa_lines),
        ],
    }
