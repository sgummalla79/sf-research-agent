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
async def test_provider_isactive_true_after_connect(client):
    """Connecting a provider sets isactive=True."""
    await client.post("/api/providers/openai/connect", json={"api_key": "sk-test"})

    resp = await client.get("/api/providers")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    assert providers["openai"]["isactive"] is True


@pytest.mark.e2e
async def test_toggle_provider_flips_isactive(client):
    """PATCH /toggle switches isactive and returns the new value."""
    await client.post("/api/providers/openai/connect", json={"api_key": "sk-test"})

    resp = await client.patch("/api/providers/openai/toggle")
    assert resp.status_code == 200
    assert resp.json()["isactive"] is False

    # Verify via list
    resp = await client.get("/api/providers")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    assert providers["openai"]["isactive"] is False

    # Toggle back
    resp = await client.patch("/api/providers/openai/toggle")
    assert resp.json()["isactive"] is True


@pytest.mark.e2e
async def test_toggle_not_connected_returns_404(client):
    resp = await client.patch("/api/providers/openai/toggle")
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_connect_resets_isactive_to_true(client):
    """Reconnecting a deactivated provider re-activates it."""
    await client.post("/api/providers/openai/connect", json={"api_key": "sk-test"})
    await client.patch("/api/providers/openai/toggle")  # deactivate

    # Reconnect
    resp = await client.post("/api/providers/openai/connect", json={"api_key": "sk-test-2"})
    assert resp.status_code == 200

    resp = await client.get("/api/providers")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    assert providers["openai"]["isactive"] is True


@pytest.mark.e2e
async def test_bedrock_connect_and_list(client):
    """POST /bedrock/connect stores credentials and shows as connected."""
    resp = await client.post("/api/providers/bedrock/connect", json={
        "bedrock_url":   "https://bedrock.example.com",
        "bedrock_token": "tok-test",
    })
    assert resp.status_code == 200
    assert resp.json()["provider"] == "bedrock"

    resp = await client.get("/api/providers")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    assert "bedrock" in providers
    assert providers["bedrock"]["connected"] is True
    assert providers["bedrock"]["isactive"]  is True


@pytest.mark.e2e
async def test_bedrock_toggle(client):
    await client.post("/api/providers/bedrock/connect", json={
        "bedrock_url": "https://bedrock.example.com", "bedrock_token": "tok"
    })

    resp = await client.patch("/api/providers/bedrock/toggle")
    assert resp.status_code == 200
    assert resp.json()["isactive"] is False

    resp = await client.patch("/api/providers/bedrock/toggle")
    assert resp.json()["isactive"] is True


@pytest.mark.e2e
async def test_bedrock_disconnect(client):
    await client.post("/api/providers/bedrock/connect", json={
        "bedrock_url": "https://bedrock.example.com", "bedrock_token": "tok"
    })

    resp = await client.delete("/api/providers/bedrock")
    assert resp.status_code == 200

    resp = await client.get("/api/providers")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    assert providers["bedrock"]["connected"] is False


@pytest.mark.e2e
async def test_model_info_endpoint(client):
    resp = await client.get("/api/providers/model-info",
                            params={"provider": "anthropic", "model": "claude-sonnet-4-6"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "claude-sonnet-4-6"
    assert "context_window" in data
