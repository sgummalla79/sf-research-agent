"""
Shared pytest fixtures.

client:  full FastAPI app wired to pragna_test DB, auth dependency overridden.
pool:    raw psycopg pool for repository-level tests.
mock_db: lightweight mock DBContext (no DB needed).
"""

import os
import pytest
import pytest_asyncio

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://pragna:pragna_dev@localhost:5432/pragna_test",
)

# Must be set before any module-level imports that call os.getenv()
os.environ["DATABASE_URL"]        = TEST_DB_URL
os.environ["SETTINGS_SECRET"]     = "iKAvMwP3LI41X6jTI65qdetfjnnIVVrStE_9B4Q2-7U="
os.environ["JWT_SECRET"]          = "a" * 64
os.environ["AUTH0_DOMAIN"]        = "test.auth0.com"
os.environ["AUTH0_CLIENT_ID"]     = "test-client-id"
os.environ["AUTH0_CLIENT_SECRET"] = "test-client-secret"


_TRUNCATE_SQL = """
    TRUNCATE TABLE
        token_usage, conversation_artifacts, conversation_messages,
        conversation_skill_execution_stages, conversation_skill_executions,
        conversation_skill_agents, conversation_skills, conversations,
        user_agents_versions, user_agents, user_skills,
        user_api_keys, user_config, users
    CASCADE
"""
# Note: skills + agents are platform data seeded by lifespan — never truncated.


# ── Shared user ───────────────────────────────────────────────────────────────

@pytest.fixture
def fake_user():
    from utils.auth import AuthUser
    return AuthUser(sub="test-user-001", email="test@example.com", name="Test User")


# ── Full test client (real DB + mocked auth) ──────────────────────────────────

@pytest_asyncio.fixture
async def client(fake_user):
    """
    AsyncClient backed by pragna_test DB with the full FastAPI lifespan running.
    Auth dependency is overridden — every request acts as fake_user.
    Tables are truncated before yielding.
    """
    from httpx import AsyncClient, ASGITransport
    from api.app import app
    from utils.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: fake_user

    # Explicitly trigger the ASGI lifespan (startup + shutdown).
    # AsyncClient alone does not send the lifespan.startup event.
    async with app.router.lifespan_context(app):
        db = app.state.db

        async with db.pool.connection() as conn:
            await conn.execute(_TRUNCATE_SQL)

        await db.users.upsert(fake_user.sub, fake_user.email, fake_user.name, None)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Content-Type": "application/json"},
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Raw pool for repository-level tests ──────────────────────────────────────

@pytest_asyncio.fixture
async def pool():
    from psycopg_pool import AsyncConnectionPool
    async with AsyncConnectionPool(
        TEST_DB_URL, min_size=1, max_size=2,
        kwargs={"autocommit": True}, open=False,
    ) as p:
        await p.open(wait=True)
        async with p.connection() as conn:
            await conn.execute(_TRUNCATE_SQL)
        yield p


# ── Lightweight mock DB (no DB needed) ────────────────────────────────────────

@pytest.fixture
def mock_db():
    from unittest.mock import AsyncMock, MagicMock
    db = MagicMock()
    for repo in ("skills", "agents", "users", "user_skills", "user_agents",
                 "conversations", "executions", "messages", "artifacts", "usage"):
        setattr(db, repo, AsyncMock())
    return db
