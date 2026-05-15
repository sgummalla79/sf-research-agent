"""
Shared pytest fixtures.

Database fixtures use a separate `pragna_test` database.
Each test that touches the DB gets a transaction that rolls back on teardown —
no persistent state between tests.
"""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

# Point at test DB before any imports that read DATABASE_URL
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL", "postgresql://pragna:pragna@localhost:5432/pragna_test"),
)
os.environ.setdefault("SETTINGS_SECRET", "dGVzdC1zZWNyZXQta2V5LXRoYXQtaXMtbG9uZy1lbm91Z2g=")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-that-is-long-enough-for-hs256-sig")
os.environ.setdefault("AUTH0_DOMAIN", "test.auth0.com")
os.environ.setdefault("AUTH0_CLIENT_ID", "test-client-id")
os.environ.setdefault("AUTH0_CLIENT_SECRET", "test-client-secret")


@pytest.fixture
def fake_user():
    from utils.auth import AuthUser
    return AuthUser(sub="test-user-001", email="test@example.com", name="Test User")


@pytest.fixture
def mock_db():
    """Lightweight mock DBContext for unit tests that don't need real DB."""
    db = MagicMock()
    db.skills        = AsyncMock()
    db.agents        = AsyncMock()
    db.users         = AsyncMock()
    db.user_skills   = AsyncMock()
    db.user_agents   = AsyncMock()
    db.conversations = AsyncMock()
    db.executions    = AsyncMock()
    db.messages      = AsyncMock()
    db.artifacts     = AsyncMock()
    db.usage         = AsyncMock()
    return db
