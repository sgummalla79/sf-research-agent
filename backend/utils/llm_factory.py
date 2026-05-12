"""
LLM factory — builds a configured LangChain chat model for a given agent slot.

Usage:
    llm = build_llm("anthropic", "claude-sonnet-4-6")
    llm = get_llm_for_slot(slot, session_agent_config)
"""

from config import PERPLEXITY_API_BASE
from utils.api_keys import get_key

# OpenAI-compatible base URLs for providers that use that protocol
_GROQ_API_BASE    = "https://api.groq.com/openai/v1"
_MISTRAL_API_BASE = "https://api.mistral.ai/v1"


def build_llm(provider: str, model: str):
    """Return a configured LangChain chat model for the given provider and model."""
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=get_key("anthropic"))

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=get_key("openai"))

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=get_key("google"))

    elif provider == "perplexity":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=get_key("perplexity"), base_url=PERPLEXITY_API_BASE)

    elif provider == "groq":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=get_key("groq"), base_url=_GROQ_API_BASE)

    elif provider == "mistral":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=get_key("mistral"), base_url=_MISTRAL_API_BASE)

    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}")


def get_llm_for_slot(slot: str, session_config: dict):
    """
    Return a configured LangChain chat model for the given agent slot,
    reading from the session's frozen config snapshot.
    Falls back to the global default if the session config is missing the slot.
    """
    from utils.agent_config import DEFAULT_AGENT_CONFIG
    cfg = session_config.get(slot) or DEFAULT_AGENT_CONFIG.get(slot, {})
    return build_llm(cfg["provider"], cfg["model"])


def slot_model(slot: str, session_config: dict) -> str:
    """Return the model name for a given slot (for usage_record calls)."""
    from utils.agent_config import DEFAULT_AGENT_CONFIG
    cfg = session_config.get(slot) or DEFAULT_AGENT_CONFIG.get(slot, {})
    return cfg.get("model", "unknown")
