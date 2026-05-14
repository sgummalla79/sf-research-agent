"""
Database backend factory for LangGraph checkpointing.

DB_BACKEND=sqlite    → aiosqlite, zero-config local file
DB_BACKEND=postgres  → AsyncPostgresSaver + connection pool

Public API on DBContext:
  upsert_user(user_id, email, name, picture)
  record_session(thread_id, user_id, snippet)  create session
  update_session_title(id, title)              overwrite title after Haiku generation
  update_last_modified(id)                     called on every reply
  pin_session(id)                              pin (max 10)
  unpin_session(id)
  rename_session(id, title)
  delete_session(id)                           removes from agent_sessions + LG tables
  list_sessions(user_id)                       returns {pinned:[...], recent:[...]}
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import DATABASE_URL, DB_BACKEND, DB_POOL_SIZE, POSTGRES_URI, SESSION_TTL_DAYS, SQLITE_PATH

logger = logging.getLogger(__name__)

MAX_PINNED = 10

# ── DDL ───────────────────────────────────────────────────────────────────────

_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    picture     TEXT,
    created_at  TEXT NOT NULL,
    last_login  TEXT
);
"""

_CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    thread_id      TEXT PRIMARY KEY,
    user_id        TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    brief_snippet  TEXT,
    last_modified  TEXT,
    pinned         INTEGER DEFAULT 0,
    pinned_at      TEXT,
    session_type   TEXT DEFAULT 'agent_flow',
    chat_model     TEXT,
    chat_provider  TEXT DEFAULT 'anthropic'
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON agent_sessions(user_id);
"""

# Additive migration — safely adds new columns to existing installs without wiping data.
# These are idempotent: PostgreSQL uses IF NOT EXISTS; SQLite errors are caught below.
_ADD_SESSION_COLUMNS_PG = [
    "ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS session_type  TEXT DEFAULT 'agent_flow'",
    "ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS chat_model    TEXT",
    "ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS chat_provider TEXT DEFAULT 'anthropic'",
]
_ADD_SESSION_COLUMNS_SL = [
    "ALTER TABLE agent_sessions ADD COLUMN session_type  TEXT DEFAULT 'agent_flow'",
    "ALTER TABLE agent_sessions ADD COLUMN chat_model    TEXT",
    "ALTER TABLE agent_sessions ADD COLUMN chat_provider TEXT DEFAULT 'anthropic'",
]

_CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS app_settings (
    user_id         TEXT NOT NULL,
    key_name        TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    PRIMARY KEY (user_id, key_name)
);
"""

_CREATE_USAGE_TABLE_SL = """
CREATE TABLE IF NOT EXISTS token_usage (
    id            INTEGER PRIMARY KEY,
    user_id       TEXT NOT NULL,
    thread_id     TEXT NOT NULL,
    agent         TEXT NOT NULL,
    model         TEXT NOT NULL,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd      REAL    DEFAULT 0,
    created_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_user ON token_usage(user_id);
"""

_CREATE_USAGE_TABLE_PG = """
CREATE TABLE IF NOT EXISTS token_usage (
    id            BIGSERIAL PRIMARY KEY,
    user_id       TEXT NOT NULL,
    thread_id     TEXT NOT NULL,
    agent         TEXT NOT NULL,
    model         TEXT NOT NULL,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd      REAL    DEFAULT 0,
    created_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_user ON token_usage(user_id);
"""

_CREATE_CONFIG_TABLE = """
CREATE TABLE IF NOT EXISTS app_config (
    user_id    TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);
"""

_CREATE_PROMPT_VERSIONS_SL = """
CREATE TABLE IF NOT EXISTS agent_prompt_versions (
    id           INTEGER PRIMARY KEY,
    user_id      TEXT    NOT NULL,
    flow_id      TEXT    NOT NULL,
    agent_key    TEXT    NOT NULL,
    version      INTEGER NOT NULL,
    content      TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'draft',
    model_config TEXT,
    created_at   TEXT    NOT NULL,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_apv_user_flow_key ON agent_prompt_versions(user_id, flow_id, agent_key);
"""

_CREATE_PROMPT_VERSIONS_PG = """
CREATE TABLE IF NOT EXISTS agent_prompt_versions (
    id           BIGSERIAL PRIMARY KEY,
    user_id      TEXT    NOT NULL,
    flow_id      TEXT    NOT NULL,
    agent_key    TEXT    NOT NULL,
    version      INTEGER NOT NULL,
    content      TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'draft',
    model_config TEXT,
    created_at   TEXT    NOT NULL,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_apv_user_flow_key ON agent_prompt_versions(user_id, flow_id, agent_key);
"""

_CREATE_SNAPSHOTS_SL = """
CREATE TABLE IF NOT EXISTS flow_prompt_snapshots (
    id               INTEGER PRIMARY KEY,
    user_id          TEXT    NOT NULL,
    flow_id          TEXT    NOT NULL,
    snapshot_version INTEGER NOT NULL,
    agent_versions   TEXT    NOT NULL,
    created_at       TEXT    NOT NULL,
    triggered_by     TEXT    NOT NULL
);
"""

_CREATE_SNAPSHOTS_PG = """
CREATE TABLE IF NOT EXISTS flow_prompt_snapshots (
    id               BIGSERIAL PRIMARY KEY,
    user_id          TEXT    NOT NULL,
    flow_id          TEXT    NOT NULL,
    snapshot_version INTEGER NOT NULL,
    agent_versions   TEXT    NOT NULL,
    created_at       TEXT    NOT NULL,
    triggered_by     TEXT    NOT NULL
);
"""

_CREATE_INSTALLED_SKILLS = """
CREATE TABLE IF NOT EXISTS installed_skills (
    user_id      TEXT NOT NULL,
    skill_id     TEXT NOT NULL,
    installed_at TEXT NOT NULL,
    PRIMARY KEY (user_id, skill_id)
);
"""


# ── Migration ─────────────────────────────────────────────────────────────────

async def _schema_complete(conn, backend: str) -> bool:
    """
    Return True only when the v2 schema is fully in place.
    Checks both the users table AND that token_usage has user_id —
    the latter catches partial migrations that crashed mid-way.
    """
    try:
        if backend == "sqlite":
            cur = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            if not await cur.fetchone():
                return False
            cur = await conn.execute("PRAGMA table_info(token_usage)")
            cols = {row[1] for row in await cur.fetchall()}
            return "user_id" in cols
        else:
            cur = await conn.execute(
                "SELECT tablename FROM pg_catalog.pg_tables "
                "WHERE schemaname='public' AND tablename='users'"
            )
            if not await cur.fetchone():
                return False
            cur = await conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='token_usage' AND column_name='user_id'"
            )
            return bool(await cur.fetchone())
    except Exception:
        return False


async def _migrate(conn, backend: str) -> None:
    """
    v2 migration: wipe all pre-auth tables and recreate with user_id columns.
    Checks schema completeness so a mid-crash partial migration is re-run.
    """
    try:
        if await _schema_complete(conn, backend):
            return  # Already on v2 schema — nothing to do

        # ── Wipe everything (legacy + any partially-created v2 tables) ────────
        to_drop = [
            "agent_prompt_versions", "flow_prompt_snapshots", "installed_skills",
            "token_usage", "agent_sessions", "app_settings", "app_config",
            "users",
            # LangGraph internal tables — include migrations table so setup()
            # re-runs all CREATE TABLE statements after a wipe
            "checkpoint_writes", "checkpoint_blobs", "checkpoints",
            "checkpoint_migrations",
        ]
        for table in to_drop:
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            except Exception:
                try:
                    await conn.execute(f"DROP TABLE IF EXISTS {table}")
                except Exception:
                    pass
        await conn.commit()

    except Exception:
        pass  # Let table creation handle edge cases


# ── DBContext ─────────────────────────────────────────────────────────────────

@dataclass
class DBContext:
    checkpointer:  Any
    _backend:      str
    _conn_or_pool: Any

    # ── helpers ───────────────────────────────────────────────────────────────

    def _p(self) -> str:
        return "?" if self._backend == "sqlite" else "%s"

    async def _exec(self, sql: str, params: tuple = ()) -> None:
        if self._backend == "sqlite":
            await self._conn_or_pool.execute(sql, params)
            await self._conn_or_pool.commit()
        else:
            async with self._conn_or_pool.connection() as conn:
                await conn.execute(sql, params)

    async def _fetchone(self, sql: str, params: tuple = ()):
        if self._backend == "sqlite":
            cur = await self._conn_or_pool.execute(sql, params)
            return await cur.fetchone()
        else:
            async with self._conn_or_pool.connection() as conn:
                cur = await conn.execute(sql, params)
                return await cur.fetchone()

    async def _fetchall(self, sql: str, params: tuple = ()):
        if self._backend == "sqlite":
            cur = await self._conn_or_pool.execute(sql, params)
            return await cur.fetchall()
        else:
            async with self._conn_or_pool.connection() as conn:
                cur = await conn.execute(sql, params)
                return await cur.fetchall()

    # ── public API ────────────────────────────────────────────────────────────

    async def upsert_user(self, user_id: str, email: str, name: str, picture: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if self._backend == "sqlite":
            await self._exec(
                "INSERT INTO users (id, email, name, picture, created_at, last_login)"
                " VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET email=excluded.email,"
                "  name=excluded.name, picture=excluded.picture, last_login=excluded.last_login",
                (user_id, email, name, picture, now, now),
            )
        else:
            await self._exec(
                "INSERT INTO users (id, email, name, picture, created_at, last_login)"
                " VALUES (%s, %s, %s, %s, %s, %s)"
                " ON CONFLICT(id) DO UPDATE SET email=EXCLUDED.email,"
                "  name=EXCLUDED.name, picture=EXCLUDED.picture, last_login=EXCLUDED.last_login",
                (user_id, email, name, picture, now, now),
            )

    async def record_session(
        self,
        thread_id:    str,
        user_id:      str,
        brief_snippet: str = "",
        session_type:  str = "agent_flow",
        chat_model:    str | None = None,
        chat_provider: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if self._backend == "sqlite":
            await self._exec(
                "INSERT OR REPLACE INTO agent_sessions"
                " (thread_id, user_id, created_at, brief_snippet, last_modified,"
                "  session_type, chat_model, chat_provider)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (thread_id, user_id, now, brief_snippet[:120], now,
                 session_type, chat_model, chat_provider),
            )
        else:
            await self._exec(
                "INSERT INTO agent_sessions"
                " (thread_id, user_id, created_at, brief_snippet, last_modified,"
                "  session_type, chat_model, chat_provider)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (thread_id) DO NOTHING",
                (thread_id, user_id, now, brief_snippet[:120], now,
                 session_type, chat_model, chat_provider),
            )

    async def update_session_title(self, thread_id: str, title: str) -> None:
        p = self._p()
        await self._exec(
            f"UPDATE agent_sessions SET brief_snippet = {p} WHERE thread_id = {p}",
            (title[:120], thread_id),
        )

    async def update_last_modified(self, thread_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        p = self._p()
        await self._exec(
            f"UPDATE agent_sessions SET last_modified = {p} WHERE thread_id = {p}",
            (now, thread_id),
        )

    async def pin_session(self, thread_id: str, user_id: str | None = None) -> None:
        p = self._p()
        if user_id is not None:
            row = await self._fetchone(
                f"SELECT COUNT(*) FROM agent_sessions WHERE pinned = 1 AND user_id = {p}",
                (user_id,),
            )
        else:
            row = await self._fetchone(
                "SELECT COUNT(*) FROM agent_sessions WHERE pinned = 1",
            )
        if row and row[0] >= MAX_PINNED:
            raise ValueError(f"Maximum {MAX_PINNED} pinned conversations reached.")
        now = datetime.now(timezone.utc).isoformat()
        await self._exec(
            f"UPDATE agent_sessions SET pinned = 1, pinned_at = {p} WHERE thread_id = {p}",
            (now, thread_id),
        )

    async def unpin_session(self, thread_id: str, user_id: str | None = None) -> None:
        p = self._p()
        await self._exec(
            f"UPDATE agent_sessions SET pinned = 0, pinned_at = NULL WHERE thread_id = {p}",
            (thread_id,),
        )

    async def rename_session(self, thread_id: str, title: str) -> None:
        p = self._p()
        await self._exec(
            f"UPDATE agent_sessions SET brief_snippet = {p} WHERE thread_id = {p}",
            (title[:120], thread_id),
        )

    async def delete_session(self, thread_id: str) -> None:
        p = self._p()
        await self._exec(
            f"DELETE FROM agent_sessions WHERE thread_id = {p}",
            (thread_id,),
        )
        # Remove LangGraph checkpoint data
        if self._backend == "sqlite":
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                await self._conn_or_pool.execute(
                    f"DELETE FROM {table} WHERE thread_id = ?", (thread_id,)  # noqa: S608
                )
            await self._conn_or_pool.commit()
        else:
            async with self._conn_or_pool.connection() as conn:
                for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                    await conn.execute(
                        f"DELETE FROM {table} WHERE thread_id = %s", (thread_id,)  # noqa: S608
                    )

    async def list_sessions(self, user_id: str) -> dict:
        p = self._p()
        rows = await self._fetchall(
            f"SELECT thread_id, created_at, brief_snippet, last_modified, pinned, pinned_at,"
            f"       session_type, chat_model, chat_provider"
            f" FROM agent_sessions WHERE user_id = {p}",
            (user_id,),
        )
        items = [
            {
                "thread_id":     r[0],
                "created_at":    r[1],
                "brief_snippet": r[2],
                "last_modified": r[3],
                "pinned":        bool(r[4]),
                "pinned_at":     r[5],
                "session_type":  r[6] or "agent_flow",
                "chat_model":    r[7],
                "chat_provider": r[8] or "anthropic",
            }
            for r in rows
        ]
        pinned = sorted(
            [s for s in items if s["pinned"]],
            key=lambda x: x["pinned_at"] or "",
            reverse=True,
        )
        recent = sorted(
            [s for s in items if not s["pinned"]],
            key=lambda x: x["last_modified"] or x["created_at"] or "",
            reverse=True,
        )
        return {"pinned": pinned[:MAX_PINNED], "recent": recent}

    async def save_usage_records(self, user_id: str, thread_id: str, records: list[dict]) -> None:
        """Replace all token_usage rows for this thread with the current full list."""
        if self._backend == "sqlite":
            await self._conn_or_pool.execute("DELETE FROM token_usage WHERE thread_id = ?", (thread_id,))
            for r in records:
                await self._conn_or_pool.execute(
                    "INSERT INTO token_usage"
                    " (user_id, thread_id, agent, model, input_tokens, output_tokens, cost_usd, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, thread_id, r["agent"], r["model"], r["input_tokens"], r["output_tokens"], r["cost_usd"], r["created_at"]),
                )
            await self._conn_or_pool.commit()
        else:
            async with self._conn_or_pool.connection() as conn:
                await conn.execute("DELETE FROM token_usage WHERE thread_id = %s", (thread_id,))
                for r in records:
                    await conn.execute(
                        "INSERT INTO token_usage"
                        " (user_id, thread_id, agent, model, input_tokens, output_tokens, cost_usd, created_at)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (user_id, thread_id, r["agent"], r["model"], r["input_tokens"], r["output_tokens"], r["cost_usd"], r["created_at"]),
                    )

    async def get_session_usage(self, thread_id: str) -> dict:
        # thread_id is globally unique so no user_id filter needed here
        sql = (
            "SELECT model, SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)"
            " FROM token_usage WHERE thread_id = ? GROUP BY model ORDER BY SUM(cost_usd) DESC"
            if self._backend == "sqlite" else
            "SELECT model, SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)"
            " FROM token_usage WHERE thread_id = %s GROUP BY model ORDER BY SUM(cost_usd) DESC"
        )
        rows = await self._fetchall(sql, (thread_id,))
        breakdown = [{"model": r[0], "input_tokens": r[1], "output_tokens": r[2], "cost_usd": round(r[3], 6)} for r in rows]
        return {
            "breakdown": breakdown,
            "totals": {
                "input_tokens":  sum(r["input_tokens"]  for r in breakdown),
                "output_tokens": sum(r["output_tokens"] for r in breakdown),
                "cost_usd":      round(sum(r["cost_usd"] for r in breakdown), 6),
            },
        }

    async def get_global_usage(self) -> dict:
        rows = await self._fetchall(
            "SELECT model, SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)"
            " FROM token_usage GROUP BY model ORDER BY SUM(cost_usd) DESC"
        )
        breakdown = [{"model": r[0], "input_tokens": r[1], "output_tokens": r[2], "cost_usd": round(r[3], 6)} for r in rows]
        count_row = await self._fetchone("SELECT COUNT(DISTINCT thread_id) FROM token_usage")
        return {
            "breakdown": breakdown,
            "totals": {
                "input_tokens":  sum(r["input_tokens"]  for r in breakdown),
                "output_tokens": sum(r["output_tokens"] for r in breakdown),
                "cost_usd":      round(sum(r["cost_usd"] for r in breakdown), 6),
            },
            "session_count": count_row[0] if count_row else 0,
        }

    async def save_api_key(self, user_id: str, key_name: str, encrypted_value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if self._backend == "sqlite":
            await self._exec(
                "INSERT OR REPLACE INTO app_settings (user_id, key_name, encrypted_value, updated_at)"
                " VALUES (?, ?, ?, ?)",
                (user_id, key_name, encrypted_value, now),
            )
        else:
            await self._exec(
                "INSERT INTO app_settings (user_id, key_name, encrypted_value, updated_at)"
                " VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (user_id, key_name) DO UPDATE SET"
                "  encrypted_value = EXCLUDED.encrypted_value, updated_at = EXCLUDED.updated_at",
                (user_id, key_name, encrypted_value, now),
            )

    async def get_all_api_keys(self, user_id: str) -> dict[str, str]:
        """Returns {key_name: encrypted_value} for every stored key belonging to the user."""
        if self._backend == "sqlite":
            rows = await self._fetchall(
                "SELECT key_name, encrypted_value FROM app_settings WHERE user_id = ?",
                (user_id,),
            )
        else:
            rows = await self._fetchall(
                "SELECT key_name, encrypted_value FROM app_settings WHERE user_id = %s",
                (user_id,),
            )
        return {r[0]: r[1] for r in rows}

    async def delete_provider(self, user_id: str, provider_id: str) -> None:
        """Remove a provider's API key and cached model list."""
        if self._backend == "sqlite":
            await self._exec(
                "DELETE FROM app_settings WHERE user_id = ? AND key_name = ?",
                (user_id, provider_id),
            )
            await self._exec(
                "DELETE FROM app_config WHERE user_id = ? AND key = ?",
                (user_id, f"models_{provider_id}"),
            )
        else:
            await self._exec(
                "DELETE FROM app_settings WHERE user_id = %s AND key_name = %s",
                (user_id, provider_id),
            )
            await self._exec(
                "DELETE FROM app_config WHERE user_id = %s AND key = %s",
                (user_id, f"models_{provider_id}"),
            )

    async def delete_api_key(self, user_id: str, key_name: str) -> None:
        """Remove a single row from app_settings by user_id and key_name."""
        if self._backend == "sqlite":
            await self._exec(
                "DELETE FROM app_settings WHERE user_id = ? AND key_name = ?",
                (user_id, key_name),
            )
        else:
            await self._exec(
                "DELETE FROM app_settings WHERE user_id = %s AND key_name = %s",
                (user_id, key_name),
            )

    async def delete_config(self, user_id: str, key: str) -> None:
        """Remove a single row from app_config by user_id and key."""
        if self._backend == "sqlite":
            await self._exec(
                "DELETE FROM app_config WHERE user_id = ? AND key = ?",
                (user_id, key),
            )
        else:
            await self._exec(
                "DELETE FROM app_config WHERE user_id = %s AND key = %s",
                (user_id, key),
            )

    async def save_config(self, user_id: str, key: str, value: str) -> None:
        """Persist a plain-text config value (not encrypted)."""
        now = datetime.now(timezone.utc).isoformat()
        if self._backend == "sqlite":
            await self._exec(
                "INSERT OR REPLACE INTO app_config (user_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, key, value, now),
            )
        else:
            await self._exec(
                "INSERT INTO app_config (user_id, key, value, updated_at) VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at",
                (user_id, key, value, now),
            )

    async def get_config(self, user_id: str, key: str) -> str | None:
        """Return a stored config value for the user, or None if not set."""
        if self._backend == "sqlite":
            row = await self._fetchone(
                "SELECT value FROM app_config WHERE user_id = ? AND key = ?",
                (user_id, key),
            )
        else:
            row = await self._fetchone(
                "SELECT value FROM app_config WHERE user_id = %s AND key = %s",
                (user_id, key),
            )
        return row[0] if row else None

    # ── Agent prompt versioning ───────────────────────────────────────────────

    async def is_skill_seeded(self, user_id: str, flow_id: str, agent_keys: list[str]) -> bool:
        """Check if ALL specified agent keys are already seeded for a flow."""
        p = self._p()
        for key in agent_keys:
            row = await self._fetchone(
                f"SELECT COUNT(*) FROM agent_prompt_versions"
                f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p} AND status = 'published'",
                (user_id, flow_id, key),
            )
            if not row or row[0] == 0:
                return False
        return True

    async def is_flow_seeded(self, user_id: str, flow_id: str) -> bool:
        p = self._p()
        row = await self._fetchone(
            f"SELECT COUNT(*) FROM agent_prompt_versions"
            f" WHERE user_id = {p} AND flow_id = {p} AND status = 'published'",
            (user_id, flow_id),
        )
        return bool(row and row[0] > 0)

    async def seed_flow_prompts(self, user_id: str, flow_id: str, prompts: dict[str, str]) -> None:
        import json
        now = datetime.now(timezone.utc).isoformat()
        if self._backend == "sqlite":
            for agent_key, content in prompts.items():
                await self._conn_or_pool.execute(
                    "INSERT INTO agent_prompt_versions"
                    " (user_id, flow_id, agent_key, version, content, status, created_at, published_at)"
                    " VALUES (?, ?, ?, 1, ?, 'published', ?, ?)",
                    (user_id, flow_id, agent_key, content, now, now),
                )
            await self._conn_or_pool.execute(
                "INSERT INTO flow_prompt_snapshots"
                " (user_id, flow_id, snapshot_version, agent_versions, created_at, triggered_by)"
                " VALUES (?, ?, 1, ?, ?, 'seed')",
                (user_id, flow_id, json.dumps({k: 1 for k in prompts}), now),
            )
            await self._conn_or_pool.commit()
        else:
            async with self._conn_or_pool.connection() as conn:
                for agent_key, content in prompts.items():
                    await conn.execute(
                        "INSERT INTO agent_prompt_versions"
                        " (user_id, flow_id, agent_key, version, content, status, created_at, published_at)"
                        " VALUES (%s, %s, %s, 1, %s, 'published', %s, %s)",
                        (user_id, flow_id, agent_key, content, now, now),
                    )
                await conn.execute(
                    "INSERT INTO flow_prompt_snapshots"
                    " (user_id, flow_id, snapshot_version, agent_versions, created_at, triggered_by)"
                    " VALUES (%s, %s, 1, %s, %s, 'seed')",
                    (user_id, flow_id, json.dumps({k: 1 for k in prompts}), now),
                )

    async def get_flow_prompts(self, user_id: str, flow_id: str) -> list[dict]:
        import json as _json
        p    = self._p()
        rows = await self._fetchall(
            f"SELECT id, agent_key, version, content, status, created_at, published_at, model_config"
            f" FROM agent_prompt_versions"
            f" WHERE user_id = {p} AND flow_id = {p}"
            f" ORDER BY agent_key, version DESC",
            (user_id, flow_id),
        )
        from collections import defaultdict
        by_key: dict[str, list] = defaultdict(list)
        for r in rows:
            by_key[r[1]].append({
                "id": r[0], "agent_key": r[1], "version": r[2],
                "content": r[3], "status": r[4],
                "created_at": r[5], "published_at": r[6],
                "model_config": _json.loads(r[7]) if r[7] else None,
            })
        result = []
        for agent_key, versions in by_key.items():
            result.append({
                "agent_key":        agent_key,
                "latest_published": next((v for v in versions if v["status"] == "published"), None),
                "draft":            next((v for v in versions if v["status"] == "draft"),     None),
            })
        return result

    async def save_prompt_draft(
        self,
        user_id:      str,
        flow_id:      str,
        agent_key:    str,
        content:      str,
        model_config: dict | None = None,
    ) -> None:
        import json as _json
        p            = self._p()
        now          = datetime.now(timezone.utc).isoformat()
        model_cfg_s  = _json.dumps(model_config) if model_config else None
        existing = await self._fetchone(
            f"SELECT id FROM agent_prompt_versions"
            f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p} AND status = 'draft'",
            (user_id, flow_id, agent_key),
        )
        if existing:
            if self._backend == "sqlite":
                await self._exec(
                    "UPDATE agent_prompt_versions SET content = ?, model_config = ?, created_at = ? WHERE id = ?",
                    (content, model_cfg_s, now, existing[0]),
                )
            else:
                await self._exec(
                    "UPDATE agent_prompt_versions SET content = %s, model_config = %s, created_at = %s WHERE id = %s",
                    (content, model_cfg_s, now, existing[0]),
                )
        else:
            max_row = await self._fetchone(
                f"SELECT MAX(version) FROM agent_prompt_versions"
                f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p} AND status = 'published'",
                (user_id, flow_id, agent_key),
            )
            next_ver = (max_row[0] or 0) + 1
            if self._backend == "sqlite":
                await self._exec(
                    "INSERT INTO agent_prompt_versions"
                    " (user_id, flow_id, agent_key, version, content, model_config, status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, 'draft', ?)",
                    (user_id, flow_id, agent_key, next_ver, content, model_cfg_s, now),
                )
            else:
                await self._exec(
                    "INSERT INTO agent_prompt_versions"
                    " (user_id, flow_id, agent_key, version, content, model_config, status, created_at)"
                    " VALUES (%s, %s, %s, %s, %s, %s, 'draft', %s)",
                    (user_id, flow_id, agent_key, next_ver, content, model_cfg_s, now),
                )

    async def discard_prompt_draft(self, user_id: str, flow_id: str, agent_key: str) -> None:
        p = self._p()
        await self._exec(
            f"DELETE FROM agent_prompt_versions"
            f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p} AND status = 'draft'",
            (user_id, flow_id, agent_key),
        )

    async def publish_prompt(self, user_id: str, flow_id: str, agent_key: str) -> dict:
        import json
        p   = self._p()
        now = datetime.now(timezone.utc).isoformat()
        draft = await self._fetchone(
            f"SELECT id, version FROM agent_prompt_versions"
            f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p} AND status = 'draft'",
            (user_id, flow_id, agent_key),
        )
        if not draft:
            raise ValueError(f"No draft to publish for {flow_id}/{agent_key}")
        draft_id, draft_ver = draft
        if self._backend == "sqlite":
            await self._exec(
                "UPDATE agent_prompt_versions SET status = 'published', published_at = ? WHERE id = ?",
                (now, draft_id),
            )
        else:
            await self._exec(
                "UPDATE agent_prompt_versions SET status = 'published', published_at = %s WHERE id = %s",
                (now, draft_id),
            )
        # Build snapshot: latest published version per agent
        rows = await self._fetchall(
            f"SELECT agent_key, MAX(version) FROM agent_prompt_versions"
            f" WHERE user_id = {p} AND flow_id = {p} AND status = 'published' GROUP BY agent_key",
            (user_id, flow_id),
        )
        agent_versions = {r[0]: r[1] for r in rows}
        max_snap = await self._fetchone(
            f"SELECT MAX(snapshot_version) FROM flow_prompt_snapshots"
            f" WHERE user_id = {p} AND flow_id = {p}",
            (user_id, flow_id),
        )
        next_snap = (max_snap[0] or 0) + 1
        if self._backend == "sqlite":
            await self._exec(
                "INSERT INTO flow_prompt_snapshots"
                " (user_id, flow_id, snapshot_version, agent_versions, created_at, triggered_by)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, flow_id, next_snap, json.dumps(agent_versions), now, agent_key),
            )
        else:
            await self._exec(
                "INSERT INTO flow_prompt_snapshots"
                " (user_id, flow_id, snapshot_version, agent_versions, created_at, triggered_by)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, flow_id, next_snap, json.dumps(agent_versions), now, agent_key),
            )
        return {"snapshot_version": next_snap, "agent_key": agent_key, "version": draft_ver}

    async def publish_skill(self, user_id: str, flow_id: str, agent_keys: list[str]) -> dict:
        """Publish all drafts for a skill atomically and create one new snapshot."""
        import json as _json
        p   = self._p()
        now = datetime.now(timezone.utc).isoformat()

        published = []
        for agent_key in agent_keys:
            draft = await self._fetchone(
                f"SELECT id, version FROM agent_prompt_versions"
                f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p} AND status = 'draft'",
                (user_id, flow_id, agent_key),
            )
            if not draft:
                continue
            draft_id, _ = draft
            if self._backend == "sqlite":
                await self._exec(
                    "UPDATE agent_prompt_versions SET status = 'published', published_at = ? WHERE id = ?",
                    (now, draft_id),
                )
            else:
                await self._exec(
                    "UPDATE agent_prompt_versions SET status = 'published', published_at = %s WHERE id = %s",
                    (now, draft_id),
                )
            published.append(agent_key)

        # Snapshot = latest published version per agent across the whole skill
        rows = await self._fetchall(
            f"SELECT agent_key, MAX(version) FROM agent_prompt_versions"
            f" WHERE user_id = {p} AND flow_id = {p} AND status = 'published' GROUP BY agent_key",
            (user_id, flow_id),
        )
        agent_versions = {r[0]: r[1] for r in rows}
        max_snap = await self._fetchone(
            f"SELECT MAX(snapshot_version) FROM flow_prompt_snapshots"
            f" WHERE user_id = {p} AND flow_id = {p}",
            (user_id, flow_id),
        )
        next_snap = (max_snap[0] or 0) + 1
        if self._backend == "sqlite":
            await self._exec(
                "INSERT INTO flow_prompt_snapshots"
                " (user_id, flow_id, snapshot_version, agent_versions, created_at, triggered_by)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, flow_id, next_snap, _json.dumps(agent_versions), now, "skill_publish"),
            )
        else:
            await self._exec(
                "INSERT INTO flow_prompt_snapshots"
                " (user_id, flow_id, snapshot_version, agent_versions, created_at, triggered_by)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, flow_id, next_snap, _json.dumps(agent_versions), now, "skill_publish"),
            )
        return {
            "snapshot_version": next_snap,
            "published_agents": published,
            "total_agents":     len(agent_keys),
        }

    async def get_latest_snapshot(self, user_id: str, flow_id: str) -> dict | None:
        import json
        p   = self._p()
        row = await self._fetchone(
            f"SELECT id, snapshot_version, agent_versions, created_at, triggered_by"
            f" FROM flow_prompt_snapshots"
            f" WHERE user_id = {p} AND flow_id = {p}"
            f" ORDER BY snapshot_version DESC LIMIT 1",
            (user_id, flow_id),
        )
        if not row:
            return None
        return {"id": row[0], "flow_id": flow_id, "snapshot_version": row[1],
                "agent_versions": json.loads(row[2]), "created_at": row[3], "triggered_by": row[4]}

    async def get_prompt_content_for_snapshot(
        self, user_id: str, flow_id: str, snapshot: dict
    ) -> dict[str, str]:
        p      = self._p()
        result = {}
        for agent_key, version in snapshot["agent_versions"].items():
            row = await self._fetchone(
                f"SELECT content FROM agent_prompt_versions"
                f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p}"
                f" AND version = {p} AND status = 'published'",
                (user_id, flow_id, agent_key, version),
            )
            if row:
                result[agent_key] = row[0]
        return result

    async def get_model_config_for_snapshot(
        self, user_id: str, flow_id: str, snapshot: dict
    ) -> dict[str, dict | None]:
        """Return per-agent model_config for all agents in the snapshot (None = use global)."""
        import json as _json
        p      = self._p()
        result = {}
        for agent_key, version in snapshot["agent_versions"].items():
            row = await self._fetchone(
                f"SELECT model_config FROM agent_prompt_versions"
                f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p}"
                f" AND version = {p} AND status = 'published'",
                (user_id, flow_id, agent_key, version),
            )
            if row and row[0]:
                result[agent_key] = _json.loads(row[0])
        return result

    async def list_snapshots(self, user_id: str, flow_id: str) -> list[dict]:
        import json
        p    = self._p()
        rows = await self._fetchall(
            f"SELECT id, snapshot_version, agent_versions, created_at, triggered_by"
            f" FROM flow_prompt_snapshots"
            f" WHERE user_id = {p} AND flow_id = {p}"
            f" ORDER BY snapshot_version DESC",
            (user_id, flow_id),
        )
        return [{"id": r[0], "snapshot_version": r[1], "agent_versions": json.loads(r[2]),
                 "created_at": r[3], "triggered_by": r[4]} for r in rows]

    async def get_agent_version_history(
        self, user_id: str, flow_id: str, agent_key: str
    ) -> list[dict]:
        import json as _json
        p    = self._p()
        rows = await self._fetchall(
            f"SELECT id, version, content, status, created_at, published_at, model_config"
            f" FROM agent_prompt_versions"
            f" WHERE user_id = {p} AND flow_id = {p} AND agent_key = {p}"
            f" ORDER BY version DESC",
            (user_id, flow_id, agent_key),
        )
        return [{"id": r[0], "version": r[1], "content": r[2],
                 "model_config": _json.loads(r[6]) if r[6] else None,
                 "status": r[3], "created_at": r[4], "published_at": r[5]} for r in rows]

    async def get_prompt_snapshot_id(self, user_id: str, flow_id: str) -> int | None:
        """Return the latest snapshot_version id for a flow, or None."""
        p   = self._p()
        row = await self._fetchone(
            f"SELECT MAX(snapshot_version) FROM flow_prompt_snapshots"
            f" WHERE user_id = {p} AND flow_id = {p}",
            (user_id, flow_id),
        )
        return row[0] if row else None

    # ── Installed skills ──────────────────────────────────────────────────────

    async def get_installed_skill_ids(self, user_id: str) -> set[str]:
        p = self._p()
        rows = await self._fetchall(
            f"SELECT skill_id FROM installed_skills WHERE user_id = {p}",
            (user_id,),
        )
        return {r[0] for r in rows}

    async def install_skill(self, user_id: str, skill_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if self._backend == "sqlite":
            await self._conn_or_pool.execute(
                "INSERT OR IGNORE INTO installed_skills (user_id, skill_id, installed_at) VALUES (?, ?, ?)",
                (user_id, skill_id, now),
            )
            await self._conn_or_pool.commit()
        else:
            async with self._conn_or_pool.connection() as conn:
                await conn.execute(
                    "INSERT INTO installed_skills (user_id, skill_id, installed_at) VALUES (%s, %s, %s)"
                    " ON CONFLICT (user_id, skill_id) DO NOTHING",
                    (user_id, skill_id, now),
                )
                await conn.commit()

    async def uninstall_skill(self, user_id: str, skill_id: str) -> None:
        if self._backend == "sqlite":
            await self._conn_or_pool.execute(
                "DELETE FROM installed_skills WHERE user_id = ? AND skill_id = ?",
                (user_id, skill_id),
            )
            await self._conn_or_pool.commit()
        else:
            async with self._conn_or_pool.connection() as conn:
                await conn.execute(
                    "DELETE FROM installed_skills WHERE user_id = %s AND skill_id = %s",
                    (user_id, skill_id),
                )
                await conn.commit()

    async def delete_expired_sessions(self) -> int:
        cutoff  = (datetime.now(timezone.utc) - timedelta(days=SESSION_TTL_DAYS)).isoformat()
        p = self._p()
        rows = await self._fetchall(
            f"SELECT thread_id FROM agent_sessions WHERE created_at < {p}",
            (cutoff,),
        )
        expired = [r[0] for r in rows]
        if not expired:
            return 0
        if self._backend == "sqlite":
            ph = ",".join("?" * len(expired))
            await self._conn_or_pool.execute(
                f"DELETE FROM agent_sessions WHERE thread_id IN ({ph})", expired  # noqa: S608
            )
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                await self._conn_or_pool.execute(
                    f"DELETE FROM {table} WHERE thread_id IN ({ph})", expired  # noqa: S608
                )
            await self._conn_or_pool.commit()
        else:
            async with self._conn_or_pool.connection() as conn:
                await conn.execute("DELETE FROM agent_sessions WHERE thread_id = ANY(%s)", (expired,))
                for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                    await conn.execute(
                        f"DELETE FROM {table} WHERE thread_id = ANY(%s)", (expired,)  # noqa: S608
                    )
                await conn.commit()
        logger.info("Deleted %d expired sessions", len(expired))
        return len(expired)


# ── SQLite backend ────────────────────────────────────────────────────────────

@asynccontextmanager
async def _sqlite_backend():
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    db_path = Path(SQLITE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(db_path)) as conn:
        await _migrate(conn, "sqlite")
        await conn.execute(_CREATE_USERS)
        await conn.execute(_CREATE_SESSIONS_TABLE)
        for sql in _ADD_SESSION_COLUMNS_SL:
            try:
                await conn.execute(sql)
            except Exception:
                pass  # column already exists
        await conn.execute(_CREATE_SETTINGS_TABLE)
        await conn.execute(_CREATE_USAGE_TABLE_SL)
        await conn.execute(_CREATE_CONFIG_TABLE)
        await conn.execute(_CREATE_PROMPT_VERSIONS_SL)
        await conn.execute(_CREATE_SNAPSHOTS_SL)
        await conn.execute(_CREATE_INSTALLED_SKILLS)
        await conn.commit()

        checkpointer = AsyncSqliteSaver(conn)
        await checkpointer.setup()

        ctx = DBContext(checkpointer=checkpointer, _backend="sqlite", _conn_or_pool=conn)
        cleanup_task = asyncio.create_task(_cleanup_loop(ctx))
        logger.info("DB backend: SQLite at %s", db_path.resolve())
        try:
            yield ctx
        finally:
            cleanup_task.cancel()


# ── PostgreSQL backend ────────────────────────────────────────────────────────

@asynccontextmanager
async def _postgres_backend(url: str):
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool

    # min_size=1 avoids holding idle connections on serverless DBs (Neon, Supabase).
    # max_size is tunable via DB_POOL_SIZE.
    async with AsyncConnectionPool(
        url,
        min_size=1,
        max_size=DB_POOL_SIZE,
        kwargs={"autocommit": True, "prepare_threshold": None},
        open=False,
    ) as pool:
        await pool.open(wait=True)
        async with pool.connection() as conn:
            await _migrate(conn, "postgres")
            await conn.execute(_CREATE_USERS)
            await conn.execute(_CREATE_SESSIONS_TABLE)
            for sql in _ADD_SESSION_COLUMNS_PG:
                await conn.execute(sql)
            await conn.execute(_CREATE_SETTINGS_TABLE)
            await conn.execute(_CREATE_USAGE_TABLE_PG)
            await conn.execute(_CREATE_CONFIG_TABLE)
            await conn.execute(_CREATE_PROMPT_VERSIONS_PG)
            await conn.execute(_CREATE_SNAPSHOTS_PG)
            await conn.execute(_CREATE_INSTALLED_SKILLS)
            await conn.commit()

        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        ctx = DBContext(checkpointer=checkpointer, _backend="postgres", _conn_or_pool=pool)
        cleanup_task = asyncio.create_task(_cleanup_loop(ctx))
        # Log host only — never log credentials
        host = url.split("@")[-1].split("/")[0] if "@" in url else url
        logger.info("DB backend: PostgreSQL at %s", host)
        try:
            yield ctx
        finally:
            cleanup_task.cancel()


# ── Cleanup loop ──────────────────────────────────────────────────────────────

async def _cleanup_loop(ctx: DBContext) -> None:
    while True:
        try:
            await ctx.delete_expired_sessions()
        except Exception:
            logger.exception("Session cleanup failed")
        await asyncio.sleep(24 * 60 * 60)


# ── Public factory ────────────────────────────────────────────────────────────

@asynccontextmanager
async def get_async_checkpointer():
    """
    Select the DB backend automatically from DATABASE_URL:
      postgresql:// or postgres://  →  PostgreSQL (Neon, Supabase, local, …)
      (empty / unset)               →  SQLite
    """
    if DB_BACKEND == "postgres":
        async with _postgres_backend(DATABASE_URL) as ctx:
            yield ctx
    else:
        async with _sqlite_backend() as ctx:
            yield ctx
