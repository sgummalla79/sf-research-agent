"""
LLM factory — builds a configured LangChain chat model for a given agent.

Usage:
    llm = build_llm("anthropic", "claude-sonnet-4-6")
    llm = get_llm_for_agent(agent_key, session_agent_config)
"""

import logging
from config import PERPLEXITY_API_BASE

log = logging.getLogger(__name__)

_GROQ_API_BASE    = "https://api.groq.com/openai/v1"
_MISTRAL_API_BASE = "https://api.mistral.ai/v1"


def build_llm(provider: str, model: str):
    """Return a configured LangChain chat model for the given provider and model."""
    from utils.user_api_keys import get_key, get_anthropic_mode

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        if get_anthropic_mode() == "bedrock":
            return ChatAnthropic(
                model=model,
                anthropic_api_url=get_key("anthropic_bedrock_url"),
                anthropic_api_key=get_key("anthropic_bedrock_token"),
            )
        return ChatAnthropic(model=model, anthropic_api_key=get_key("anthropic"))

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=get_key("openai"))

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=get_key("google"))

    if provider == "perplexity":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=get_key("perplexity"), base_url=PERPLEXITY_API_BASE)

    if provider == "groq":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=get_key("groq"), base_url=_GROQ_API_BASE)

    if provider == "mistral":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=get_key("mistral"), base_url=_MISTRAL_API_BASE)

    raise ValueError(f"Unknown LLM provider: {provider!r}")


def get_llm_for_agent(agent_key: str, session_agent_config: dict):
    """
    Return a configured LangChain chat model for the given agent key,
    reading from the session's frozen config snapshot.
    """
    cfg = session_agent_config.get(agent_key)
    if not cfg:
        raise RuntimeError(
            f"No model configured for agent '{agent_key}'. "
            "Ensure session_agent_config is populated before invoking the pipeline."
        )
    log.info("get_llm_for_agent  agent=%s  provider=%s  model=%s",
             agent_key, cfg.get("provider"), cfg.get("model"))
    return build_llm(cfg["provider"], cfg["model"])


def agent_model(agent_key: str, session_agent_config: dict) -> str:
    """Return the model name for a given agent key (for usage_record calls)."""
    cfg = session_agent_config.get(agent_key, {})
    return cfg.get("model", "unknown")
