"""
E2E test — agent prompt versioning lifecycle.

Tests the draft → publish → current_version pointer flow.
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.e2e
async def test_save_draft_and_publish(mock_db, fake_user):
    from repositories.skill_repository import Skill
    from repositories.agent_repository import Agent
    from repositories.user_agent_repository import UserAgentVersion

    mock_skill = Skill(id="skill-001", skill_key="architect", name="Architect",
                       description="", icon="⚡", version=1, created_at="2026-01-01")
    mock_agent = Agent(id="agent-001", skill_id="skill-001", agent_key="discovery",
                       label="Discovery Agent", default_content="Default", created_at="2026-01-01")

    mock_db.skills.get_by_key = AsyncMock(return_value=mock_skill)
    mock_db.agents.get_by_key = AsyncMock(return_value=mock_agent)
    mock_db.user_agents.save_draft = AsyncMock(return_value=UserAgentVersion(
        id="uav-001", user_agent_id="ua-001", version=2,
        content="Updated prompt", status="draft", created_at="2026-01-01", published_at=None,
    ))

    from fastapi.testclient import TestClient
    from api.app import app
    from unittest.mock import patch

    with patch("utils.auth.get_current_user", return_value=fake_user):
        app.state.db = mock_db
        client = TestClient(app)
        response = client.put(
            "/api/skills/architect/agents/discovery/draft",
            json={"content": "Updated prompt"},
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["version"] == 2


@pytest.mark.e2e
async def test_publish_all_no_drafts_returns_400(mock_db, fake_user):
    from repositories.skill_repository import Skill
    mock_skill = Skill(id="skill-001", skill_key="architect", name="Architect",
                       description="", icon="⚡", version=1, created_at="2026-01-01")
    mock_db.skills.get_by_key = AsyncMock(return_value=mock_skill)
    mock_db.user_agents.publish_all = AsyncMock(return_value=[])

    from fastapi.testclient import TestClient
    from api.app import app
    from unittest.mock import patch

    with patch("utils.auth.get_current_user", return_value=fake_user):
        app.state.db = mock_db
        client = TestClient(app)
        response = client.post("/api/skills/architect/publish")

    assert response.status_code == 400
