"""
LLM model pricing — used for cost estimation only.
All prices are per 1,000,000 tokens (input / output).
Update these constants when provider pricing changes.
"""

MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":         {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input":  0.80, "output":  4.00},
    "sonar-pro":                 {"input":  3.00, "output": 15.00},
    "gemini-2.5-pro":            {"input":  1.25, "output": 10.00},
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    p = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    return round((input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000, 6)


def usage_record(agent: str, model: str, metadata: dict | None) -> dict:
    """Build a usage record dict from LangChain usage_metadata."""
    from datetime import datetime, timezone
    m   = metadata or {}
    inp = m.get("input_tokens", 0)
    out = m.get("output_tokens", 0)
    return {
        "agent":         agent,
        "model":         model,
        "input_tokens":  inp,
        "output_tokens": out,
        "cost_usd":      cost_usd(model, inp, out),
        "created_at":    datetime.now(timezone.utc).isoformat(),
    }
