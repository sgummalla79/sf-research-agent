"""
E2E tests for /api/providers routes.
Provider model fetching (refresh) is mocked — no real API keys needed.
"""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.e2e
async def test_list_providers_returns_all(client):
    resp = await client.get("/api/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    ids = [p["id"] for p in data["providers"]]
    assert "anthropic" in ids
    assert "openai"    in ids
    assert "google"    in ids
    assert "perplexity" in ids


@pytest.mark.e2e
async def test_connect_and_disconnect_provider(client):
    # Connect
    resp = await client.post("/api/providers/anthropic/connect",
                             json={"api_key": "sk-ant-test-key"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["provider"] == "anthropic"

    # List shows connected
    resp = await client.get("/api/providers")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    assert providers["anthropic"]["connected"] is True

    # Disconnect
    resp = await client.delete("/api/providers/anthropic")
    assert resp.status_code == 200

    # No longer connected
    resp = await client.get("/api/providers")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    assert providers["anthropic"]["connected"] is False


@pytest.mark.e2e
async def test_connect_unknown_provider_returns_404(client):
    resp = await client.post("/api/providers/nonexistent/connect",
                             json={"api_key": "key"})
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_refresh_models(client):
    with patch("utils.models_cache.fetch_models",
               new=AsyncMock(return_value=[{"id": "gpt-4o", "name": "GPT-4o"}])):
        resp = await client.post("/api/providers/openai/refresh")

    assert resp.status_code == 200
    assert resp.json()["provider"] == "openai"
    assert len(resp.json()["models"]) == 1


@pytest.mark.e2e
async def test_model_info_endpoint(client):
    resp = await client.get("/api/providers/model-info",
                            params={"provider": "anthropic", "model": "claude-sonnet-4-6"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "claude-sonnet-4-6"
    assert "context_window" in data
