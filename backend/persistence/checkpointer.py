"""
Database backend factory for LangGraph checkpointing.

DB_BACKEND=sqlite    → aiosqlite, zero-config local file
DB_BACKEND=postgres  → AsyncPostgresSaver + connection pool

Public API on DBContext:
  record_session(id, snippet)          create session
  update_session_title(id, title)      overwrite title after Haiku generation
  update_last_modified(id)             called on every reply
  pin_session(id)                      pin (max 10)
  unpin_session(id)
  rename_session(id, title)
  delete_session(id)                   removes from agent_sessions + LG tables
  list_sessions()                      returns {pinned:[...], recent:[...]}
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import DB_BACKEND, DB_POOL_SIZE, POSTGRES_URI, SESSION_TTL_DAYS, SQLITE_PATH

logger = logging.getLogger(__name__)

MAX_PINNED = 10

# ── DDL ───────────────────────────────────────────────────────────────────────

_CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    thread_id      TEXT PRIMARY KEY,
    created_at     TEXT NOT NULL,
    brief_snippet  TEXT,
    last_modified  TEXT,
    pinned         INTEGER DEFAULT 0,
    pinned_at      TEXT
);
"""

_CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS app_settings (
    key_name        TEXT PRIMARY KEY,
    encrypted_value TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

# ── SQL — SQLite (? placeholders) ─────────────────────────────────────────────

_SL = dict(
    insert   = "INSERT OR REPLACE INTO agent_sessions (thread_id, created_at, brief_snippet, last_modified) VALUES (?, ?, ?, ?)",
    set_title= "UPDATE agent_sessions SET brief_snippet  = ? WHERE thread_id = ?",
    set_lm   = "UPDATE agent_sessions SET last_modified  = ? WHERE thread_id = ?",
    pin_count= "SELECT COUNT(*) FROM agent_sessions WHERE pinned = 1",
    pin      = "UPDATE agent_sessions SET pinned = 1, pinned_at = ? WHERE thread_id = ?",
    unpin    = "UPDATE agent_sessions SET pinned = 0, pinned_at = NULL WHERE thread_id = ?",
    rename   = "UPDATE agent_sessions SET brief_snippet  = ? WHERE thread_id = ?",
    del_sess = "DELETE FROM agent_sessions WHERE thread_id = ?",
    list_all = "SELECT thread_id, created_at, brief_snippet, last_modified, pinned, pinned_at FROM agent_sessions",
    expired  = "SELECT thread_id FROM agent_sessions WHERE created_at < ?",
    del_by_ids= "DELETE FROM {table} WHERE thread_id IN ({ph})",
)

# ── SQL — PostgreSQL (%s placeholders) ────────────────────────────────────────

_PG = dict(
    insert   = "INSERT INTO agent_sessions (thread_id, created_at, brief_snippet, last_modified) VALUES (%s, %s, %s, %s) ON CONFLICT (thread_id) DO NOTHING",
    set_title= "UPDATE agent_sessions SET brief_snippet  = %s WHERE thread_id = %s",
    set_lm   = "UPDATE agent_sessions SET last_modified  = %s WHERE thread_id = %s",
    pin_count= "SELECT COUNT(*) FROM agent_sessions WHERE pinned = 1",
    pin      = "UPDATE agent_sessions SET pinned = 1, pinned_at = %s WHERE thread_id = %s",
    unpin    = "UPDATE agent_sessions SET pinned = 0, pinned_at = NULL WHERE thread_id = %s",
    rename   = "UPDATE agent_sessions SET brief_snippet  = %s WHERE thread_id = %s",
    del_sess = "DELETE FROM agent_sessions WHERE thread_id = %s",
    list_all = "SELECT thread_id, created_at, brief_snippet, last_modified, pinned, pinned_at FROM agent_sessions",
    expired  = "SELECT thread_id FROM agent_sessions WHERE created_at < %s",
)


# ── DBContext ─────────────────────────────────────────────────────────────────

@dataclass
class DBContext:
    checkpointer:  Any
    _backend:      str
    _conn_or_pool: Any

    # ── helpers ───────────────────────────────────────────────────────────────

    def _q(self, key: str) -> str:
        return _SL[key] if self._backend == "sqlite" else _PG[key]

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

    async def record_session(self, thread_id: str, brief_snippet: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._exec(self._q("insert"), (thread_id, now, brief_snippet[:120], now))

    async def update_session_title(self, thread_id: str, title: str) -> None:
        await self._exec(self._q("set_title"), (title[:120], thread_id))

    async def update_last_modified(self, thread_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._exec(self._q("set_lm"), (now, thread_id))

    async def pin_session(self, thread_id: str) -> None:
        row = await self._fetchone(self._q("pin_count"))
        if row and row[0] >= MAX_PINNED:
            raise ValueError(f"Maximum {MAX_PINNED} pinned conversations reached.")
        now = datetime.now(timezone.utc).isoformat()
        await self._exec(self._q("pin"), (now, thread_id))

    async def unpin_session(self, thread_id: str) -> None:
        await self._exec(self._q("unpin"), (thread_id,))

    async def rename_session(self, thread_id: str, title: str) -> None:
        await self._exec(self._q("rename"), (title[:120], thread_id))

    async def delete_session(self, thread_id: str) -> None:
        await self._exec(self._q("del_sess"), (thread_id,))
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

    async def list_sessions(self) -> dict:
        rows  = await self._fetchall(self._q("list_all"))
        items = [
            {
                "thread_id":     r[0],
                "created_at":    r[1],
                "brief_snippet": r[2],
                "last_modified": r[3],
                "pinned":        bool(r[4]),
                "pinned_at":     r[5],
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

    async def save_api_key(self, key_name: str, encrypted_value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if self._backend == "sqlite":
            await self._exec(
                "INSERT OR REPLACE INTO app_settings (key_name, encrypted_value, updated_at) VALUES (?, ?, ?)",
                (key_name, encrypted_value, now),
            )
        else:
            await self._exec(
                "INSERT INTO app_settings (key_name, encrypted_value, updated_at) VALUES (%s, %s, %s)"
                " ON CONFLICT (key_name) DO UPDATE SET encrypted_value = EXCLUDED.encrypted_value, updated_at = EXCLUDED.updated_at",
                (key_name, encrypted_value, now),
            )

    async def get_all_api_keys(self) -> dict[str, str]:
        """Returns {key_name: encrypted_value} for every stored key."""
        rows = await self._fetchall("SELECT key_name, encrypted_value FROM app_settings")
        return {r[0]: r[1] for r in rows}

    async def delete_expired_sessions(self) -> int:
        cutoff  = (datetime.now(timezone.utc) - timedelta(days=SESSION_TTL_DAYS)).isoformat()
        rows    = await self._fetchall(self._q("expired"), (cutoff,))
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


# ── Migration ─────────────────────────────────────────────────────────────────

async def _migrate(conn, backend: str) -> None:
    new_cols = [
        ("brief_snippet", "TEXT"),
        ("last_modified", "TEXT"),
        ("pinned",        "INTEGER DEFAULT 0"),
        ("pinned_at",     "TEXT"),
    ]
    for col, typ in new_cols:
        try:
            if backend == "sqlite":
                await conn.execute(f"ALTER TABLE agent_sessions ADD COLUMN {col} {typ}")
                await conn.commit()
            else:
                await conn.execute(f"ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS {col} {typ}")
                await conn.commit()
        except Exception:
            pass  # column already exists


# ── SQLite backend ────────────────────────────────────────────────────────────

@asynccontextmanager
async def _sqlite_backend():
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    db_path = Path(SQLITE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute(_CREATE_SESSIONS_TABLE)
        await conn.execute(_CREATE_SETTINGS_TABLE)
        await conn.commit()
        await _migrate(conn, "sqlite")

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
async def _postgres_backend():
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool

    if not POSTGRES_URI:
        raise ValueError("POSTGRES_URI is required when DB_BACKEND=postgres.")

    async with AsyncConnectionPool(
        POSTGRES_URI, min_size=5, max_size=DB_POOL_SIZE, kwargs={"autocommit": True},
    ) as pool:
        async with pool.connection() as conn:
            pg_ddl = _CREATE_SESSIONS_TABLE.replace("?", "%s")
            await conn.execute(pg_ddl)
            await conn.execute(_CREATE_SETTINGS_TABLE)
            await conn.commit()
            await _migrate(conn, "postgres")

        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        ctx = DBContext(checkpointer=checkpointer, _backend="postgres", _conn_or_pool=pool)
        cleanup_task = asyncio.create_task(_cleanup_loop(ctx))
        logger.info("DB backend: PostgreSQL at %s", POSTGRES_URI.split("@")[-1])
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
    if DB_BACKEND == "sqlite":
        async with _sqlite_backend() as ctx:
            yield ctx
    else:
        async with _postgres_backend() as ctx:
            yield ctx
