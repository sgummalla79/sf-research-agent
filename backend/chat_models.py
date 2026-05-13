"""
Curated Claude model list for free-form chat sessions.

These are separate from agent flow models (which are configured per-slot
in the agent config).  Only Claude models are offered for chat.
"""

CHAT_MODELS: list[dict] = [
    {
        "model":       "claude-opus-4-7",
        "display":     "Opus 4.7",
        "description": "Most capable for ambitious work",
    },
    {
        "model":       "claude-sonnet-4-6",
        "display":     "Sonnet 4.6",
        "description": "Responsive everyday work",
        "default":     True,
    },
    {
        "model":       "claude-haiku-4-5-20251001",
        "display":     "Haiku 4.5",
        "description": "Fastest, most efficient",
    },
]

CHAT_DEFAULT_MODEL = "claude-sonnet-4-6"
