"""
Stage 2 — Dynamic Discovery Agent

Intelligently determines what type of architectural discussion is happening,
then asks ONLY the questions relevant to that type. Does not blindly run
through a Salesforce-specific checklist for every session.

Overrides _build_messages (windowed conversation history instead of a single
human turn) and _post_process (LangGraph interrupt loop for Q&A rounds).
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from agents.base import BaseAgent
from config import MAX_DISCOVERY_QUESTIONS
from state import AgentState, DiscoveryQuestion


class DiscoveryOutput(BaseModel):
    next_questions:     list[str]
    updated_questions:  list[DiscoveryQuestion]
    discovery_complete: bool
    reasoning:          str


class DiscoveryAgent(BaseAgent):
    prompt_key = "DISCOVERY_SYSTEM_PROMPT"
    llm_slot   = "discovery"
    schema     = DiscoveryOutput

    _WINDOW = 30

    def _build_messages(self, state: AgentState) -> list:
        windowed = (
            state.messages[-self._WINDOW:]
            if len(state.messages) > self._WINDOW
            else state.messages
        )
        # Claude requires conversation to end with a HumanMessage
        if windowed and isinstance(windowed[-1], AIMessage):
            windowed = [*windowed, HumanMessage(content="Please begin the discovery session.")]
        return [
            SystemMessage(content=state.flow_config.get(self.prompt_key, "")),
            *windowed,
        ]

    def _post_process(self, state: AgentState, result: DiscoveryOutput, urec) -> dict:
        answered_count = sum(1 for q in result.updated_questions if q.answer)
        cap_reached    = answered_count >= MAX_DISCOVERY_QUESTIONS

        if result.discovery_complete or cap_reached or not result.next_questions:
            return {
                "current_stage":       "discovery",
                "discovery_questions": result.updated_questions,
                "discovery_complete":  True,
                "usage_records":       [urec],
            }

        # Suspend and wait for user answers; resumes with a list of strings
        answers: list[str] = interrupt(result.next_questions)

        # Pair each answer back into the question objects
        answered_map = dict(zip(result.next_questions, answers))
        for q in result.updated_questions:
            if q.question in answered_map and not q.answer:
                q.answer    = answered_map[q.question]
                q.satisfied = bool(q.answer.strip())

        qa_lines = "\n".join(
            f"Q{i+1}: {q}\nA{i+1}: {a}"
            for i, (q, a) in enumerate(zip(result.next_questions, answers))
        )

        return {
            "current_stage":       "discovery",
            "discovery_questions": result.updated_questions,
            "discovery_complete":  False,
            "usage_records":       [urec],
            "messages": [
                AIMessage(
                    name="discovery",
                    content="\n".join(f"{i+1}. {q}" for i, q in enumerate(result.next_questions)),
                ),
                HumanMessage(content=qa_lines),
            ],
        }


run_discovery = DiscoveryAgent()
