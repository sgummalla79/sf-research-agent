"""
Unit tests for model_metadata.py and models_cache.py.
Pure function calls — no mocking needed.
"""

import pytest


class TestModelMetadata:

    def test_known_model_returns_info(self):
        from utils.model_metadata import get_model_info
        info = get_model_info("anthropic", "claude-sonnet-4-6")
        assert info is not None
        assert info["model"]          == "claude-sonnet-4-6"
        assert info["provider"]       == "anthropic"
        assert info["context_window"] > 0

    def test_google_model_has_large_context(self):
        from utils.model_metadata import get_model_info
        info = get_model_info("google", "gemini-2.5-pro")
        assert info["context_window"] >= 1_000_000

    def test_unknown_model_returns_none(self):
        from utils.model_metadata import get_model_info
        assert get_model_info("anthropic", "nonexistent-model-xyz") is None

    def test_all_known_models_have_context_window(self):
        from utils.model_metadata import _MODEL_INFO
        for model_id, info in _MODEL_INFO.items():
            assert info["context_window"] > 0, f"{model_id} has no context_window"
            assert info["provider"] in ("anthropic", "google", "perplexity", "openai")


class TestModelsCache:

    async def test_anthropic_returns_model_list(self):
        from utils.models_cache import fetch_models
        models = await fetch_models("anthropic")
        assert isinstance(models, list)
        assert len(models) > 0
        assert all("id" in m and "name" in m for m in models)

    async def test_google_returns_model_list(self):
        from utils.models_cache import fetch_models
        models = await fetch_models("google")
        assert any("gemini" in m["id"] for m in models)

    async def test_perplexity_returns_model_list(self):
        from utils.models_cache import fetch_models
        models = await fetch_models("perplexity")
        assert any("sonar" in m["id"] for m in models)

    async def test_openai_returns_model_list(self):
        from utils.models_cache import fetch_models
        models = await fetch_models("openai")
        assert any("gpt" in m["id"] for m in models)

    async def test_unknown_provider_returns_empty(self):
        from utils.models_cache import fetch_models
        models = await fetch_models("unknown-provider")
        assert models == []
