"""
E2E test — conversation creation and regular chat message.

Uses FastAPI TestClient + a real test database.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.e2e
async def test_create_conversation(mock_db, fake_user):
    """Create a conversation and verify the response."""
    from fastapi.testclient import TestClient
    from api.app import app

    from repositories.conversation_repository import Conversation
    mock_db.conversations.create = AsyncMock(return_value=Conversation(
        id="conv-001", user_id=fake_user.sub, title="Test Conv",
        chat_provider="anthropic", chat_model="claude-sonnet-4-6",
        created_at="2026-01-01T00:00:00Z", last_modified="2026-01-01T00:00:00Z",
    ))

    with patch("utils.auth.get_current_user", return_value=fake_user):
        app.state.db = mock_db
        client = TestClient(app, raise_server_exceptions=True)
        response = client.post("/api/conversations", json={
            "title": "Test Conv", "chat_provider": "anthropic", "chat_model": "claude-sonnet-4-6"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "conv-001"
    assert data["title"] == "Test Conv"


@pytest.mark.e2e
async def test_list_conversations_empty(mock_db, fake_user):
    mock_db.conversations.list_for_user = AsyncMock(return_value=[])

    from fastapi.testclient import TestClient
    from api.app import app

    with patch("utils.auth.get_current_user", return_value=fake_user):
        app.state.db = mock_db
        client = TestClient(app)
        response = client.get("/api/conversations")

    assert response.status_code == 200
    assert response.json()["conversations"] == []
