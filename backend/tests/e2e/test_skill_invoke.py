"""
E2E test — skill invocation guards.

Tests that the invoke endpoint properly rejects invalid states
without actually running the LangGraph pipeline.
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.e2e
async def test_invoke_rejects_when_skill_not_running(mock_db, fake_user):
    """409 when another skill is already running in the conversation."""
    from repositories.conversation_repository import Conversation, ConversationSkill
    from repositories.execution_repository import Execution

    mock_db.conversations.get_by_id = AsyncMock(return_value=Conversation(
        id="conv-001", user_id=fake_user.sub, title="Test",
        chat_provider="anthropic", chat_model="claude-sonnet-4-6",
        created_at="2026-01-01", last_modified="2026-01-01",
    ))
    mock_db.conversations.get_skill = AsyncMock(return_value=ConversationSkill(
        id="cs-001", conversation_id="conv-001", skill_id="skill-001", added_at="2026-01-01",
    ))
    # Simulate a running execution
    mock_db.executions.get_running = AsyncMock(return_value=Execution(
        id="exec-existing", conversation_skill_id="cs-001",
        status="running", started_at="2026-01-01", completed_at=None,
    ))

    from fastapi.testclient import TestClient
    from api.app import app
    from unittest.mock import patch

    with patch("utils.auth.get_current_user", return_value=fake_user):
        app.state.db = mock_db
        client = TestClient(app)
        response = client.post(
            "/api/conversations/conv-001/skills/cs-001/invoke",
            json={"brief": "Build a platform", "source_type": "brief"},
        )

    assert response.status_code == 409
    assert "already running" in response.json()["detail"]


@pytest.mark.e2e
async def test_invoke_rejects_conversation_not_found(mock_db, fake_user):
    mock_db.conversations.get_by_id = AsyncMock(return_value=None)

    from fastapi.testclient import TestClient
    from api.app import app
    from unittest.mock import patch

    with patch("utils.auth.get_current_user", return_value=fake_user):
        app.state.db = mock_db
        client = TestClient(app)
        response = client.post(
            "/api/conversations/nonexistent/skills/cs-001/invoke",
            json={"brief": "test", "source_type": "brief"},
        )

    assert response.status_code == 404
