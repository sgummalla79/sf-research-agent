import os
from dotenv import load_dotenv

load_dotenv()

# ── Auth (shared with Express server) ────────────────────────────────────────
# Must match JWT_SECRET in express-server/.env — Express signs service tokens
# with this secret; FastAPI validates them. Leave empty to run standalone in
# dev mode (all requests resolve to "dev-user").
JWT_SECRET = os.getenv("JWT_SECRET", "")

# ── API keys are managed via the Settings UI, not environment variables ───────
# Use utils.api_keys.get_key() in agent code to retrieve them at call time.

# ── Database ──────────────────────────────────────────────────────────────────
# Set DATABASE_URL to select the backend automatically:
#   postgresql://...  →  PostgreSQL  (Neon, Supabase, local Docker, etc.)
#   (empty / unset)   →  SQLite (zero-config, ideal for local dev/testing)
#
# Examples:
#   DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/db?sslmode=require
#   DATABASE_URL=postgresql://agent:agent@localhost:5432/research_agent
DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_PATH  = os.getenv("SQLITE_PATH", "data/agent.db")  # used when DATABASE_URL is empty

# Derived — no need to set these manually
_url_lower = DATABASE_URL.lower()
DB_BACKEND  = "postgres" if _url_lower.startswith(("postgresql://", "postgres://")) else "sqlite"
POSTGRES_URI = DATABASE_URL if DB_BACKEND == "postgres" else ""

# Session title generation: Claude Haiku (fast, low-cost, 500ms)
CLAUDE_HAIKU_MODEL = os.getenv("CLAUDE_HAIKU_MODEL", "claude-haiku-4-5-20251001")

# Perplexity base URL (OpenAI-compatible)
PERPLEXITY_API_BASE = "https://api.perplexity.ai"

# Maximum approver rejection loops before halting
MAX_REVISIONS = 5

# Safety cap on discovery questions.
MAX_DISCOVERY_QUESTIONS = int(os.getenv("MAX_DISCOVERY_QUESTIONS", "30"))

# Session lifecycle
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "15"))

# Database connection pool (PostgreSQL only)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))

# File upload — local filesystem storage
UPLOAD_DIR       = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_PDF_PAGES    = int(os.getenv("MAX_PDF_PAGES",    "50"))
