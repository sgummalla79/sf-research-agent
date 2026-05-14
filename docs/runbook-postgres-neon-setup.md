# Runbook — PostgreSQL + Neon + psycopg3 + LangGraph Setup Issues

Use this document whenever the backend fails to start, tables are missing,
or DB-related errors appear after a deployment or restart.

---

## The Three Non-Negotiable Pool Settings

Any time you touch `AsyncConnectionPool` kwargs in `checkpointer.py`, all three
of these must be present. Removing any one breaks things in a non-obvious way.

```python
kwargs={"autocommit": True, "prepare_threshold": None}
```

| Setting | Value | Why |
|---|---|---|
| `autocommit` | `True` | LangGraph migrations use `CREATE INDEX CONCURRENTLY` which cannot run inside a transaction block |
| `prepare_threshold` | `None` | Neon's pooler uses PgBouncer in transaction mode — PgBouncer does not support prepared statements. `None` = never prepare. `0` = prepare immediately (opposite of what you want) |

**Common mistake:** `prepare_threshold=0` looks like "zero prepared statements" but
actually means "prepare at first execution". The correct value to disable prepared
statements entirely is `None`.

---

## Migration Wipe Rule — Always Drop the Migration Tracker Too

Any library that tracks its own migration state in a table (LangGraph uses
`checkpoint_migrations`) must have that tracker table dropped alongside its
data tables in `_migrate()`.

**Why:** If the tracker survives a wipe, the library queries it on next startup,
sees "all migrations already applied", and skips every `CREATE TABLE` statement.
The actual tables are never recreated.

**Rule:** For every external library that manages its own schema, add its
migration/version tracking table to `_migrate()`'s drop list.

Current example — LangGraph:
```python
# LangGraph internal tables — include migrations table so setup()
# re-runs all CREATE TABLE statements after a wipe
"checkpoint_writes", "checkpoint_blobs", "checkpoints",
"checkpoint_migrations",   # ← tracker must be here too
```

If you add another library with its own migration table in the future,
apply the same pattern.

---

## Diagnosing "Tables Missing" After Startup

### Step 1 — Check the health endpoint

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

The `tables` check lists exactly which tables are missing.

### Step 2 — Check what actually exists in the DB

```bash
cd backend && source .venv/bin/activate
python3 -c "
import asyncio, os
from dotenv import load_dotenv
load_dotenv()
import psycopg

async def check():
    url = os.environ['DATABASE_URL']
    async with await psycopg.AsyncConnection.connect(url, prepare_threshold=None, autocommit=True) as conn:
        cur = await conn.execute(\"SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' ORDER BY tablename\")
        rows = await cur.fetchall()
        print([r[0] for r in rows])

asyncio.run(check())
"
```

### Step 3 — If a library's data tables are missing but its tracker table exists

The tracker has stale entries. Drop it manually so the library re-runs from scratch:

```bash
python3 -c "
import asyncio, os
from dotenv import load_dotenv
load_dotenv()
import psycopg

async def fix():
    url = os.environ['DATABASE_URL']
    async with await psycopg.AsyncConnection.connect(url, prepare_threshold=None, autocommit=True) as conn:
        await conn.execute('DROP TABLE IF EXISTS THE_TRACKER_TABLE_NAME')
        print('Done — restart the backend')

asyncio.run(fix())
"
```

Replace `THE_TRACKER_TABLE_NAME` with the actual tracker (e.g. `checkpoint_migrations`
for LangGraph). Then restart — the library will recreate everything from scratch.

### Step 4 — Verify after restart

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
# "tables": { "ok": true, "total": 11, "missing": [] }
```

---

## Common Errors and Their Causes

| Error | Cause | Fix |
|---|---|---|
| `cannot insert multiple commands into a prepared statement` | `prepare_threshold=0` (wrong value) | Change to `prepare_threshold=None` |
| `CREATE INDEX CONCURRENTLY cannot run inside a transaction block` | `autocommit` missing or `False` | Add `"autocommit": True` to pool kwargs |
| Tables missing but no startup error | Migration tracker survived a wipe; library skipped all `CREATE TABLE` | Drop the tracker table manually, restart |
| `relation "X" does not exist` during a request | Table was never created (see above) | Same as above |
| App crashes on startup with psycopg error | Pool kwargs wrong | Check all three settings in the table at the top |

---

## Where These Settings Live

`backend/persistence/checkpointer.py` — `_postgres_backend()` function.

Look for `AsyncConnectionPool(...)` and verify the `kwargs` dict has both settings.
