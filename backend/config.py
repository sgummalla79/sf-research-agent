import os
from dotenv import load_dotenv

load_dotenv()

# ── Database (PostgreSQL only) ────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))

# ── LLM ──────────────────────────────────────────────────────────────────────
CLAUDE_HAIKU_MODEL: str = os.getenv("CLAUDE_HAIKU_MODEL", "claude-haiku-4-5-20251001")
PERPLEXITY_API_BASE: str = "https://api.perplexity.ai"

# ── Pipeline limits ───────────────────────────────────────────────────────────
MAX_REVISIONS: int           = int(os.getenv("MAX_REVISIONS", "5"))
MAX_DISCOVERY_QUESTIONS: int = int(os.getenv("MAX_DISCOVERY_QUESTIONS", "30"))

# ── File upload ───────────────────────────────────────────────────────────────
UPLOAD_DIR: str      = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_PDF_PAGES: int   = int(os.getenv("MAX_PDF_PAGES", "50"))
