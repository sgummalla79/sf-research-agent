"""
LLM Provider Registry — metadata + async model-list fetchers for all supported providers.

Each provider entry describes:
  - display name and description
  - API key placeholder text
  - async fetch_models(api_key) → list[str]

Model lists are fetched once (after key entry) and cached in the DB.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# Ordered list of provider IDs for display
PROVIDER_ORDER = ["anthropic", "openai", "google", "perplexity", "groq", "mistral"]

PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "name":        "Anthropic",
        "description": "Claude Opus, Sonnet, Haiku",
        "placeholder": "sk-ant-api03-…",
        "key_label":   "Anthropic API Key",
        "auth_modes": [
            {
                "id":    "direct",
                "label": "Direct API",
                "fields": [
                    {"key": "anthropic", "label": "API Key", "placeholder": "sk-ant-api03-…"},
                ],
            },
            {
                "id":    "bedrock",
                "label": "AWS Bedrock",
                "fields": [
                    {"key": "anthropic_bedrock_url",   "label": "Bedrock Base URL", "placeholder": "https://…"},
                    {"key": "anthropic_bedrock_token", "label": "Auth Token",       "placeholder": "…"},
                ],
            },
        ],
    },
    "openai": {
        "name":        "OpenAI",
        "description": "GPT-4o, o3, o4-mini and more",
        "placeholder": "sk-proj-…",
        "key_label":   "OpenAI API Key",
    },
    "google": {
        "name":        "Google",
        "description": "Gemini 2.5 Pro, Flash and more",
        "placeholder": "AIza…",
        "key_label":   "Google API Key",
    },
    "perplexity": {
        "name":        "Perplexity",
        "description": "Sonar search-grounded models",
        "placeholder": "pplx-…",
        "key_label":   "Perplexity API Key",
    },
    "groq": {
        "name":        "Groq",
        "description": "Fast inference — Llama, Mixtral, Gemma",
        "placeholder": "gsk_…",
        "key_label":   "Groq API Key",
    },
    "mistral": {
        "name":        "Mistral",
        "description": "Mistral Large, Small, Nemo and more",
        "placeholder": "…",
        "key_label":   "Mistral API Key",
    },
}

# Curated static list for providers that have no public models endpoint
_PERPLEXITY_MODELS = [
    "sonar-pro",
    "sonar",
    "sonar-reasoning-pro",
    "sonar-deep-research",
]

# Models to exclude from OpenAI list (embeddings, audio, image, etc.)
_OPENAI_EXCLUDE_PREFIXES = (
    "text-embedding", "tts-", "whisper-", "dall-e", "davinci", "babbage",
    "text-moderation", "gpt-3.5-turbo-instruct", "ft:", "o1-mini-2024",
)


async def fetch_models(
    provider_id: str,
    api_key: str,
    mode: str = "direct",
    bedrock_url: str = "",
    bedrock_token: str = "",
) -> list[str]:
    """
    Fetch available models for the given provider using the supplied API key.
    Returns a sorted list of model ID strings.
    Raises on auth failure or network error so callers can surface the error to the user.
    """
    if provider_id == "anthropic":
        return await _fetch_anthropic(api_key, mode=mode, bedrock_url=bedrock_url, bedrock_token=bedrock_token)

    fetchers = {
        "openai":     _fetch_openai,
        "google":     _fetch_google,
        "perplexity": _fetch_perplexity,
        "groq":       _fetch_groq,
        "mistral":    _fetch_mistral,
    }
    fn = fetchers.get(provider_id)
    if fn is None:
        raise ValueError(f"Unknown provider: {provider_id!r}")
    return await fn(api_key)


# ── Per-provider fetch implementations ───────────────────────────────────────

# Curated Bedrock model IDs — Bedrock gateway has no /models endpoint
_BEDROCK_MODELS = [
    "us.anthropic.claude-opus-4-7",
    "us.anthropic.claude-sonnet-4-6",
    "us.anthropic.claude-haiku-4-5-20251001",
]


async def _fetch_anthropic(
    api_key: str,
    mode: str = "direct",
    bedrock_url: str = "",
    bedrock_token: str = "",
) -> list[str]:
    import anthropic
    if mode == "bedrock":
        # Bedrock gateway has no /models endpoint — validate by sending a minimal test message
        client = anthropic.AsyncAnthropicBedrock(
            base_url=bedrock_url,
            api_key=bedrock_token,
        )
        await client.messages.create(
            model=_BEDROCK_MODELS[1],
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return list(_BEDROCK_MODELS)
    else:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.models.list(limit=100)
        return sorted(m.id for m in response.data)


async def _fetch_openai(api_key: str) -> list[str]:
    import openai
    client = openai.AsyncOpenAI(api_key=api_key)
    response = await client.models.list()
    models = [
        m.id for m in response.data
        if not any(m.id.startswith(p) for p in _OPENAI_EXCLUDE_PREFIXES)
    ]
    return sorted(models)


async def _fetch_google(api_key: str) -> list[str]:
    # google-generativeai list_models is synchronous; run in thread executor
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    loop = asyncio.get_event_loop()

    def _list():
        return [
            m.name.removeprefix("models/")
            for m in genai.list_models()
            if "generateContent" in (m.supported_generation_methods or [])
        ]

    models = await loop.run_in_executor(None, _list)
    return sorted(models)


async def _fetch_perplexity(api_key: str) -> list[str]:
    # No public models endpoint — validate key format only, return static list
    if not api_key.startswith("pplx-"):
        raise ValueError("Perplexity API keys begin with 'pplx-'. Please check your key.")
    return list(_PERPLEXITY_MODELS)


async def _fetch_groq(api_key: str) -> list[str]:
    import openai
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    response = await client.models.list()
    return sorted(m.id for m in response.data)


async def _fetch_mistral(api_key: str) -> list[str]:
    import httpx
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return sorted(m["id"] for m in data.get("data", []))
