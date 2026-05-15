"""
Unit tests for utils/provider_registry.py — per-provider model fetching.
All external SDK/HTTP calls are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


async def test_fetch_anthropic_direct():
    from utils.provider_registry import _fetch_anthropic

    mock_model = MagicMock()
    mock_model.id = "claude-sonnet-4-6"

    mock_response = MagicMock()
    mock_response.data = [mock_model]

    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=None)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        models = await _fetch_anthropic("sk-ant-test")

    assert "claude-sonnet-4-6" in models


async def test_fetch_openai():
    from utils.provider_registry import _fetch_openai

    mock_model = MagicMock()
    mock_model.id = "gpt-4o"

    mock_response = MagicMock()
    mock_response.data = [mock_model]

    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=None)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        models = await _fetch_openai("sk-oai-test")

    assert "gpt-4o" in models


async def test_fetch_openai_excludes_non_chat_models():
    from utils.provider_registry import _fetch_openai

    m1 = MagicMock(); m1.id = "gpt-4o"
    m2 = MagicMock(); m2.id = "text-embedding-ada-002"
    m3 = MagicMock(); m3.id = "tts-1"
    m4 = MagicMock(); m4.id = "whisper-1"

    mock_response = MagicMock()
    mock_response.data = [m1, m2, m3, m4]

    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=None)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        models = await _fetch_openai("sk-oai-test")

    assert "gpt-4o" in models
    assert "text-embedding-ada-002" not in models
    assert "tts-1" not in models
    assert "whisper-1" not in models


async def test_fetch_google():
    from utils.provider_registry import _fetch_google

    mock_model = MagicMock()
    mock_model.name = "models/gemini-2.5-pro"
    mock_model.supported_generation_methods = ["generateContent"]

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.list_models", return_value=[mock_model]):
        models = await _fetch_google("AIza-test")

    assert "gemini-2.5-pro" in models


async def test_fetch_google_excludes_non_generative():
    from utils.provider_registry import _fetch_google

    m1 = MagicMock(); m1.name = "models/gemini-2.5-pro"
    m1.supported_generation_methods = ["generateContent"]
    m2 = MagicMock(); m2.name = "models/embedding-001"
    m2.supported_generation_methods = ["embedContent"]

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.list_models", return_value=[m1, m2]):
        models = await _fetch_google("AIza-test")

    assert "gemini-2.5-pro" in models
    assert "embedding-001" not in models


async def test_fetch_perplexity_valid_key():
    from utils.provider_registry import _fetch_perplexity, _PERPLEXITY_MODELS
    models = await _fetch_perplexity("pplx-valid-key")
    assert models == list(_PERPLEXITY_MODELS)


async def test_fetch_perplexity_invalid_key_raises():
    from utils.provider_registry import _fetch_perplexity
    with pytest.raises(ValueError, match="pplx-"):
        await _fetch_perplexity("invalid-key-format")


async def test_fetch_groq():
    from utils.provider_registry import _fetch_groq

    mock_model = MagicMock(); mock_model.id = "llama-3.3-70b-versatile"
    mock_response = MagicMock(); mock_response.data = [mock_model]
    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=None)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        models = await _fetch_groq("gsk-test")

    assert "llama-3.3-70b-versatile" in models


async def test_fetch_mistral():
    from utils.provider_registry import _fetch_mistral

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"id": "mistral-large-latest"}]}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        models = await _fetch_mistral("mst-test")

    assert "mistral-large-latest" in models


async def test_fetch_models_dispatches_correctly():
    from utils.provider_registry import fetch_models

    with patch("utils.provider_registry._fetch_anthropic",
               new=AsyncMock(return_value=["claude-sonnet-4-6"])) as mock:
        result = await fetch_models("anthropic", "sk-ant-test")

    mock.assert_called_once_with("sk-ant-test", mode="direct",
                                 bedrock_url="", bedrock_token="")
    assert result == ["claude-sonnet-4-6"]


async def test_fetch_models_unknown_provider_raises():
    from utils.provider_registry import fetch_models
    with pytest.raises(ValueError, match="Unknown provider"):
        await fetch_models("unknown-provider", "some-key")
