"""
Curated chat-capable models per LLM provider.

Only models suitable for free-form conversation are listed here.
The flows route filters this list to only include providers the user
has connected, so the frontend never shows models the user can't use.
"""

# provider_id → list of chat-capable models (in display order)
CHAT_MODELS_BY_PROVIDER: dict[str, list[dict]] = {
    "anthropic": [
        {
            "model":       "claude-opus-4-7",
            "display":     "Claude Opus 4.7",
            "description": "Most capable — ambitious and complex work",
            "provider":    "anthropic",
        },
        {
            "model":       "claude-sonnet-4-6",
            "display":     "Claude Sonnet 4.6",
            "description": "Balanced — responsive everyday work",
            "provider":    "anthropic",
            "default":     True,
        },
        {
            "model":       "claude-haiku-4-5-20251001",
            "display":     "Claude Haiku 4.5",
            "description": "Fastest — quick tasks and high volume",
            "provider":    "anthropic",
        },
    ],
    "google": [
        {
            "model":       "gemini-2.0-flash",
            "display":     "Gemini 2.0 Flash",
            "description": "Fast and capable",
            "provider":    "google",
            "default":     True,
        },
        {
            "model":       "gemini-1.5-pro",
            "display":     "Gemini 1.5 Pro",
            "description": "Long context, strong reasoning",
            "provider":    "google",
        },
        {
            "model":       "gemini-1.5-flash",
            "display":     "Gemini 1.5 Flash",
            "description": "Efficient for everyday tasks",
            "provider":    "google",
        },
    ],
    "openai": [
        {
            "model":       "gpt-4o",
            "display":     "GPT-4o",
            "description": "Most capable OpenAI model",
            "provider":    "openai",
            "default":     True,
        },
        {
            "model":       "gpt-4o-mini",
            "display":     "GPT-4o Mini",
            "description": "Fast and cost-efficient",
            "provider":    "openai",
        },
    ],
    "perplexity": [
        {
            "model":       "sonar-pro",
            "display":     "Sonar Pro",
            "description": "Search-grounded, high accuracy",
            "provider":    "perplexity",
            "default":     True,
        },
        {
            "model":       "sonar",
            "display":     "Sonar",
            "description": "Search-grounded, fast",
            "provider":    "perplexity",
        },
    ],
}

# Fallback default model used when no provider-specific default is found
CHAT_DEFAULT_MODEL    = "claude-sonnet-4-6"
CHAT_DEFAULT_PROVIDER = "anthropic"
