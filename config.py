import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
PERPLEXITY_API_KEY = os.environ["PERPLEXITY_API_KEY"]
GOOGLE_API_KEY     = os.environ["GOOGLE_API_KEY"]

# ── Database backend ──────────────────────────────────────────────────────────
# DB_BACKEND = "postgres"  →  local Docker or any cloud PostgreSQL (Supabase, Neon, Railway...)
# DB_BACKEND = "sqlite"    →  zero-config local file, ideal for dev/testing
DB_BACKEND   = os.getenv("DB_BACKEND", "postgres")
POSTGRES_URI = os.getenv("POSTGRES_URI", "")          # required when DB_BACKEND=postgres
SQLITE_PATH  = os.getenv("SQLITE_PATH", "data/agent.db")  # used when DB_BACKEND=sqlite

# Intake, Discovery, Reviewer, Approver, document writing: Claude Sonnet
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# Session title generation: Claude Haiku (fast, low-cost, 500ms)
CLAUDE_HAIKU_MODEL = os.getenv("CLAUDE_HAIKU_MODEL", "claude-haiku-4-5-20251001")

# Research — Perplexity: real-time web search, current limits, citations
PERPLEXITY_MODEL    = os.getenv("PERPLEXITY_MODEL", "sonar-pro")
PERPLEXITY_API_BASE = "https://api.perplexity.ai"

# Research — Gemini: deep architectural reasoning, 1M context, Search grounding
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

# Maximum approver rejection loops before halting
MAX_REVISIONS = 5

# Safety cap on discovery questions.
# The agent asks as many as it needs — this only prevents infinite loops
# if answers are consistently too vague to satisfy any section.
# At 30 questions the agent proceeds with whatever it has gathered.
MAX_DISCOVERY_QUESTIONS = int(os.getenv("MAX_DISCOVERY_QUESTIONS", "30"))

# Session lifecycle
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "15"))

# Database connection pool
# 10 concurrent sessions × ~2 DB ops per node = 20 minimum
# Increase for higher concurrency targets
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))

# File upload — local filesystem storage
UPLOAD_DIR       = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_PDF_PAGES    = int(os.getenv("MAX_PDF_PAGES",    "50"))
