"""
Unit tests for utils/llm_factory.py — LLM construction and agent slot lookup.
LLM provider clients are mocked so no API keys are needed.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_provider_keys():
    """Inject fake API keys into the ContextVar for all tests in this module."""
    from utils.user_context import set_user_context
    set_user_context({
        "anthropic":  "sk-ant-test",
        "openai":     "sk-oai-test",
        "google":     "AIza-test",
        "perplexity": "pplx-test",
        "groq":       "gsk-test",
        "mistral":    "mst-test",
    }, "direct")


def test_build_llm_anthropic():
    with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
        mock_cls.return_value = MagicMock()
        from utils.llm_factory import build_llm
        llm = build_llm("anthropic", "claude-sonnet-4-6")
        mock_cls.assert_called_once_with(
            model="claude-sonnet-4-6", anthropic_api_key="sk-ant-test"
        )


def test_build_llm_openai():
    with patch("langchain_openai.ChatOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        from utils.llm_factory import build_llm
        llm = build_llm("openai", "gpt-4o")
        mock_cls.assert_called_once_with(model="gpt-4o", api_key="sk-oai-test")


def test_build_llm_google():
    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        from utils.llm_factory import build_llm
        llm = build_llm("google", "gemini-2.0-flash")
        mock_cls.assert_called_once_with(model="gemini-2.0-flash", google_api_key="AIza-test")


def test_build_llm_perplexity():
    with patch("langchain_openai.ChatOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        from utils.llm_factory import build_llm
        from config import PERPLEXITY_API_BASE
        llm = build_llm("perplexity", "sonar-pro")
        mock_cls.assert_called_once_with(
            model="sonar-pro", api_key="pplx-test", base_url=PERPLEXITY_API_BASE
        )


def test_build_llm_unknown_provider_raises():
    from utils.llm_factory import build_llm
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_llm("nonexistent", "some-model")


def test_get_llm_for_agent_uses_config():
    session_cfg = {
        "discovery": {"provider": "anthropic", "model": "claude-sonnet-4-6"}
    }
    with patch("utils.llm_factory.build_llm") as mock_build:
        mock_build.return_value = MagicMock()
        from utils.llm_factory import get_llm_for_agent
        get_llm_for_agent("discovery", session_cfg)
        mock_build.assert_called_once_with("anthropic", "claude-sonnet-4-6")


def test_get_llm_for_agent_raises_when_not_in_config():
    from utils.llm_factory import get_llm_for_agent
    with pytest.raises(RuntimeError, match="No model configured for agent"):
        get_llm_for_agent("discovery", {})


def test_agent_model_returns_model_name():
    from utils.llm_factory import agent_model
    cfg = {"review": {"provider": "anthropic", "model": "claude-opus-4-7"}}
    assert agent_model("review", cfg) == "claude-opus-4-7"
    assert agent_model("missing", cfg) == "unknown"
