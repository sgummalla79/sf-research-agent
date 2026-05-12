"""
Model metadata — context window, max output tokens, and pricing per provider/model.

Pricing is per 1,000,000 tokens (input / output).
Patterns are matched as case-insensitive substrings against the model ID.
More specific patterns must come before broader ones in the same family.
"""

from __future__ import annotations

# Each entry: patterns (ordered, most specific first), context_window, max_output_tokens,
# input_cost and output_cost per 1M tokens, and optional notes.
_METADATA = [
    # ── Anthropic ─────────────────────────────────────────────────────────────
    {"patterns": ["claude-opus"],
     "context_window": 200_000, "max_output_tokens": 32_000,
     "input_cost": 15.00, "output_cost": 75.00},

    {"patterns": ["claude-sonnet"],
     "context_window": 200_000, "max_output_tokens": 64_000,
     "input_cost": 3.00, "output_cost": 15.00},

    {"patterns": ["claude-haiku"],
     "context_window": 200_000, "max_output_tokens": 8_096,
     "input_cost": 0.80, "output_cost": 4.00},

    # ── OpenAI ────────────────────────────────────────────────────────────────
    {"patterns": ["o4-mini"],
     "context_window": 200_000, "max_output_tokens": 100_000,
     "input_cost": 1.10, "output_cost": 4.40},

    {"patterns": ["o3-mini"],
     "context_window": 200_000, "max_output_tokens": 100_000,
     "input_cost": 1.10, "output_cost": 4.40},

    {"patterns": ["o3"],
     "context_window": 200_000, "max_output_tokens": 100_000,
     "input_cost": 10.00, "output_cost": 40.00},

    {"patterns": ["o1-mini"],
     "context_window": 128_000, "max_output_tokens": 65_536,
     "input_cost": 3.00, "output_cost": 12.00},

    {"patterns": ["o1"],
     "context_window": 200_000, "max_output_tokens": 100_000,
     "input_cost": 15.00, "output_cost": 60.00},

    {"patterns": ["gpt-4o-mini"],
     "context_window": 128_000, "max_output_tokens": 16_384,
     "input_cost": 0.15, "output_cost": 0.60},

    {"patterns": ["gpt-4o"],
     "context_window": 128_000, "max_output_tokens": 16_384,
     "input_cost": 2.50, "output_cost": 10.00},

    {"patterns": ["gpt-4-turbo"],
     "context_window": 128_000, "max_output_tokens": 4_096,
     "input_cost": 10.00, "output_cost": 30.00},

    {"patterns": ["gpt-4"],
     "context_window": 8_192, "max_output_tokens": 8_192,
     "input_cost": 30.00, "output_cost": 60.00},

    {"patterns": ["gpt-3.5-turbo"],
     "context_window": 16_385, "max_output_tokens": 4_096,
     "input_cost": 0.50, "output_cost": 1.50},

    # ── Google ────────────────────────────────────────────────────────────────
    {"patterns": ["gemini-2.5-pro"],
     "context_window": 1_048_576, "max_output_tokens": 65_536,
     "input_cost": 1.25, "output_cost": 10.00},

    {"patterns": ["gemini-2.5-flash"],
     "context_window": 1_048_576, "max_output_tokens": 65_536,
     "input_cost": 0.30, "output_cost": 2.50},

    {"patterns": ["gemini-2.0-flash"],
     "context_window": 1_048_576, "max_output_tokens": 8_192,
     "input_cost": 0.10, "output_cost": 0.40},

    {"patterns": ["gemini-1.5-pro"],
     "context_window": 2_097_152, "max_output_tokens": 8_192,
     "input_cost": 1.25, "output_cost": 5.00},

    {"patterns": ["gemini-1.5-flash"],
     "context_window": 1_048_576, "max_output_tokens": 8_192,
     "input_cost": 0.075, "output_cost": 0.30},

    # ── Perplexity ────────────────────────────────────────────────────────────
    {"patterns": ["sonar-reasoning-pro"],
     "context_window": 128_000, "max_output_tokens": 8_000,
     "input_cost": 8.00, "output_cost": 40.00},

    {"patterns": ["sonar-deep-research"],
     "context_window": 128_000, "max_output_tokens": 8_000,
     "input_cost": 8.00, "output_cost": 40.00},

    {"patterns": ["sonar-pro"],
     "context_window": 200_000, "max_output_tokens": 8_000,
     "input_cost": 3.00, "output_cost": 15.00},

    {"patterns": ["sonar"],
     "context_window": 128_000, "max_output_tokens": 8_000,
     "input_cost": 1.00, "output_cost": 1.00},

    # ── Groq ──────────────────────────────────────────────────────────────────
    {"patterns": ["llama-3.3-70b", "llama-3.1-70b"],
     "context_window": 128_000, "max_output_tokens": 32_768,
     "input_cost": 0.59, "output_cost": 0.79},

    {"patterns": ["llama-3.1-8b", "llama-3-8b"],
     "context_window": 128_000, "max_output_tokens": 8_192,
     "input_cost": 0.05, "output_cost": 0.08},

    {"patterns": ["mixtral-8x7b"],
     "context_window": 32_768, "max_output_tokens": 32_768,
     "input_cost": 0.24, "output_cost": 0.24},

    {"patterns": ["gemma2-9b"],
     "context_window": 8_192, "max_output_tokens": 8_192,
     "input_cost": 0.20, "output_cost": 0.20},

    # ── Mistral ───────────────────────────────────────────────────────────────
    {"patterns": ["mistral-large"],
     "context_window": 128_000, "max_output_tokens": 128_000,
     "input_cost": 2.00, "output_cost": 6.00},

    {"patterns": ["mistral-medium"],
     "context_window": 32_000, "max_output_tokens": 8_192,
     "input_cost": 0.40, "output_cost": 1.20},

    {"patterns": ["mistral-small", "ministral-3b", "ministral-8b"],
     "context_window": 32_000, "max_output_tokens": 8_192,
     "input_cost": 0.10, "output_cost": 0.30},

    {"patterns": ["codestral"],
     "context_window": 256_000, "max_output_tokens": 256_000,
     "input_cost": 0.30, "output_cost": 0.90},
]


def lookup(model_id: str) -> dict | None:
    """
    Return metadata for the given model ID by substring matching.
    Returns None if no pattern matches.
    """
    model_lower = model_id.lower()
    for entry in _METADATA:
        if any(p in model_lower for p in entry["patterns"]):
            return {
                "context_window":      entry["context_window"],
                "max_output_tokens":   entry["max_output_tokens"],
                "input_cost_per_million":  entry["input_cost"],
                "output_cost_per_million": entry["output_cost"],
            }
    return None


async def fetch_live(provider_id: str, model_id: str) -> dict | None:
    """
    Attempt a live API call to get accurate context window for the model.
    Currently implemented for Anthropic only (their SDK exposes it).
    Returns None if the provider isn't supported or the call fails.
    """
    if provider_id != "anthropic":
        return None
    try:
        from utils.api_keys import get_key
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=get_key("anthropic"))
        model  = await client.models.retrieve(model_id)
        return {"context_window": model.context_window}
    except Exception:
        return None
