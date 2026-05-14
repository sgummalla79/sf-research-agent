"""
Chat Agent — free-form LLM conversation node.

Used when session_type == "chat". No structured pipeline, no interrupts.
Just maintains conversation history and streams responses back.

Supports Anthropic Extended Thinking when state.extended_thinking is True.
"""

import logging
from langchain_core.messages import AIMessage

from state import AgentState
from utils.pricing import usage_record

logger = logging.getLogger(__name__)

# Budget tokens for extended thinking — how much the model can reason before responding
THINKING_BUDGET = 10_000


def run_chat(state: AgentState) -> dict:
    """Single-node free-form chat. Reads conversation history from state.messages."""
    model   = state.chat_model or "claude-sonnet-4-6"
    thinking = state.extended_thinking

    if thinking:
        return _run_with_thinking(state, model)
    else:
        return _run_standard(state, model)


def _run_standard(state: AgentState, model: str) -> dict:
    from utils.llm_factory import build_llm
    from utils.llm_retry import invoke_with_retry

    provider = state.chat_provider or "anthropic"
    llm      = build_llm(provider, model)
    response = invoke_with_retry(llm, list(state.messages))
    urec     = usage_record("chat", model, getattr(response, "usage_metadata", None))

    return {
        "current_stage": "chat",
        "usage_records": [urec],
        "messages":      [AIMessage(name="chat", content=response.content)],
    }


def _run_with_thinking(state: AgentState, model: str) -> dict:
    """Extended Thinking via Anthropic SDK directly (LangChain doesn't support it yet)."""
    import anthropic
    from utils.api_keys import get_key
    from utils.pricing import usage_record

    client = anthropic.Anthropic(api_key=get_key("anthropic"))

    # Convert LangChain messages to Anthropic API format
    api_messages = []
    for msg in state.messages:
        role    = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        if content.strip():
            api_messages.append({"role": role, "content": content})

    if not api_messages:
        api_messages = [{"role": "user", "content": "Hello"}]

    response = client.messages.create(
        model=model,
        max_tokens=16_000,
        thinking={"type": "enabled", "budget_tokens": THINKING_BUDGET},
        messages=api_messages,
    )

    # Extract text content (skip thinking blocks)
    text = " ".join(
        block.text for block in response.content
        if hasattr(block, "text")
    )

    urec = usage_record(
        "chat", model,
        {"input_token_count": response.usage.input_tokens,
         "output_token_count": response.usage.output_tokens},
    )

    return {
        "current_stage": "chat",
        "usage_records": [urec],
        "messages":      [AIMessage(name="chat", content=text)],
    }
