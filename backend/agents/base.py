"""
BaseAgent — skeleton for all single-LLM-call agent nodes.

Covers the 80 % case: load prompt from state.flow_config, call one LLM slot,
optionally parse structured output, record token usage, return a state dict.

Agents with fan-out calls (researcher) or heavy I/O (intake) stay as plain
functions — they don't fit this pattern and that's fine.

Subclass contract
-----------------
    class MyAgent(BaseAgent):
        prompt_key = "MY_SYSTEM_PROMPT"   # key in state.flow_config
        llm_slot   = "my_slot"            # key in session_agent_config
        schema     = MyOutputModel        # Pydantic model; None = raw AIMessage

        def _build_human_prompt(self, state): ...   # build user-turn content
        def _post_process(self, state, result, urec): ...   # map to state update

Override _build_messages instead of _build_human_prompt when the message list
is not a simple [system + human] pair (e.g. windowed conversation history).
"""

from langchain_core.messages import HumanMessage, SystemMessage

from state import AgentState
from utils.llm_factory import get_llm_for_slot, slot_model
from utils.llm_retry import invoke_with_retry
from utils.pricing import usage_record


class BaseAgent:

    prompt_key: str
    llm_slot:   str
    schema:     type | None = None

    # ── LangGraph node entry point ────────────────────────────────────────────

    def __call__(self, state: AgentState) -> dict:
        llm  = self._build_llm(state)
        msgs = self._build_messages(state)
        raw  = invoke_with_retry(llm, msgs)

        if self.schema:
            result  = raw["parsed"]
            raw_msg = raw.get("raw")
        else:
            result  = raw
            raw_msg = raw

        urec = usage_record(
            self.llm_slot,
            slot_model(self.llm_slot, state.session_agent_config),
            getattr(raw_msg, "usage_metadata", None),
        )
        return self._post_process(state, result, urec)

    # ── Overrideable hooks ────────────────────────────────────────────────────

    def _build_llm(self, state: AgentState):
        llm = get_llm_for_slot(self.llm_slot, state.session_agent_config)
        return llm.with_structured_output(self.schema, include_raw=True) if self.schema else llm

    def _build_messages(self, state: AgentState) -> list:
        return [
            SystemMessage(content=state.flow_config.get(self.prompt_key, "")),
            HumanMessage(content=self._build_human_prompt(state)),
        ]

    def _build_human_prompt(self, state: AgentState) -> str:
        """Build the user-turn content. Override in subclasses."""
        return ""

    def _post_process(self, state: AgentState, result, urec) -> dict:
        """Map the LLM result and usage record to an AgentState update dict."""
        raise NotImplementedError(f"{type(self).__name__} must implement _post_process")
